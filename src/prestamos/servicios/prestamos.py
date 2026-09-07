"""Caso de uso de entrega, devolucion, atraso, cancelacion y consultas.

Este servicio orquesta persistencia JSON y motor de reglas. No decide si una
transicion es valida por su cuenta: antes de guardar cualquier cambio llama a
``prestamos.reglas.validar_transicion`` con el contexto necesario. Las mutaciones
registran eventos de auditoria por RN-18. Las consultas clasifican por RN-16 y
aplican visibilidad por rol segun RN-19; no registran eventos para evitar ruido,
porque solo leen datos y no cambian inventario ni estado de prestamos.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import logging
from pathlib import Path
from typing import Any, Callable, Iterable

from prestamos.errores import ErrorAutorizacion, ErrorDominio, ErrorValidacion
from prestamos.logging_conf import registrar_evento
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.reglas import (
    EventoTransicion,
    estado_por_compromiso,
    validar_transicion,
)
from prestamos.repositorios.fabricas import repositorio_equipos, repositorio_prestamos
from prestamos.repositorios.json_repo import RepositorioJson


class ServicioPrestamos:
    """Operaciones sobre prestamos existentes respaldadas por JSON."""

    def __init__(
        self,
        repo_prestamos: RepositorioJson[Prestamo] | None = None,
        repo_equipos: RepositorioJson[Equipo] | None = None,
        *,
        datos_dir: str | Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repo_prestamos = repo_prestamos or repositorio_prestamos(datos_dir)
        self.repo_equipos = repo_equipos or repositorio_equipos(datos_dir)
        self._logger = logger

    def registrar_entrega(
        self,
        id_prestamo: str,
        encargado: Usuario,
        *,
        fecha_entrega: date | None = None,
    ) -> Prestamo:
        """Registra T-06: APROBADA -> ENTREGADA (RN-13)."""

        prestamo: Prestamo | None = None
        equipos: dict[str, Equipo] = {}
        fecha = fecha_entrega or date.today()
        try:
            prestamo = self.repo_prestamos.obtener(id_prestamo)
            equipos = self._equipos_de(prestamo)

            validar_transicion(
                prestamo,
                EventoTransicion.REGISTRAR_ENTREGA,
                encargado,
                fecha_actual=fecha,
                fecha_operacion=fecha,
                equipos=equipos,
            )

            actualizado = replace(
                prestamo,
                estado=EstadoPrestamo.ENTREGADA,
                fecha_entrega=fecha,
            )
            self.repo_prestamos.guardar(actualizado)
            self._marcar_equipos(equipos.values(), EstadoEquipo.PRESTADO)
            self._evento_ok(
                "prestamo_entrega",
                actor=encargado,
                prestamo=actualizado,
                equipos=equipos,
                fecha_entrega=fecha.isoformat(),
            )
            return actualizado
        except ErrorDominio as exc:
            self._evento_error(
                "prestamo_entrega",
                actor=encargado,
                id_prestamo=id_prestamo,
                prestamo=prestamo,
                equipos=equipos,
                error=exc,
            )
            raise

    def registrar_devolucion(
        self,
        id_prestamo: str,
        encargado: Usuario,
        *,
        fecha_devolucion: date | None = None,
        equipos_devueltos: Iterable[str] | None = None,
    ) -> Prestamo:
        """Registra T-08 o T-09 y libera equipos al devolver (RN-14/RN-16)."""

        prestamo: Prestamo | None = None
        prestamo_a_devolver: Prestamo | None = None
        equipos: dict[str, Equipo] = {}
        fecha = fecha_devolucion or date.today()
        devueltos: tuple[str, ...] = ()
        try:
            prestamo = self.repo_prestamos.obtener(id_prestamo)
            devueltos = tuple(prestamo.equipos if equipos_devueltos is None else equipos_devueltos)

            prestamo_a_devolver, requiere_marcar_atraso = self._preparar_atraso_si_corresponde(
                prestamo, fecha
            )
            evento = (
                EventoTransicion.REGISTRAR_DEVOLUCION_ATRASADA
                if prestamo_a_devolver.estado is EstadoPrestamo.ATRASADA
                else EventoTransicion.REGISTRAR_DEVOLUCION
            )

            validar_transicion(
                prestamo_a_devolver,
                evento,
                encargado,
                fecha_actual=fecha,
                fecha_operacion=fecha,
                equipos_devueltos=devueltos,
            )
            equipos = self._equipos_de(prestamo_a_devolver)
            existentes = self.repo_prestamos.listar()

            actualizado = replace(
                prestamo_a_devolver,
                estado=EstadoPrestamo.DEVUELTA,
                fecha_devolucion=fecha,
            )
            if requiere_marcar_atraso:
                self.repo_prestamos.guardar(prestamo_a_devolver)
            self.repo_prestamos.guardar(actualizado)
            self._sincronizar_equipos(equipos.values(), existentes, actualizado, fecha)
            self._evento_ok(
                "prestamo_devolucion",
                actor=encargado,
                prestamo=actualizado,
                equipos=equipos,
                fecha_devolucion=fecha.isoformat(),
                equipos_devueltos=list(devueltos),
                atraso_intermedio=requiere_marcar_atraso,
            )
            return actualizado
        except ErrorDominio as exc:
            self._evento_error(
                "prestamo_devolucion",
                actor=encargado,
                id_prestamo=id_prestamo,
                prestamo=prestamo_a_devolver or prestamo,
                equipos=equipos,
                error=exc,
                equipos_devueltos=list(devueltos),
            )
            raise

    def cancelar(
        self,
        id_prestamo: str,
        usuario: Usuario,
        motivo: str | None,
        *,
        fecha_actual: date | None = None,
    ) -> Prestamo:
        """Registra T-04 o T-05 antes de la entrega, con motivo (RN-15).

        `fecha_actual` es opcional y solo se usa para recalcular el estado de
        los equipos liberados: una reserva ajena ya vencida no debe dejarlos
        RESERVADO. Se inyecta por la misma razon que `fecha_entrega` y
        `fecha_devolucion`, para que las pruebas no dependan del dia en que
        corran.
        """

        prestamo: Prestamo | None = None
        equipos: dict[str, Equipo] = {}
        hoy = fecha_actual or date.today()
        try:
            prestamo = self.repo_prestamos.obtener(id_prestamo)
            validar_transicion(
                prestamo,
                EventoTransicion.CANCELAR_SOLICITUD,
                usuario,
                fecha_actual=hoy,
                motivo_cancelacion=motivo,
            )
            equipos = (
                self._equipos_de(prestamo)
                if prestamo.estado is EstadoPrestamo.APROBADA
                else {}
            )
            existentes = self.repo_prestamos.listar()

            actualizado = replace(
                prestamo,
                estado=EstadoPrestamo.CANCELADA,
                motivo_cancelacion=motivo,
            )
            self.repo_prestamos.guardar(actualizado)
            if prestamo.estado is EstadoPrestamo.APROBADA:
                self._sincronizar_equipos(equipos.values(), existentes, actualizado, hoy)
            self._evento_ok(
                "prestamo_cancelacion",
                actor=usuario,
                prestamo=actualizado,
                equipos=equipos,
                motivo_cancelacion=motivo,
                fecha_actual=hoy.isoformat(),
            )
            return actualizado
        except ErrorDominio as exc:
            self._evento_error(
                "prestamo_cancelacion",
                actor=usuario,
                id_prestamo=id_prestamo,
                prestamo=prestamo,
                equipos=equipos,
                error=exc,
            )
            raise

    def marcar_atraso(
        self,
        id_prestamo: str,
        *,
        usuario: Usuario | None = None,
        fecha_actual: date | None = None,
    ) -> Prestamo:
        """Registra T-07: ENTREGADA -> ATRASADA (RN-16)."""

        prestamo: Prestamo | None = None
        fecha = fecha_actual or date.today()
        try:
            prestamo = self.repo_prestamos.obtener(id_prestamo)
            validar_transicion(
                prestamo,
                EventoTransicion.MARCAR_ATRASO,
                usuario,
                fecha_actual=fecha,
            )
            actualizado = replace(prestamo, estado=EstadoPrestamo.ATRASADA)
            self.repo_prestamos.guardar(actualizado)
            self._evento_ok(
                "prestamo_atraso",
                actor=usuario,
                prestamo=actualizado,
                fecha_actual=fecha.isoformat(),
            )
            return actualizado
        except ErrorDominio as exc:
            self._evento_error(
                "prestamo_atraso",
                actor=usuario,
                id_prestamo=id_prestamo,
                prestamo=prestamo,
                error=exc,
            )
            raise

    def prestamos_futuros(
        self,
        usuario: Usuario | None,
        *,
        fecha_actual: date | None = None,
        id_usuario: str | None = None,
        codigo_equipo: str | None = None,
    ) -> list[Prestamo]:
        """Consulta futuros: APROBADA con inicio posterior a hoy (RN-16/RN-19)."""

        hoy = fecha_actual or date.today()
        return self._consultar(
            usuario,
            id_usuario=id_usuario,
            codigo_equipo=codigo_equipo,
            clasificador=lambda prestamo: (
                prestamo.estado is EstadoPrestamo.APROBADA
                and prestamo.fecha_inicio > hoy
            ),
        )

    def prestamos_vigentes(
        self,
        usuario: Usuario | None,
        *,
        fecha_actual: date | None = None,
        id_usuario: str | None = None,
        codigo_equipo: str | None = None,
    ) -> list[Prestamo]:
        """Consulta vigentes: ENTREGADA sin devolucion y dentro del plazo (RN-16/RN-19)."""

        hoy = fecha_actual or date.today()
        return self._consultar(
            usuario,
            id_usuario=id_usuario,
            codigo_equipo=codigo_equipo,
            clasificador=lambda prestamo: (
                prestamo.estado is EstadoPrestamo.ENTREGADA
                and prestamo.fecha_devolucion is None
                and prestamo.fecha_inicio <= hoy <= prestamo.fecha_termino
            ),
        )

    def prestamos_atrasados(
        self,
        usuario: Usuario | None,
        *,
        fecha_actual: date | None = None,
        id_usuario: str | None = None,
        codigo_equipo: str | None = None,
    ) -> list[Prestamo]:
        """Consulta atrasados sin modificar estados persistidos (RN-16/RN-19)."""

        hoy = fecha_actual or date.today()
        return self._consultar(
            usuario,
            id_usuario=id_usuario,
            codigo_equipo=codigo_equipo,
            clasificador=lambda prestamo: (
                prestamo.fecha_devolucion is None
                and (
                    prestamo.estado is EstadoPrestamo.ATRASADA
                    or (
                        prestamo.estado is EstadoPrestamo.ENTREGADA
                        and prestamo.fecha_termino < hoy
                    )
                )
            ),
        )


    def _evento_ok(
        self,
        accion: str,
        *,
        actor: Usuario | None,
        prestamo: Prestamo,
        equipos: dict[str, Equipo] | None = None,
        **contexto: Any,
    ) -> None:
        self._registrar_evento_seguro(
            accion,
            actor=actor,
            resultado="ok",
            id_prestamo=prestamo.id,
            id_solicitante=prestamo.id_solicitante,
            equipos=list((equipos or {}).keys()) or list(prestamo.equipos),
            estado=prestamo.estado.value,
            **contexto,
        )

    def _evento_error(
        self,
        accion: str,
        *,
        actor: Usuario | None,
        id_prestamo: str,
        error: ErrorDominio,
        prestamo: Prestamo | None = None,
        equipos: dict[str, Equipo] | None = None,
        **contexto: Any,
    ) -> None:
        self._registrar_evento_seguro(
            accion,
            actor=actor,
            resultado="error",
            id_prestamo=prestamo.id if prestamo is not None else id_prestamo,
            id_solicitante=prestamo.id_solicitante if prestamo is not None else None,
            equipos=list((equipos or {}).keys())
            or (list(prestamo.equipos) if prestamo is not None else []),
            estado=prestamo.estado.value if prestamo is not None else None,
            motivo_error=error.para_log(),
            **contexto,
        )

    def _registrar_evento_seguro(
        self,
        accion: str,
        *,
        actor: Usuario | None,
        resultado: str,
        **contexto: Any,
    ) -> None:
        try:
            registrar_evento(
                accion,
                usuario=actor.id if actor is not None else None,
                resultado=resultado,
                logger=self._logger,
                **contexto,
            )
        except Exception:
            # La auditoria no debe cambiar el resultado de la operacion ni
            # reemplazar el ErrorDominio original por un problema del logger.
            pass

    def _preparar_atraso_si_corresponde(
        self,
        prestamo: Prestamo,
        fecha: date,
    ) -> tuple[Prestamo, bool]:
        if (
            prestamo.estado is EstadoPrestamo.ENTREGADA
            and prestamo.fecha_devolucion is None
            and fecha > prestamo.fecha_termino
        ):
            validar_transicion(
                prestamo,
                EventoTransicion.MARCAR_ATRASO,
                None,
                fecha_actual=fecha,
            )
            return replace(prestamo, estado=EstadoPrestamo.ATRASADA), True
        return prestamo, False

    def _consultar(
        self,
        usuario: Usuario | None,
        *,
        id_usuario: str | None,
        codigo_equipo: str | None,
        clasificador: Callable[[Prestamo], bool],
    ) -> list[Prestamo]:
        id_filtrado = self._id_usuario_visible(usuario, id_usuario)
        equipo_filtrado = self._filtro_texto(codigo_equipo, "codigo_equipo")
        resultado: list[Prestamo] = []
        for prestamo in self.repo_prestamos.listar():
            if id_filtrado is not None and prestamo.id_solicitante != id_filtrado:
                continue
            if equipo_filtrado is not None and equipo_filtrado not in prestamo.equipos:
                continue
            if clasificador(prestamo):
                resultado.append(prestamo)
        return resultado

    def _id_usuario_visible(
        self,
        usuario: Usuario | None,
        id_usuario: str | None,
    ) -> str | None:
        if usuario is None:
            raise ErrorAutorizacion(
                "La consulta requiere un usuario autenticado (RN-02).",
                regla="RN-02",
            )
        if not usuario.activo:
            raise ErrorAutorizacion(
                "El usuario debe estar activo para consultar prestamos (RN-02).",
                regla="RN-02",
                detalles={"usuario": usuario.id},
            )

        id_filtrado = self._filtro_texto(id_usuario, "id_usuario")
        if usuario.rol is Rol.SOLICITANTE:
            if id_filtrado is not None and id_filtrado != usuario.id:
                raise ErrorAutorizacion(
                    "El solicitante solo puede consultar sus propios prestamos (RN-19).",
                    regla="RN-19",
                    detalles={"usuario": usuario.id, "id_usuario": id_filtrado},
                )
            return usuario.id
        if usuario.rol is Rol.ENCARGADO:
            return id_filtrado

        # Defensa ante datos inconsistentes o futuras extensiones de Rol: hoy
        # solo existen SOLICITANTE y ENCARGADO, cubiertos arriba.
        raise ErrorAutorizacion(
            "El rol del usuario no esta autorizado para consultar prestamos (RN-01).",
            regla="RN-01",
            detalles={"rol": getattr(usuario.rol, "value", usuario.rol)},
        )

    def _filtro_texto(self, valor: str | None, campo: str) -> str | None:
        if valor is None:
            return None
        if not isinstance(valor, str) or not valor.strip():
            raise ErrorValidacion(
                f"El filtro '{campo}' no puede estar vacio (RN-17).",
                regla="RN-17",
                detalles={"campo": campo},
            )
        return valor.strip()

    def _equipos_de(self, prestamo: Prestamo) -> dict[str, Equipo]:
        return {codigo: self.repo_equipos.obtener(codigo) for codigo in prestamo.equipos}

    def _marcar_equipos(
        self,
        equipos: Iterable[Equipo],
        estado: EstadoEquipo,
    ) -> None:
        for equipo in equipos:
            self.repo_equipos.guardar(replace(equipo, estado=estado))

    def _sincronizar_equipos(
        self,
        equipos: Iterable[Equipo],
        existentes: Iterable[Prestamo],
        prestamo_actual: Prestamo,
        hoy: date,
    ) -> None:
        """Recalcula el estado de cada equipo desde los compromisos que quedan.

        Reemplaza dos escrituras que decidian a ciegas y se equivocaban en
        cuanto un equipo tenia mas de un prestamo:

        - la cancelacion escribia `RESERVADO -> DISPONIBLE` aunque otra reserva
          siguiera viva;
        - la devolucion escribia `DISPONIBLE` y borraba el `RESERVADO` que otra
          solicitud aprobada todavia justificaba.

        Ninguna de las dos se notaba mientras nadie escribiera `RESERVADO`. La
        aprobacion (#11) ya lo escribe.

        `prestamo_actual` es el prestamo que esta operacion acaba de decidir, y
        se pasa explicitamente para que el resultado no dependa de si la
        escritura ya aterrizo.
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
                self.repo_equipos.guardar(replace(equipo, estado=destino))


def crear_servicio_prestamos(
    *,
    datos_dir: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> ServicioPrestamos:
    return ServicioPrestamos(datos_dir=datos_dir, logger=logger)


def registrar_entrega(
    id_prestamo: str,
    encargado: Usuario,
    *,
    fecha_entrega: date | None = None,
    datos_dir: str | Path | None = None,
) -> Prestamo:
    return crear_servicio_prestamos(datos_dir=datos_dir).registrar_entrega(
        id_prestamo,
        encargado,
        fecha_entrega=fecha_entrega,
    )


def registrar_devolucion(
    id_prestamo: str,
    encargado: Usuario,
    *,
    fecha_devolucion: date | None = None,
    equipos_devueltos: Iterable[str] | None = None,
    datos_dir: str | Path | None = None,
) -> Prestamo:
    return crear_servicio_prestamos(datos_dir=datos_dir).registrar_devolucion(
        id_prestamo,
        encargado,
        fecha_devolucion=fecha_devolucion,
        equipos_devueltos=equipos_devueltos,
    )


def cancelar(
    id_prestamo: str,
    usuario: Usuario,
    motivo: str | None,
    *,
    fecha_actual: date | None = None,
    datos_dir: str | Path | None = None,
) -> Prestamo:
    return crear_servicio_prestamos(datos_dir=datos_dir).cancelar(
        id_prestamo,
        usuario,
        motivo,
        fecha_actual=fecha_actual,
    )


def marcar_atraso(
    id_prestamo: str,
    *,
    usuario: Usuario | None = None,
    fecha_actual: date | None = None,
    datos_dir: str | Path | None = None,
) -> Prestamo:
    return crear_servicio_prestamos(datos_dir=datos_dir).marcar_atraso(
        id_prestamo,
        usuario=usuario,
        fecha_actual=fecha_actual,
    )


def prestamos_futuros(
    usuario: Usuario | None,
    *,
    fecha_actual: date | None = None,
    id_usuario: str | None = None,
    codigo_equipo: str | None = None,
    datos_dir: str | Path | None = None,
) -> list[Prestamo]:
    return crear_servicio_prestamos(datos_dir=datos_dir).prestamos_futuros(
        usuario,
        fecha_actual=fecha_actual,
        id_usuario=id_usuario,
        codigo_equipo=codigo_equipo,
    )


def prestamos_vigentes(
    usuario: Usuario | None,
    *,
    fecha_actual: date | None = None,
    id_usuario: str | None = None,
    codigo_equipo: str | None = None,
    datos_dir: str | Path | None = None,
) -> list[Prestamo]:
    return crear_servicio_prestamos(datos_dir=datos_dir).prestamos_vigentes(
        usuario,
        fecha_actual=fecha_actual,
        id_usuario=id_usuario,
        codigo_equipo=codigo_equipo,
    )


def prestamos_atrasados(
    usuario: Usuario | None,
    *,
    fecha_actual: date | None = None,
    id_usuario: str | None = None,
    codigo_equipo: str | None = None,
    datos_dir: str | Path | None = None,
) -> list[Prestamo]:
    return crear_servicio_prestamos(datos_dir=datos_dir).prestamos_atrasados(
        usuario,
        fecha_actual=fecha_actual,
        id_usuario=id_usuario,
        codigo_equipo=codigo_equipo,
    )
