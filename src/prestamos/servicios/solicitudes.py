"""Caso de uso: solicitud, aprobacion y rechazo de prestamos (RF-05, RF-08).

Este servicio cubre la *fase de decision* del ciclo de vida: T-01 (crear),
T-02 (aprobar) y T-03 (rechazar). La *fase de custodia* -entrega, devolucion,
atraso- y la cancelacion viven en `servicios/prestamos.py`.

Ese corte no coincide con `docs/reglas-negocio.md`, que mapea RN-15 aqui: la
cancelacion ya estaba implementada y probada en `prestamos.py` como parte del
issue #12, y T-04/T-05 cancelan desde SOLICITADA *y* desde APROBADA, o sea que
pertenece a las salidas de la maquina de estados y no a la decision. La fila del
documento se corrige, no el codigo.

No decide nada por su cuenta: cada operacion arma el `Prestamo` resultante y se
lo pasa a `reglas.validar_transicion` con el contexto que las guardas necesitan
(catalogo de equipos, prestamos existentes, solicitante). Lo unico que este
modulo posee es la *orquestacion*: resolver referencias, generar el id, ordenar
las escrituras y registrar el evento.

Autorizacion: se inyecta un `ServicioAuth` y cada operacion llama
`requiere_rol(...)` por dentro, como `ServicioUsuarios` y `ServicioEquipos`. A
diferencia de `ServicioPrestamos`, que recibe un `Usuario` por parametro, aqui
el usuario se relee en cada llamada, de modo que un encargado desactivado a
mitad de sesion deja de poder aprobar de inmediato (RN-02). La convivencia de
ambas convenciones esta anotada en el issue #48; la aprobacion es justamente la
operacion donde la diferencia mas importa, porque es la que compromete
inventario.
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Iterable

from prestamos.auth import ServicioAuth
from prestamos.errores import ErrorValidacion
from prestamos.logging_conf import registrar_evento
from prestamos.modelos import (
    Equipo,
    EstadoPrestamo,
    Prestamo,
    Rol,
    Usuario,
    normalizar_identificador,
)
from prestamos.reglas import EventoTransicion, estado_por_compromiso, validar_transicion
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.repositorios.json_repo import RepositorioJson

# Prefijo e id de las solicitudes. Se usa `S-` y no `P-` porque el archivo es
# `solicitudes.json` y porque T-01 es la transicion que crea el registro; que la
# entidad se llame `Prestamo` y cubra los siete estados es la asimetria que
# `repositorios/fabricas.py` ya documenta.
PREFIJO_SOLICITUD = "S-"
ANCHO_SECUENCIA = 4
_SECUENCIA = re.compile(rf"^{re.escape(PREFIJO_SOLICITUD)}(\d+)$")


class ServicioSolicitudes:
    """Crear, aprobar y rechazar solicitudes, respaldadas por JSON."""

    def __init__(
        self,
        auth: ServicioAuth,
        repo_prestamos: RepositorioJson[Prestamo] | None = None,
        repo_equipos: RepositorioJson[Equipo] | None = None,
        repo_usuarios: RepositorioJson[Usuario] | None = None,
        *,
        datos_dir: str | Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Servicio de solicitudes.

        Son cuatro colaboradores, el constructor mas pesado del paquete, y cada
        uno responde a una guarda concreta del motor:

        - `repo_prestamos`: RN-07 (limite de equipos activos) y RN-10
          (solapamiento) necesitan ver *todas* las solicitudes, no solo la que
          se esta tocando.
        - `repo_equipos`: RN-05 exige el catalogo para resolver los codigos.
        - `repo_usuarios`: `reglas._validar_aprobacion` pide un `solicitante`
          para comprobar RN-02, y `ServicioAuth` solo sabe resolver al usuario
          *actual*.

        `repo_usuarios` deberia ser *el mismo* que usa `auth`, por la razon que
        documenta `servicios/usuarios.py`: ambos leen `usuarios.json`, y si
        apuntan a archivos distintos una baja logica no invalidaria la sesion
        correspondiente.

        `logger` se inyecta para que las pruebas no escriban en el log real:
        `datos/logs/eventos.log` esta versionado.
        """
        self._auth = auth
        self._prestamos = repo_prestamos or repositorio_prestamos(datos_dir)
        self._equipos = repo_equipos or repositorio_equipos(datos_dir)
        self._usuarios = repo_usuarios or repositorio_usuarios(datos_dir)
        self._logger = logger

    # ------------------------------------------------------------------ API

    def crear_solicitud(
        self,
        equipos: Iterable[str],
        motivo: str,
        fecha_inicio: date,
        fecha_termino: date,
        *,
        fecha_solicitud: date | None = None,
    ) -> Prestamo:
        """T-01: un Solicitante pide equipos para un rango de fechas (RF-05).

        El id lo genera el servicio y no el llamador: `json_repo.guardar` es un
        *upsert*, asi que un id repetido reemplazaria la solicitud existente en
        silencio. Generandolo aqui, el chequeo de colision vive en un solo
        lugar.
        """
        solicitante = self._auth.requiere_rol(Rol.SOLICITANTE)
        hoy = fecha_solicitud or date.today()
        codigos = self._normalizar_codigos(equipos)

        existentes = self._prestamos.listar()
        catalogo = self._resolver_equipos(codigos, accion="solicitud_creada", actor=solicitante)

        solicitud = Prestamo(
            id=self._siguiente_id(existentes),
            id_solicitante=solicitante.id,
            equipos=codigos,
            motivo=motivo,
            estado=EstadoPrestamo.SOLICITADA,
            fecha_solicitud=hoy,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
        )

        self._validar(
            solicitud,
            EventoTransicion.CREAR_SOLICITUD,
            solicitante,
            accion="solicitud_creada",
            fecha_actual=hoy,
            equipos=catalogo,
            prestamos_existentes=existentes,
        )

        self._prestamos.guardar(solicitud)
        self._evento(
            "solicitud_creada",
            actor=solicitante,
            objetivo=solicitud.id,
            equipos=list(codigos),
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_termino=fecha_termino.isoformat(),
        )
        return solicitud

    def aprobar(
        self,
        id_solicitud: str,
        *,
        fecha_aprobacion: date | None = None,
    ) -> Prestamo:
        """T-02: el Encargado aprueba y el equipo queda reservado (RF-08).

        Orden de escritura: se resuelve todo lo que puede levantar
        `RecursoNoEncontrado` *antes* de la primera escritura, siguiendo el
        precedente de `prestamos.registrar_devolucion`. Recien despues se guarda
        la solicitud y se recalcula el estado de cada equipo.
        """
        encargado = self._auth.requiere_rol(Rol.ENCARGADO)
        hoy = fecha_aprobacion or date.today()
        solicitud = self._prestamos.obtener(normalizar_identificador(id_solicitud))

        existentes = self._prestamos.listar()
        catalogo = self._resolver_equipos(
            solicitud.equipos, accion="solicitud_aprobada", actor=encargado
        )
        solicitante = self._resolver_solicitante(solicitud, actor=encargado)

        aprobada = replace(
            solicitud,
            estado=EstadoPrestamo.APROBADA,
            fecha_aprobacion=hoy,
        )

        self._validar(
            solicitud,
            EventoTransicion.APROBAR_SOLICITUD,
            encargado,
            accion="solicitud_aprobada",
            objetivo=solicitud.id,
            fecha_actual=hoy,
            equipos=catalogo,
            prestamos_existentes=existentes,
            solicitante=solicitante,
        )

        self._prestamos.guardar(aprobada)
        self._sincronizar_equipos(catalogo.values(), existentes, aprobada, hoy)
        self._evento(
            "solicitud_aprobada",
            actor=encargado,
            objetivo=aprobada.id,
            id_solicitante=aprobada.id_solicitante,
            equipos=list(aprobada.equipos),
        )
        return aprobada

    def rechazar(self, id_solicitud: str, motivo: str) -> Prestamo:
        """T-03: el Encargado rechaza, y el motivo es obligatorio (RF-08, RN-17).

        No toca el estado de los equipos: una solicitud rechazada nunca llego a
        comprometer inventario.
        """
        encargado = self._auth.requiere_rol(Rol.ENCARGADO)
        solicitud = self._prestamos.obtener(normalizar_identificador(id_solicitud))

        rechazada = replace(
            solicitud,
            estado=EstadoPrestamo.RECHAZADA,
            motivo_rechazo=motivo,
        )

        self._validar(
            solicitud,
            EventoTransicion.RECHAZAR_SOLICITUD,
            encargado,
            accion="solicitud_rechazada",
            objetivo=solicitud.id,
            motivo_rechazo=motivo,
        )

        self._prestamos.guardar(rechazada)
        self._evento(
            "solicitud_rechazada",
            actor=encargado,
            objetivo=rechazada.id,
            id_solicitante=rechazada.id_solicitante,
        )
        return rechazada

    # -------------------------------------------------------------- Interno

    def _validar(
        self,
        solicitud: Prestamo,
        evento: EventoTransicion,
        actor: Usuario,
        *,
        accion: str,
        objetivo: str | None = None,
        **contexto: object,
    ) -> None:
        """Delega en el motor y deja el rechazo en el log (RN-17, RN-18).

        `f413186` fijo el criterio de registrar tambien lo que no cambia estado;
        un rechazo por regla de negocio es justamente eso.
        """
        try:
            validar_transicion(solicitud, evento, actor, **contexto)
        except Exception as exc:
            self._evento(
                accion,
                actor=actor,
                objetivo=objetivo,
                resultado="error",
                error=type(exc).__name__,
                regla=getattr(exc, "regla", None),
            )
            raise

    def _sincronizar_equipos(
        self,
        equipos: Iterable[Equipo],
        existentes: Iterable[Prestamo],
        prestamo_actual: Prestamo,
        hoy: date,
    ) -> None:
        """Recalcula el estado de cada equipo desde los compromisos vivos.

        `prestamo_actual` se pasa explicitamente para que el resultado no
        dependa de si la escritura de la solicitud ya aterrizo.
        """
        persistidos = list(existentes)
        for equipo in equipos:
            destino = estado_por_compromiso(
                equipo,
                persistidos,
                prestamo_actual=prestamo_actual,
                fecha_actual=hoy,
            )
            if destino is not equipo.estado:
                self._equipos.guardar(replace(equipo, estado=destino))

    def _resolver_equipos(
        self,
        codigos: Iterable[str],
        *,
        accion: str,
        actor: Usuario,
    ) -> dict[str, Equipo]:
        """Catalogo de los equipos nombrados, antes de escribir nada.

        Se resuelve por adelantado a proposito: si un codigo no existe, el
        `RecursoNoEncontrado` sale con la solicitud intacta.
        """
        catalogo: dict[str, Equipo] = {}
        for codigo in codigos:
            try:
                catalogo[codigo] = self._equipos.obtener(codigo)
            except Exception as exc:
                self._evento(
                    accion,
                    actor=actor,
                    resultado="error",
                    error=type(exc).__name__,
                    equipo=codigo,
                )
                raise
        return catalogo

    def _resolver_solicitante(self, solicitud: Prestamo, *, actor: Usuario) -> Usuario:
        """El duenno de la solicitud, que `_validar_aprobacion` necesita por RN-02."""
        try:
            return self._usuarios.obtener(solicitud.id_solicitante)
        except Exception as exc:
            self._evento(
                "solicitud_aprobada",
                actor=actor,
                objetivo=solicitud.id,
                resultado="error",
                error=type(exc).__name__,
                id_solicitante=solicitud.id_solicitante,
            )
            raise

    def _normalizar_codigos(self, equipos: Iterable[str]) -> tuple[str, ...]:
        if isinstance(equipos, str):
            raise ErrorValidacion(
                "El campo 'equipos' debe ser una lista de codigos, no un texto (RN-06).",
                regla="RN-06",
                detalles={"campo": "equipos", "recibido": equipos},
            )
        return tuple(normalizar_identificador(codigo) for codigo in equipos)

    def _siguiente_id(self, existentes: Iterable[Prestamo]) -> str:
        """Id secuencial `S-0001`, tomando el mayor sufijo numerico existente.

        Secuencial y no UUID porque la persistencia es JSON versionado y
        legible: el docstring de `json_repo.guardar` dice que la posicion de
        insercion se elige para que los diffs sigan siendo legibles, y un UUID
        de 36 caracteres en cada registro pelea contra eso.

        Los ids que no siguen el formato se ignoran para el maximo, en vez de
        romper: `solicitudes.json` puede venir editado a mano o con las
        fixtures `P-01` de las pruebas.

        Limitacion conocida: leer-decidir-escribir no es seguro con dos
        procesos simultaneos -ambos calcularian el mismo id siguiente, y la
        verificacion de abajo tambien compite-. Se acepta porque
        `_escribir_atomico` ya acota la durabilidad al uso monoproceso; es la
        instancia local del issue #49.
        """
        mayor = 0
        for prestamo in existentes:
            coincidencia = _SECUENCIA.match(prestamo.id.strip())
            if coincidencia is not None:
                mayor = max(mayor, int(coincidencia.group(1)))

        candidato = f"{PREFIJO_SOLICITUD}{mayor + 1:0{ANCHO_SECUENCIA}d}"
        if self._prestamos.buscar(candidato) is not None:
            raise ErrorValidacion(
                f"El identificador generado {candidato} ya esta ocupado (RN-17).",
                regla="RN-17",
                detalles={"id": candidato},
            )
        return candidato

    def _evento(
        self,
        accion: str,
        *,
        actor: Usuario | None,
        resultado: str = "ok",
        **contexto: object,
    ) -> None:
        registrar_evento(
            accion,
            usuario=actor.id if actor is not None else None,
            resultado=resultado,
            logger=self._logger,
            **{k: v for k, v in contexto.items() if v is not None},
        )
