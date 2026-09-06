"""Casos negativos / entradas invalidas (minimo 3): CP-10 a CP-12.

Cada caso entra por la operacion real del servicio, no por el motor de reglas,
y afirma la terna completa de la excepcion de dominio -`codigo`, `regla` y
`mensaje` textual- mas los `detalles` que `ErrorDominio.para_log()` manda a los
logs y a Sentry. Afirmar el mensaje por igualdad y no por subcadena es
deliberado: `errores.py` establece que la CLI muestra solo `mensaje`, asi que
ese texto es interfaz de usuario y cambiarlo debe romper una prueba.

El idiom de `test_borde.py` -`assert "RN-XX" in mensaje`- no sirve aqui: los
mensajes de `auth.requiere_rol` y de la invariante de fechas de `Prestamo` no
nombran su regla, que solo vive en el atributo `.regla`.

CP-11 y CP-12 fijan ademas la guarda en su capa de origen con una segunda
asercion, porque la operacion de servicio corta antes de llegar a ella:
`aprobar()` es detenido por `auth` y nunca alcanza `_validar_usuario_operador`,
y `crear_solicitud()` revienta al construir el `Prestamo`.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest

from prestamos.auth import ServicioAuth, hash_contrasena
from prestamos.errores import ErrorAutorizacion, ErrorValidacion, TransicionNoPermitida
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.reglas import EventoTransicion, validar_transicion
from prestamos.repositorios.json_repo import RepositorioJson
from prestamos.servicios.prestamos import ServicioPrestamos
from prestamos.servicios.solicitudes import ServicioSolicitudes

CONTRASENA_NEGATIVA = "Clave-Negativa-2026"

# Jueves 10 de septiembre de 2026, la misma ancla que usan los casos
# funcionales y de borde. Ninguna prueba llama `date.today()`: si lo hiciera,
# RN-08 y RN-09 cambiarian de significado segun el dia en que corra la suite.
FECHA_CONTROL = date(2026, 9, 10)

# Logger propio, sin handlers de archivo. `registrar_evento` cae en
# `configurar_logging()` cuando no se le inyecta uno, y esa llamada abre un
# `FileHandler` sobre el logger de la aplicacion que sobrevive a la prueba.
# Un logger aislado con `NullHandler` evita el archivo y no deja nada que
# desmontar, que es lo que permite mantener este modulo sin fixtures.
_LOGGER_PRUEBAS = logging.getLogger("pruebas.negativos")
_LOGGER_PRUEBAS.addHandler(logging.NullHandler())
_LOGGER_PRUEBAS.propagate = False


def _usuario(
    id_usuario: str,
    *,
    rol: Rol,
    activo: bool = True,
) -> Usuario:
    return Usuario(
        id=id_usuario,
        nombre=f"Usuario negativo {id_usuario}",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        # `iteraciones=1`: la prueba necesita una credencial verificable, no una
        # resistente. `verificar_contrasena` lee el numero desde la propia
        # cadena, asi que la sesion se abre igual.
        hash_contrasena=hash_contrasena(CONTRASENA_NEGATIVA, iteraciones=1),
    )


def _encargado(id_usuario: str = "enc-negativo") -> Usuario:
    return _usuario(id_usuario, rol=Rol.ENCARGADO)


def _solicitante(id_usuario: str = "sol-negativo") -> Usuario:
    return _usuario(id_usuario, rol=Rol.SOLICITANTE)


def _equipo(
    codigo: str,
    *,
    estado: EstadoEquipo = EstadoEquipo.DISPONIBLE,
) -> Equipo:
    return Equipo(
        codigo=codigo,
        nombre=f"Equipo {codigo}",
        tipo="Notebook",
        descripcion="Equipo para caso negativo",
        estado=estado,
    )


def _prestamo(
    id_prestamo: str,
    *,
    id_solicitante: str = "sol-negativo",
    equipos: tuple[str, ...] = ("EQ-NEG-01",),
    estado: EstadoPrestamo = EstadoPrestamo.SOLICITADA,
    fecha_inicio: date = date(2026, 9, 14),
    fecha_termino: date = date(2026, 9, 16),
    fecha_solicitud: date = FECHA_CONTROL,
    fecha_aprobacion: date | None = None,
    fecha_entrega: date | None = None,
    fecha_devolucion: date | None = None,
) -> Prestamo:
    return Prestamo(
        id=id_prestamo,
        id_solicitante=id_solicitante,
        equipos=equipos,
        motivo="Caso negativo documentado",
        estado=estado,
        fecha_solicitud=fecha_solicitud,
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        fecha_aprobacion=fecha_aprobacion,
        fecha_entrega=fecha_entrega,
        fecha_devolucion=fecha_devolucion,
    )


def _repos_prestamos(tmp_path: Path) -> tuple[
    RepositorioJson[Prestamo],
    RepositorioJson[Equipo],
    ServicioPrestamos,
]:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    repo_equipos = RepositorioJson(tmp_path / "equipos.json", Equipo, "codigo")
    return repo_prestamos, repo_equipos, ServicioPrestamos(repo_prestamos, repo_equipos)


def _repos_solicitudes(tmp_path: Path) -> tuple[
    RepositorioJson[Prestamo],
    RepositorioJson[Equipo],
    RepositorioJson[Usuario],
    ServicioAuth,
    ServicioSolicitudes,
]:
    """Stack completo de solicitudes.

    `aprobar` y `crear_solicitud` no reciben al actor, lo sacan de
    `auth.requiere_rol(...)`, asi que hace falta un usuario persistido con hash
    real y una sesion abierta.
    """

    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    repo_equipos = RepositorioJson(tmp_path / "equipos.json", Equipo, "codigo")
    repo_usuarios = RepositorioJson(tmp_path / "usuarios.json", Usuario, "id")
    auth = ServicioAuth(repo_usuarios, logger=_LOGGER_PRUEBAS)
    servicio = ServicioSolicitudes(
        auth,
        repo_prestamos,
        repo_equipos,
        repo_usuarios,
        logger=_LOGGER_PRUEBAS,
    )
    return repo_prestamos, repo_equipos, repo_usuarios, auth, servicio


@pytest.mark.negativo
def test_CP10_RF10_devolver_prestamo_aprobado_nunca_entregado_rechaza_por_rn14(
    tmp_path: Path,
) -> None:
    """RN-14: solo se devuelve lo que se entrego.

    El estado origen es `APROBADA` y no `SOLICITADA` a proposito: es el unico
    donde la asercion de no-efecto tiene mordida, porque el equipo esta
    `RESERVADO` y una devolucion indebida liberaria una reserva viva.

    La fecha de devolucion es posterior al termino, de modo que el caso prueba
    ademas que `_preparar_atraso_si_corresponde` no promueve un `APROBADA` a
    `ATRASADA`: nunca hubo custodia fisica, asi que no hay atraso que marcar.
    """

    repo_prestamos, repo_equipos, servicio = _repos_prestamos(tmp_path)
    original = _prestamo(
        "PREST-NUNCA-ENTREGADO",
        estado=EstadoPrestamo.APROBADA,
        fecha_inicio=date(2026, 9, 7),
        fecha_termino=date(2026, 9, 9),
        fecha_aprobacion=date(2026, 9, 4),
    )
    repo_prestamos.guardar(original)
    repo_equipos.guardar(_equipo("EQ-NEG-01", estado=EstadoEquipo.RESERVADO))

    with pytest.raises(TransicionNoPermitida) as exc_info:
        servicio.registrar_devolucion(
            "PREST-NUNCA-ENTREGADO",
            _encargado(),
            fecha_devolucion=FECHA_CONTROL,
        )

    error = exc_info.value
    assert error.codigo == "TRANSICION_NO_PERMITIDA"
    assert error.regla == "RN-14"
    assert error.mensaje == (
        "La transicion REGISTRAR_DEVOLUCION no esta permitida desde APROBADA (RN-14)."
    )
    assert error.detalles == {
        "estado": "APROBADA",
        "evento": "REGISTRAR_DEVOLUCION",
    }
    assert repo_prestamos.obtener("PREST-NUNCA-ENTREGADO") == original
    assert repo_prestamos.obtener("PREST-NUNCA-ENTREGADO").estado is EstadoPrestamo.APROBADA
    assert repo_equipos.obtener("EQ-NEG-01").estado is EstadoEquipo.RESERVADO


@pytest.mark.negativo
def test_CP11_RF08_solicitante_no_puede_aprobar_solicitud_por_rn11(
    tmp_path: Path,
) -> None:
    """RN-11: aprobar es exclusivo del Encargado, en las dos capas que lo guardan.

    `aprobar()` llama `auth.requiere_rol(Rol.ENCARGADO)` en su primera linea,
    antes de leer la solicitud, asi que el mensaje alcanzable por el servicio es
    el generico de autorizacion. La segunda asercion invoca el motor
    directamente para dejar constancia de que la guarda de dominio existe, es
    redundante y da el mensaje especifico con rol y transicion.
    """

    repo_prestamos, repo_equipos, repo_usuarios, auth, servicio = _repos_solicitudes(
        tmp_path
    )
    solicitante = _solicitante()
    repo_usuarios.guardar(solicitante)
    repo_equipos.guardar(_equipo("EQ-NEG-01"))
    original = _prestamo("S-0001", estado=EstadoPrestamo.SOLICITADA)
    repo_prestamos.guardar(original)
    auth.iniciar_sesion(solicitante.id, CONTRASENA_NEGATIVA)

    with pytest.raises(ErrorAutorizacion) as exc_servicio:
        servicio.aprobar("S-0001", fecha_aprobacion=FECHA_CONTROL)

    error_servicio = exc_servicio.value
    assert error_servicio.codigo == "ERROR_AUTORIZACION"
    assert error_servicio.regla == "RN-11"
    assert error_servicio.mensaje == "No tiene permisos para realizar esta operacion."
    assert error_servicio.detalles == {
        "rol_actual": "SOLICITANTE",
        "roles_requeridos": ["ENCARGADO"],
    }
    assert repo_prestamos.obtener("S-0001") == original
    assert repo_prestamos.obtener("S-0001").estado is EstadoPrestamo.SOLICITADA
    assert repo_equipos.obtener("EQ-NEG-01").estado is EstadoEquipo.DISPONIBLE

    with pytest.raises(ErrorAutorizacion) as exc_motor:
        validar_transicion(
            original,
            EventoTransicion.APROBAR_SOLICITUD,
            solicitante,
            fecha_actual=FECHA_CONTROL,
        )

    error_motor = exc_motor.value
    assert error_motor.codigo == "ERROR_AUTORIZACION"
    assert error_motor.regla == "RN-11"
    assert error_motor.mensaje == (
        "El rol SOLICITANTE no esta autorizado para APROBAR_SOLICITUD (RN-11)."
    )
    assert error_motor.detalles == {
        "usuario": "sol-negativo",
        "rol": "SOLICITANTE",
        "roles_autorizados": ["ENCARGADO"],
        "transicion": "T-02",
    }


@pytest.mark.negativo
def test_CP12_RF05_fecha_termino_anterior_al_inicio_rechaza_por_rn17(
    tmp_path: Path,
) -> None:
    """RN-17: la operacion invalida se rechaza antes de persistir.

    La invariante vive en `Prestamo.__post_init__`, pero llega por la puerta del
    usuario: `crear_solicitud` recibe las fechas sueltas y construye la entidad
    adentro. Por eso el caso entra por el servicio y afirma que no quedo nada en
    el JSON ni se consumio el correlativo, y recien despues ancla la invariante
    en el constructor del modelo, que hoy ninguna prueba ejercita directamente.
    """

    repo_prestamos, repo_equipos, repo_usuarios, auth, servicio = _repos_solicitudes(
        tmp_path
    )
    solicitante = _solicitante()
    repo_usuarios.guardar(solicitante)
    repo_equipos.guardar(_equipo("EQ-NEG-01"))
    auth.iniciar_sesion(solicitante.id, CONTRASENA_NEGATIVA)

    with pytest.raises(ErrorValidacion) as exc_servicio:
        servicio.crear_solicitud(
            ["EQ-NEG-01"],
            "Practico de laboratorio con fechas invertidas",
            date(2026, 9, 18),
            date(2026, 9, 14),
            fecha_solicitud=FECHA_CONTROL,
        )

    error_servicio = exc_servicio.value
    assert error_servicio.codigo == "ERROR_VALIDACION"
    assert error_servicio.regla == "RN-17"
    assert error_servicio.mensaje == (
        "La fecha de inicio no puede ser posterior a la fecha de termino."
    )
    assert error_servicio.detalles == {
        "fecha_inicio": "2026-09-18",
        "fecha_termino": "2026-09-14",
    }
    assert repo_prestamos.listar() == []

    # El correlativo no se consumio: la primera solicitud valida sigue siendo
    # `S-0001`. `_siguiente_id` lo deriva del repositorio, asi que un rechazo
    # que hubiera persistido algo se delataria aqui.
    valida = servicio.crear_solicitud(
        ["EQ-NEG-01"],
        "Practico de laboratorio con fechas correctas",
        date(2026, 9, 14),
        date(2026, 9, 16),
        fecha_solicitud=FECHA_CONTROL,
    )
    assert valida.id == "S-0001"
    assert [solicitud.id for solicitud in repo_prestamos.listar()] == ["S-0001"]

    with pytest.raises(ErrorValidacion) as exc_modelo:
        _prestamo(
            "S-9999",
            fecha_inicio=date(2026, 9, 18),
            fecha_termino=date(2026, 9, 14),
        )

    error_modelo = exc_modelo.value
    assert error_modelo.codigo == "ERROR_VALIDACION"
    assert error_modelo.regla == "RN-17"
    assert error_modelo.mensaje == error_servicio.mensaje
    assert error_modelo.detalles == error_servicio.detalles
