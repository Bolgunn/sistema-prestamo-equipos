"""Pruebas cruzadas de integrante 1 sobre funcionalidad de integrante 2.

Casos PC20-01 a PC20-04, disenados desde requerimientos, reglas de negocio y
reparto de trabajo documentado antes de revisar la implementacion.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import subprocess
import sys

import pytest

from prestamos.auth import hash_contrasena
from prestamos.errores import ErrorAutorizacion, ErrorValidacion
from prestamos.logging_conf import configurar_logging
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.repositorios.json_repo import RepositorioJson
from prestamos.servicios.prestamos import ServicioPrestamos

CONTRASENA = "Clave-Cruzada-2026"
FECHA_CONTROL = date(2026, 9, 10)


def _usuario(id_usuario: str, rol: Rol, *, activo: bool = True) -> Usuario:
    return Usuario(
        id=id_usuario,
        nombre=f"Usuario cruzado {id_usuario}",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        hash_contrasena=hash_contrasena(CONTRASENA, iteraciones=1),
    )


def _encargado(id_usuario: str = "enc-cruzado") -> Usuario:
    return _usuario(id_usuario, Rol.ENCARGADO)


def _solicitante(id_usuario: str = "sol-cruzado") -> Usuario:
    return _usuario(id_usuario, Rol.SOLICITANTE)


def _equipo(codigo: str, estado: EstadoEquipo = EstadoEquipo.DISPONIBLE) -> Equipo:
    return Equipo(
        codigo=codigo,
        nombre=f"Equipo {codigo}",
        tipo="Notebook",
        descripcion="Equipo usado en pruebas cruzadas",
        estado=estado,
    )


def _prestamo(
    id_prestamo: str,
    *,
    id_solicitante: str = "sol-cruzado",
    equipos: tuple[str, ...] = ("EQ-PC20-01",),
    estado: EstadoPrestamo = EstadoPrestamo.ENTREGADA,
    fecha_inicio: date = date(2026, 9, 8),
    fecha_termino: date = date(2026, 9, 12),
    fecha_aprobacion: date | None = date(2026, 9, 7),
    fecha_entrega: date | None = date(2026, 9, 8),
) -> Prestamo:
    return Prestamo(
        id=id_prestamo,
        id_solicitante=id_solicitante,
        equipos=equipos,
        motivo="Revision cruzada de ciclo de vida",
        estado=estado,
        fecha_solicitud=date(2026, 9, 7),
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        fecha_aprobacion=fecha_aprobacion,
        fecha_entrega=fecha_entrega,
    )


def _repos_prestamos(tmp_path: Path) -> tuple[
    RepositorioJson[Prestamo],
    RepositorioJson[Equipo],
    ServicioPrestamos,
]:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    repo_equipos = RepositorioJson(tmp_path / "equipos.json", Equipo, "codigo")
    return repo_prestamos, repo_equipos, ServicioPrestamos(repo_prestamos, repo_equipos)


@pytest.mark.prueba_cruzada
def test_PC20_01_RF10_devolucion_parcial_no_libera_prestamo_ni_equipos(tmp_path: Path) -> None:
    repo_prestamos, repo_equipos, servicio = _repos_prestamos(tmp_path)
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-PARCIAL",
            equipos=("EQ-PC20-01", "EQ-PC20-02"),
        )
    )
    repo_equipos.guardar(_equipo("EQ-PC20-01", EstadoEquipo.PRESTADO))
    repo_equipos.guardar(_equipo("EQ-PC20-02", EstadoEquipo.PRESTADO))

    with pytest.raises(ErrorValidacion) as exc_info:
        servicio.registrar_devolucion(
            "P-PC20-PARCIAL",
            _encargado(),
            fecha_devolucion=date(2026, 9, 10),
            equipos_devueltos=["EQ-PC20-01"],
        )

    error = exc_info.value
    assert error.regla == "RN-14"
    assert error.detalles == {"faltantes": ["EQ-PC20-02"], "no_esperados": []}
    assert repo_prestamos.obtener("P-PC20-PARCIAL").estado is EstadoPrestamo.ENTREGADA
    assert repo_prestamos.obtener("P-PC20-PARCIAL").fecha_devolucion is None
    assert repo_equipos.obtener("EQ-PC20-01").estado is EstadoEquipo.PRESTADO
    assert repo_equipos.obtener("EQ-PC20-02").estado is EstadoEquipo.PRESTADO


@pytest.mark.prueba_cruzada
def test_PC20_02_RF12_solicitante_solo_ve_sus_prestamos_atrasados(tmp_path: Path) -> None:
    repo_prestamos, repo_equipos, servicio = _repos_prestamos(tmp_path)
    solicitante = _solicitante("sol-propio")
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-PROPIO",
            id_solicitante="sol-propio",
            equipos=("EQ-PC20-PROPIO",),
            fecha_termino=date(2026, 9, 9),
        )
    )
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-AJENO",
            id_solicitante="sol-ajeno",
            equipos=("EQ-PC20-AJENO",),
            fecha_termino=date(2026, 9, 9),
        )
    )
    repo_equipos.guardar(_equipo("EQ-PC20-PROPIO", EstadoEquipo.PRESTADO))
    repo_equipos.guardar(_equipo("EQ-PC20-AJENO", EstadoEquipo.PRESTADO))

    atrasados = servicio.prestamos_atrasados(solicitante, fecha_actual=FECHA_CONTROL)

    assert [prestamo.id for prestamo in atrasados] == ["P-PC20-PROPIO"]
    with pytest.raises(ErrorAutorizacion) as exc_info:
        servicio.prestamos_atrasados(
            solicitante,
            fecha_actual=FECHA_CONTROL,
            id_usuario="sol-ajeno",
        )
    assert exc_info.value.regla == "RN-19"
    assert repo_prestamos.obtener("P-PC20-PROPIO").estado is EstadoPrestamo.ENTREGADA
    assert repo_prestamos.obtener("P-PC20-AJENO").estado is EstadoPrestamo.ENTREGADA


@pytest.mark.prueba_cruzada
def test_PC20_03_RF12_cli_futuros_filtra_por_usuario_y_equipo(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        SENTRY_DSN="",
        PRESTAMOS_LOG_PATH=str(tmp_path / "eventos.log"),
    )
    repositorio_usuarios(tmp_path).guardar(_encargado())
    repo_prestamos = repositorio_prestamos(tmp_path)
    repo_equipos = repositorio_equipos(tmp_path)
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-VISIBLE",
            id_solicitante="sol-filtrado",
            equipos=("EQ-PC20-VISIBLE",),
            estado=EstadoPrestamo.APROBADA,
            fecha_inicio=date(2026, 9, 14),
            fecha_termino=date(2026, 9, 16),
            fecha_entrega=None,
        )
    )
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-OCULTO",
            id_solicitante="sol-filtrado",
            equipos=("EQ-PC20-OTRO",),
            estado=EstadoPrestamo.APROBADA,
            fecha_inicio=date(2026, 9, 14),
            fecha_termino=date(2026, 9, 16),
            fecha_entrega=None,
        )
    )
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-AJENO",
            id_solicitante="sol-ajeno",
            equipos=("EQ-PC20-VISIBLE",),
            estado=EstadoPrestamo.APROBADA,
            fecha_inicio=date(2026, 9, 14),
            fecha_termino=date(2026, 9, 16),
            fecha_entrega=None,
        )
    )
    repo_equipos.guardar(_equipo("EQ-PC20-VISIBLE", EstadoEquipo.RESERVADO))
    repo_equipos.guardar(_equipo("EQ-PC20-OTRO", EstadoEquipo.RESERVADO))

    resultado = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "prestamos",
            "--datos-dir",
            str(tmp_path),
            "--usuario",
            "enc-cruzado",
            "--contrasena",
            CONTRASENA,
            "prestamos",
            "futuros",
            "--fecha",
            "2026-09-10",
            "--id-usuario",
            "sol-filtrado",
            "--codigo-equipo",
            "EQ-PC20-VISIBLE",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert resultado.returncode == 0
    assert resultado.stderr == ""
    assert resultado.stdout.strip() == (
        "P-PC20-VISIBLE | APROBADA | sol-filtrado | EQ-PC20-VISIBLE | "
        "2026-09-14 -> 2026-09-16"
    )
    assert "P-PC20-OCULTO" not in resultado.stdout
    assert "P-PC20-AJENO" not in resultado.stdout


@pytest.mark.prueba_cruzada
@pytest.mark.xfail(strict=True, reason="DEF-02 / #47: ServicioPrestamos no registra eventos RN-18")
def test_PC20_04_RN18_entrega_debe_quedar_en_log_de_auditoria(
    tmp_path: Path,
) -> None:
    repo_prestamos, repo_equipos, servicio = _repos_prestamos(tmp_path)
    repo_prestamos.guardar(
        _prestamo(
            "P-PC20-LOG",
            estado=EstadoPrestamo.APROBADA,
            fecha_entrega=None,
        )
    )
    repo_equipos.guardar(_equipo("EQ-PC20-01", EstadoEquipo.RESERVADO))

    log_path = tmp_path / "auditoria.log"
    configurar_logging(log_path)

    servicio.registrar_entrega(
        "P-PC20-LOG",
        _encargado(),
        fecha_entrega=date(2026, 9, 10),
    )

    contenido = log_path.read_text(encoding="utf-8")
    assert "prestamo_entrega" in contenido
    assert CONTRASENA not in contenido


@pytest.mark.prueba_cruzada
def test_PC20_05_RF14_init_demo_permita_consulta_manual_documentada(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        SENTRY_DSN="",
        PRESTAMOS_LOG_PATH=str(tmp_path / "eventos.log"),
    )
    datos_dir = tmp_path / "datos-demo-cruzados"

    init_demo = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "prestamos",
            "--datos-dir",
            str(datos_dir),
            "init-demo",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    consulta = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "prestamos",
            "--datos-dir",
            str(datos_dir),
            "--usuario",
            "enc-demo",
            "--contrasena",
            "DemoEncargado2026!",
            "prestamos",
            "atrasados",
            "--fecha",
            "2026-09-10",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert init_demo.returncode == 0
    assert "Datos de demostracion creados" in init_demo.stdout
    assert consulta.returncode == 0
    assert consulta.stderr == ""
    assert consulta.stdout.strip() == (
        "S-0004 | ATRASADA | sol-demo-2 | EQ-DEMO-04 | 2026-08-25 -> 2026-08-27"
    )
    assert "Traceback" not in init_demo.stdout + init_demo.stderr + consulta.stdout + consulta.stderr
