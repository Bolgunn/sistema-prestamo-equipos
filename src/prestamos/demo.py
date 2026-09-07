"""Datos de demostracion reproducibles para el revisor (issue #15)."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from prestamos.auth import ServicioAuth
from prestamos.modelos import Rol
from prestamos.repositorios.fabricas import (
    ARCHIVO_EQUIPOS,
    ARCHIVO_PRESTAMOS,
    ARCHIVO_USUARIOS,
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.servicios.equipos import ServicioEquipos
from prestamos.servicios.prestamos import ServicioPrestamos
from prestamos.servicios.solicitudes import ServicioSolicitudes
from prestamos.servicios.usuarios import ServicioUsuarios, crear_encargado_inicial

RUTA_DEMO_DEFAULT = Path("datos") / "demo"
ARCHIVOS_DEMO = (ARCHIVO_USUARIOS, ARCHIVO_EQUIPOS, ARCHIVO_PRESTAMOS)
FECHA_REFERENCIA_DEMO = date(2026, 9, 10)

ID_ENCARGADO_DEMO = "enc-demo"
CLAVE_ENCARGADO_DEMO = "DemoEncargado2026!"
ID_SOLICITANTE_DEMO = "sol-demo"
CLAVE_SOLICITANTE_DEMO = "DemoSolicitante2026!"
ID_SOLICITANTE_ALTERNO_DEMO = "sol-demo-2"
CLAVE_SOLICITANTE_ALTERNO_DEMO = "DemoSolicitante2026!"

_HASH_ENCARGADO_DEMO = (
    "pbkdf2_sha256$200000$000102030405060708090a0b0c0d0e0f"
    "$fe248f964766aa3bb514bb0142b74111280ba19112e9b34cc69f3e5084d3e0f1"
)
_HASH_SOLICITANTE_DEMO = (
    "pbkdf2_sha256$200000$101112131415161718191a1b1c1d1e1f"
    "$4b31aba34cba68704d7ab7eea00603cfc6083da3424c178d211836dcd3261a53"
)
_HASH_SOLICITANTE_ALTERNO_DEMO = (
    "pbkdf2_sha256$200000$202122232425262728292a2b2c2d2e2f"
    "$f4cfff878244de9ecdd54f2397bcf213279985fff0a5d4c8669c08a866e21af5"
)


@dataclass(frozen=True)
class ResultadoInitDemo:
    """Resultado automatizable del comando init-demo."""

    ruta: Path
    creado: bool
    sobrescrito: bool
    mensaje: str


def inicializar_datos_demo(
    datos_dir: str | Path | None = None,
    *,
    sobrescribir: bool = False,
) -> ResultadoInitDemo:
    """Crea o regenera el dataset demo sin destruirlo silenciosamente."""

    destino = Path(datos_dir) if datos_dir is not None else RUTA_DEMO_DEFAULT
    destino = destino.resolve()
    existen_datos = _existen_archivos_demo(destino)

    if existen_datos and not sobrescribir:
        return ResultadoInitDemo(
            ruta=destino,
            creado=False,
            sobrescrito=False,
            mensaje=(
                f"Los datos de demostracion ya existen en {destino}. "
                "Use init-demo --force para regenerarlos."
            ),
        )

    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destino.name}.", dir=destino.parent) as temporal:
        temporal_path = Path(temporal)
        _generar_dataset(temporal_path)
        destino.mkdir(parents=True, exist_ok=True)
        for nombre in ARCHIVOS_DEMO:
            os.replace(temporal_path / nombre, destino / nombre)

    sobrescrito = existen_datos and sobrescribir
    return ResultadoInitDemo(
        ruta=destino,
        creado=not sobrescrito,
        sobrescrito=sobrescrito,
        mensaje=(
            f"Datos de demostracion regenerados en {destino}."
            if sobrescrito
            else f"Datos de demostracion creados en {destino}."
        ),
    )


def _existen_archivos_demo(destino: Path) -> bool:
    return any((destino / nombre).exists() for nombre in ARCHIVOS_DEMO)


def _generar_dataset(datos_dir: Path) -> None:
    logger = _logger_silencioso()
    repo_usuarios = repositorio_usuarios(datos_dir)
    repo_equipos = repositorio_equipos(datos_dir)
    repo_prestamos = repositorio_prestamos(datos_dir)

    encargado = crear_encargado_inicial(
        ID_ENCARGADO_DEMO,
        "Encargada Demo",
        "enc.demo@usm.cl",
        CLAVE_ENCARGADO_DEMO,
        repositorio=repo_usuarios,
        logger=logger,
    )
    repo_usuarios.guardar(
        replace(encargado, hash_contrasena=_HASH_ENCARGADO_DEMO)
    )

    auth = ServicioAuth(repo_usuarios, logger=logger)
    usuarios = ServicioUsuarios(auth, repo_usuarios, logger=logger)
    equipos = ServicioEquipos(auth, repo_equipos, repo_prestamos, logger=logger)
    solicitudes = ServicioSolicitudes(
        auth,
        repo_prestamos,
        repo_equipos,
        repo_usuarios,
        logger=logger,
    )
    prestamos = ServicioPrestamos(repo_prestamos, repo_equipos)

    auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO)
    solicitante = usuarios.registrar_usuario(
        ID_SOLICITANTE_DEMO,
        "Solicitante Demo",
        "sol.demo@usm.cl",
        Rol.SOLICITANTE,
        CLAVE_SOLICITANTE_DEMO,
    )
    repo_usuarios.guardar(
        replace(solicitante, hash_contrasena=_HASH_SOLICITANTE_DEMO)
    )
    solicitante_alterno = usuarios.registrar_usuario(
        ID_SOLICITANTE_ALTERNO_DEMO,
        "Solicitante Alterno Demo",
        "sol.demo2@usm.cl",
        Rol.SOLICITANTE,
        CLAVE_SOLICITANTE_ALTERNO_DEMO,
    )
    repo_usuarios.guardar(
        replace(
            solicitante_alterno,
            hash_contrasena=_HASH_SOLICITANTE_ALTERNO_DEMO,
        )
    )
    for codigo, nombre, tipo in (
        ("EQ-DEMO-01", "Notebook Dell Latitude", "Notebook"),
        ("EQ-DEMO-02", "Proyector Epson", "Proyector"),
        ("EQ-DEMO-03", "Kit Arduino", "Electronica"),
        ("EQ-DEMO-04", "Camara Sony", "Audiovisual"),
        ("EQ-DEMO-05", "Multimetro Fluke", "Instrumentacion"),
    ):
        equipos.registrar_equipo(
            codigo,
            nombre,
            tipo,
            "Equipo de demostracion para pruebas manuales y automatizadas.",
        )

    auth.cerrar_sesion()
    auth.iniciar_sesion(ID_SOLICITANTE_DEMO, CLAVE_SOLICITANTE_DEMO)
    solicitudes.crear_solicitud(
        ["EQ-DEMO-01"],
        "Reserva pendiente para revisar el flujo de aprobacion.",
        date(2026, 9, 28),
        date(2026, 9, 30),
        fecha_solicitud=date(2026, 9, 7),
    )
    solicitud_aprobada = solicitudes.crear_solicitud(
        ["EQ-DEMO-02"],
        "Reserva aprobada para una presentacion de laboratorio.",
        date(2026, 9, 14),
        date(2026, 9, 16),
        fecha_solicitud=date(2026, 9, 7),
    )
    solicitud_entregada = solicitudes.crear_solicitud(
        ["EQ-DEMO-03"],
        "Prestamo entregado para practica de electronica.",
        date(2026, 9, 9),
        date(2026, 9, 11),
        fecha_solicitud=date(2026, 9, 7),
    )

    auth.cerrar_sesion()
    auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO)
    solicitudes.aprobar(solicitud_aprobada.id, fecha_aprobacion=date(2026, 9, 8))
    solicitudes.aprobar(solicitud_entregada.id, fecha_aprobacion=date(2026, 9, 8))
    encargado = auth.requiere_sesion()
    prestamos.registrar_entrega(
        solicitud_entregada.id,
        encargado,
        fecha_entrega=date(2026, 9, 9),
    )

    auth.cerrar_sesion()
    auth.iniciar_sesion(ID_SOLICITANTE_ALTERNO_DEMO, CLAVE_SOLICITANTE_ALTERNO_DEMO)
    solicitud_atrasada = solicitudes.crear_solicitud(
        ["EQ-DEMO-04"],
        "Prestamo atrasado para probar consultas y devolucion tardia.",
        date(2026, 8, 25),
        date(2026, 8, 27),
        fecha_solicitud=date(2026, 8, 24),
    )
    solicitud_devuelta = solicitudes.crear_solicitud(
        ["EQ-DEMO-05"],
        "Prestamo ya devuelto para revisar historial cerrado.",
        date(2026, 9, 9),
        FECHA_REFERENCIA_DEMO,
        fecha_solicitud=date(2026, 9, 7),
    )

    auth.cerrar_sesion()
    auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO)
    encargado = auth.requiere_sesion()
    solicitudes.aprobar(solicitud_atrasada.id, fecha_aprobacion=date(2026, 8, 25))
    prestamos.registrar_entrega(
        solicitud_atrasada.id,
        encargado,
        fecha_entrega=date(2026, 8, 25),
    )
    prestamos.marcar_atraso(
        solicitud_atrasada.id,
        usuario=encargado,
        fecha_actual=date(2026, 8, 28),
    )
    solicitudes.aprobar(solicitud_devuelta.id, fecha_aprobacion=date(2026, 9, 8))
    prestamos.registrar_entrega(
        solicitud_devuelta.id,
        encargado,
        fecha_entrega=date(2026, 9, 9),
    )
    prestamos.registrar_devolucion(
        solicitud_devuelta.id,
        encargado,
        fecha_devolucion=FECHA_REFERENCIA_DEMO,
    )


def _logger_silencioso() -> logging.Logger:
    logger = logging.getLogger("prestamos.demo")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger
