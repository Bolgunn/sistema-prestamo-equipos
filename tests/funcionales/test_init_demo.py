"""Pruebas funcionales del comando init-demo (issue #15)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from prestamos.auth import ServicioAuth
from prestamos.demo import (
    ARCHIVOS_DEMO,
    CLAVE_ENCARGADO_DEMO,
    FECHA_REFERENCIA_DEMO,
    CLAVE_SOLICITANTE_ALTERNO_DEMO,
    CLAVE_SOLICITANTE_DEMO,
    ID_ENCARGADO_DEMO,
    ID_SOLICITANTE_ALTERNO_DEMO,
    ID_SOLICITANTE_DEMO,
    inicializar_datos_demo,
)
from prestamos.modelos import EstadoEquipo, EstadoPrestamo, Rol
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.servicios.prestamos import ServicioPrestamos


@pytest.fixture
def ejecutar_cli(tmp_path: Path):
    entorno = os.environ.copy()
    entorno.update(
        PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        SENTRY_DSN="",
        NIVEL_LOG="INFO",
        PRESTAMOS_LOG_PATH=str(tmp_path / "eventos.log"),
    )

    def ejecutar(*argumentos: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", "-m", "prestamos", *argumentos],
            cwd=tmp_path,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=20,
        )

    return ejecutar


def _contenido_archivos(datos_dir: Path) -> dict[str, str]:
    return {nombre: (datos_dir / nombre).read_text(encoding="utf-8") for nombre in ARCHIVOS_DEMO}


def test_init_demo_crea_archivos_en_datos_demo_por_defecto(ejecutar_cli, tmp_path: Path) -> None:
    resultado = ejecutar_cli("init-demo")

    assert resultado.returncode == 0
    assert "Datos de demostracion creados" in resultado.stdout
    datos_demo = tmp_path / "datos" / "demo"
    assert sorted(path.name for path in datos_demo.glob("*.json")) == sorted(ARCHIVOS_DEMO)
    assert "Traceback" not in resultado.stdout + resultado.stderr


def test_init_demo_dataset_tiene_contenido_minimo_consistente_y_usable(tmp_path: Path) -> None:
    resultado = inicializar_datos_demo(tmp_path)

    assert resultado.creado is True
    usuarios = repositorio_usuarios(tmp_path).listar()
    equipos = repositorio_equipos(tmp_path).listar()
    prestamos = repositorio_prestamos(tmp_path).listar()

    assert len(usuarios) >= 2
    assert any(usuario.rol is Rol.ENCARGADO for usuario in usuarios)
    assert any(usuario.rol is Rol.SOLICITANTE for usuario in usuarios)
    assert len(equipos) >= 5
    assert {prestamo.estado for prestamo in prestamos} >= {
        EstadoPrestamo.SOLICITADA,
        EstadoPrestamo.APROBADA,
        EstadoPrestamo.ENTREGADA,
        EstadoPrestamo.ATRASADA,
        EstadoPrestamo.DEVUELTA,
    }
    assert any(prestamo.estado is EstadoPrestamo.ATRASADA for prestamo in prestamos)

    equipos_por_codigo = {equipo.codigo: equipo for equipo in equipos}
    usuarios_por_id = {usuario.id: usuario for usuario in usuarios}
    for prestamo in prestamos:
        assert prestamo.id_solicitante in usuarios_por_id
        for codigo in prestamo.equipos:
            assert codigo in equipos_por_codigo

    assert equipos_por_codigo["EQ-DEMO-01"].estado is EstadoEquipo.DISPONIBLE
    assert equipos_por_codigo["EQ-DEMO-02"].estado is EstadoEquipo.RESERVADO
    assert equipos_por_codigo["EQ-DEMO-03"].estado is EstadoEquipo.PRESTADO
    assert equipos_por_codigo["EQ-DEMO-04"].estado is EstadoEquipo.PRESTADO
    assert equipos_por_codigo["EQ-DEMO-05"].estado is EstadoEquipo.DISPONIBLE

    auth = ServicioAuth(repositorio_usuarios(tmp_path))
    encargado = auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO).usuario
    assert encargado.rol is Rol.ENCARGADO
    servicio = ServicioPrestamos(datos_dir=tmp_path)
    assert [
        p.id
        for p in servicio.prestamos_atrasados(
            encargado, fecha_actual=FECHA_REFERENCIA_DEMO
        )
    ] == ["S-0004"]


def test_init_demo_no_guarda_contrasenas_en_texto_plano_y_credenciales_permiten_login(
    tmp_path: Path,
) -> None:
    inicializar_datos_demo(tmp_path)
    contenido = (tmp_path / "usuarios.json").read_text(encoding="utf-8")

    assert CLAVE_ENCARGADO_DEMO not in contenido
    assert CLAVE_SOLICITANTE_DEMO not in contenido
    assert "pbkdf2_sha256$" in contenido

    auth = ServicioAuth(repositorio_usuarios(tmp_path))
    assert auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO).usuario.id == ID_ENCARGADO_DEMO
    auth.cerrar_sesion()
    assert auth.iniciar_sesion(ID_SOLICITANTE_DEMO, CLAVE_SOLICITANTE_DEMO).usuario.id == ID_SOLICITANTE_DEMO
    auth.cerrar_sesion()
    assert (
        auth.iniciar_sesion(ID_SOLICITANTE_ALTERNO_DEMO, CLAVE_SOLICITANTE_ALTERNO_DEMO).usuario.id
        == ID_SOLICITANTE_ALTERNO_DEMO
    )


def test_init_demo_es_idempotente_y_no_modifica_datos_existentes_sin_force(
    ejecutar_cli,
    tmp_path: Path,
) -> None:
    datos_dir = tmp_path / "demo"
    primero = ejecutar_cli("--datos-dir", str(datos_dir), "init-demo")
    antes = _contenido_archivos(datos_dir)

    segundo = ejecutar_cli("--datos-dir", str(datos_dir), "init-demo")
    despues = _contenido_archivos(datos_dir)

    assert primero.returncode == 0
    assert segundo.returncode == 0
    assert "ya existen" in segundo.stdout
    assert "--force" in segundo.stdout
    assert despues == antes


def test_init_demo_force_regenera_datos_existentes(ejecutar_cli, tmp_path: Path) -> None:
    datos_dir = tmp_path / "demo"
    assert ejecutar_cli("--datos-dir", str(datos_dir), "init-demo").returncode == 0
    (datos_dir / "usuarios.json").write_text(json.dumps([]), encoding="utf-8")

    resultado = ejecutar_cli("--datos-dir", str(datos_dir), "init-demo", "--force")

    assert resultado.returncode == 0
    assert "regenerados" in resultado.stdout
    usuarios = repositorio_usuarios(datos_dir).listar()
    assert {usuario.id for usuario in usuarios} >= {
        ID_ENCARGADO_DEMO,
        ID_SOLICITANTE_DEMO,
        ID_SOLICITANTE_ALTERNO_DEMO,
    }


def test_init_demo_force_es_reproducible_byte_a_byte_y_coincide_con_versionados(
    tmp_path: Path,
) -> None:
    datos_dir = tmp_path / "demo"
    versionados_dir = Path(__file__).resolve().parents[2] / "datos" / "demo"

    inicializar_datos_demo(datos_dir)
    primera = _contenido_archivos(datos_dir)
    inicializar_datos_demo(datos_dir, sobrescribir=True)
    segunda = _contenido_archivos(datos_dir)

    assert segunda == primera
    assert segunda == _contenido_archivos(versionados_dir)


def test_json_reales_de_datos_demo_son_validos_y_no_exponen_contrasenas() -> None:
    datos_demo = Path(__file__).resolve().parents[2] / "datos" / "demo"
    usuarios = repositorio_usuarios(datos_demo).listar()
    equipos = repositorio_equipos(datos_demo).listar()
    prestamos = repositorio_prestamos(datos_demo).listar()
    contenido_usuarios = (datos_demo / "usuarios.json").read_text(encoding="utf-8")

    assert len(usuarios) >= 2
    assert any(
        usuario.id == ID_ENCARGADO_DEMO and usuario.rol is Rol.ENCARGADO
        for usuario in usuarios
    )
    assert any(usuario.rol is Rol.SOLICITANTE for usuario in usuarios)
    assert len(equipos) == 5
    assert any(prestamo.estado is EstadoPrestamo.ATRASADA for prestamo in prestamos)
    assert CLAVE_ENCARGADO_DEMO not in contenido_usuarios
    assert CLAVE_SOLICITANTE_DEMO not in contenido_usuarios
    assert CLAVE_SOLICITANTE_ALTERNO_DEMO not in contenido_usuarios

    auth = ServicioAuth(repositorio_usuarios(datos_demo))
    sesion = auth.iniciar_sesion(ID_ENCARGADO_DEMO, CLAVE_ENCARGADO_DEMO)

    assert sesion.usuario.id == ID_ENCARGADO_DEMO


def test_help_muestra_init_demo_y_no_expone_helper_publico(ejecutar_cli) -> None:
    resultado = ejecutar_cli("--help")

    assert resultado.returncode == 0
    assert "init-demo" in resultado.stdout
    assert "crear_encargado_inicial" not in resultado.stdout
