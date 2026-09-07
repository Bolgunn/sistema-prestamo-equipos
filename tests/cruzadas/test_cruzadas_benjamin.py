from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pytest

from prestamos.auth import ServicioAuth
from prestamos.errores import ErrorAutorizacion, ErrorValidacion
from prestamos.modelos import EstadoEquipo, EstadoPrestamo, Rol
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.repositorios.json_repo import RepositorioJson
from prestamos.servicios.equipos import ServicioEquipos
from prestamos.servicios.solicitudes import ServicioSolicitudes
from prestamos.servicios.usuarios import ServicioUsuarios, crear_encargado_inicial

CONTRASENA = "Clave-Cruzada-2026"
FECHA_BASE = date(2026, 9, 7)
FECHA_APROBACION = date(2026, 9, 8)
FECHA_INICIO = date(2026, 9, 14)
FECHA_TERMINO = date(2026, 9, 16)


@dataclass
class SistemaCruzado:
    auth: ServicioAuth
    usuarios: ServicioUsuarios
    equipos: ServicioEquipos
    solicitudes: ServicioSolicitudes
    repo_usuarios: RepositorioJson
    repo_equipos: RepositorioJson
    repo_prestamos: RepositorioJson


@pytest.fixture
def sistema(tmp_path) -> SistemaCruzado:
    logger = logging.getLogger(f"prestamos.tests.cruzadas.{tmp_path.name}")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False

    repo_usuarios = repositorio_usuarios(tmp_path)
    repo_equipos = repositorio_equipos(tmp_path)
    repo_prestamos = repositorio_prestamos(tmp_path)

    crear_encargado_inicial(
        "enc-cruzado",
        "Encargada Cruzada",
        "enc.cruzado@usm.cl",
        CONTRASENA,
        repositorio=repo_usuarios,
        logger=logger,
        iteraciones_hash=1,
    )
    auth = ServicioAuth(repo_usuarios, logger=logger)
    usuarios = ServicioUsuarios(
        auth,
        repo_usuarios,
        logger=logger,
        iteraciones_hash=1,
    )
    equipos = ServicioEquipos(auth, repo_equipos, repo_prestamos, logger=logger)
    solicitudes = ServicioSolicitudes(
        auth,
        repo_prestamos,
        repo_equipos,
        repo_usuarios,
        logger=logger,
    )

    iniciar(auth, "enc-cruzado")
    usuarios.registrar_usuario(
        "sol-cruzado",
        "Solicitante Cruzada",
        "sol.cruzado@usm.cl",
        Rol.SOLICITANTE,
        CONTRASENA,
    )
    usuarios.registrar_usuario(
        "sol-otro",
        "Otra Solicitante",
        "sol.otra@usm.cl",
        Rol.SOLICITANTE,
        CONTRASENA,
    )
    for codigo in ("EQ-CX-01", "EQ-CX-02", "EQ-CX-03", "EQ-CX-04", "EQ-CX-05"):
        equipos.registrar_equipo(
            codigo,
            f"Equipo {codigo}",
            "Notebook",
            "Equipo temporal para pruebas cruzadas.",
        )
    auth.cerrar_sesion()

    return SistemaCruzado(
        auth=auth,
        usuarios=usuarios,
        equipos=equipos,
        solicitudes=solicitudes,
        repo_usuarios=repo_usuarios,
        repo_equipos=repo_equipos,
        repo_prestamos=repo_prestamos,
    )


def iniciar(auth: ServicioAuth, id_usuario: str) -> None:
    auth.cerrar_sesion()
    auth.iniciar_sesion(id_usuario, CONTRASENA)


def crear_solicitud(sistema: SistemaCruzado, codigo_equipo: str):
    iniciar(sistema.auth, "sol-cruzado")
    return sistema.solicitudes.crear_solicitud(
        [codigo_equipo],
        "Trabajo practico de laboratorio",
        FECHA_INICIO,
        FECHA_TERMINO,
        fecha_solicitud=FECHA_BASE,
    )


@pytest.mark.combinacion
def test_CX01_usuario_desactivado_bloquea_aprobacion_sin_reservar_equipo(
    sistema: SistemaCruzado,
) -> None:
    solicitud = crear_solicitud(sistema, "EQ-CX-01")

    iniciar(sistema.auth, "enc-cruzado")
    sistema.usuarios.desactivar("sol-cruzado")

    with pytest.raises(ErrorValidacion) as exc_info:
        sistema.solicitudes.aprobar(solicitud.id, fecha_aprobacion=FECHA_APROBACION)

    assert exc_info.value.regla == "RN-02"
    persistida = sistema.repo_prestamos.obtener(solicitud.id)
    equipo = sistema.repo_equipos.obtener("EQ-CX-01")
    solicitante = sistema.repo_usuarios.obtener("sol-cruzado")
    assert persistida.estado is EstadoPrestamo.SOLICITADA
    assert persistida.fecha_aprobacion is None
    assert equipo.estado is EstadoEquipo.DISPONIBLE
    assert solicitante.activo is False


@pytest.mark.combinacion
def test_CX02_equipo_en_mantencion_bloquea_aprobacion_sin_cambiar_solicitud(
    sistema: SistemaCruzado,
) -> None:
    solicitud = crear_solicitud(sistema, "EQ-CX-02")

    iniciar(sistema.auth, "enc-cruzado")
    sistema.equipos.enviar_a_mantencion("EQ-CX-02")

    with pytest.raises(ErrorValidacion) as exc_info:
        sistema.solicitudes.aprobar(solicitud.id, fecha_aprobacion=FECHA_APROBACION)

    assert exc_info.value.regla == "RN-05"
    persistida = sistema.repo_prestamos.obtener(solicitud.id)
    equipo = sistema.repo_equipos.obtener("EQ-CX-02")
    assert persistida.estado is EstadoPrestamo.SOLICITADA
    assert persistida.fecha_aprobacion is None
    assert equipo.estado is EstadoEquipo.MANTENCION


@pytest.mark.combinacion
def test_CX03_solicitud_aprobada_bloquea_baja_y_mantiene_reserva(
    sistema: SistemaCruzado,
) -> None:
    solicitud = crear_solicitud(sistema, "EQ-CX-03")

    iniciar(sistema.auth, "enc-cruzado")
    aprobada = sistema.solicitudes.aprobar(
        solicitud.id,
        fecha_aprobacion=FECHA_APROBACION,
    )

    with pytest.raises(ErrorValidacion) as exc_info:
        sistema.equipos.dar_de_baja("EQ-CX-03")

    assert exc_info.value.regla == "RN-21"
    persistida = sistema.repo_prestamos.obtener(solicitud.id)
    equipo = sistema.repo_equipos.obtener("EQ-CX-03")
    assert aprobada.estado is EstadoPrestamo.APROBADA
    assert persistida.estado is EstadoPrestamo.APROBADA
    assert equipo.estado is EstadoEquipo.RESERVADO


@pytest.mark.combinacion
def test_CX04_solicitud_rechazada_no_bloquea_baja_y_conserva_motivo(
    sistema: SistemaCruzado,
) -> None:
    solicitud = crear_solicitud(sistema, "EQ-CX-04")

    iniciar(sistema.auth, "enc-cruzado")
    rechazada = sistema.solicitudes.rechazar(
        solicitud.id,
        "No hay disponibilidad operativa para esta actividad.",
    )
    baja = sistema.equipos.dar_de_baja("EQ-CX-04")

    persistida = sistema.repo_prestamos.obtener(solicitud.id)
    equipo = sistema.repo_equipos.obtener("EQ-CX-04")
    assert rechazada.estado is EstadoPrestamo.RECHAZADA
    assert persistida.estado is EstadoPrestamo.RECHAZADA
    assert persistida.motivo_rechazo == "No hay disponibilidad operativa para esta actividad."
    assert baja.estado is EstadoEquipo.BAJA
    assert equipo.estado is EstadoEquipo.BAJA


@pytest.mark.combinacion
def test_CX05_usuario_promovido_no_puede_autoaprobar_y_no_reserva_equipo(
    sistema: SistemaCruzado,
) -> None:
    solicitud = crear_solicitud(sistema, "EQ-CX-05")

    iniciar(sistema.auth, "enc-cruzado")
    sistema.usuarios.editar_usuario("sol-cruzado", rol=Rol.ENCARGADO)
    iniciar(sistema.auth, "sol-cruzado")

    with pytest.raises(ErrorAutorizacion) as exc_info:
        sistema.solicitudes.aprobar(solicitud.id, fecha_aprobacion=FECHA_APROBACION)

    assert exc_info.value.regla == "RN-22"
    persistida = sistema.repo_prestamos.obtener(solicitud.id)
    equipo = sistema.repo_equipos.obtener("EQ-CX-05")
    usuario = sistema.repo_usuarios.obtener("sol-cruzado")
    assert persistida.estado is EstadoPrestamo.SOLICITADA
    assert persistida.fecha_aprobacion is None
    assert equipo.estado is EstadoEquipo.DISPONIBLE
    assert usuario.rol is Rol.ENCARGADO
