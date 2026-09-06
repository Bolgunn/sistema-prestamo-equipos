"""Pruebas funcionales del CLI y menu interactivo (issue #14)."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from prestamos import cli, menu
from prestamos.auth import ServicioAuth, hash_contrasena
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)

CLAVE = "clave-menu-2026"


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

    def ejecutar(*argumentos: str, entrada: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", "-m", "prestamos", *argumentos],
            cwd=tmp_path,
            env=entorno,
            input=entrada,
            capture_output=True,
            text=True,
            timeout=15,
        )

    return ejecutar


def _usuario(id_usuario: str, rol: Rol = Rol.ENCARGADO, *, activo: bool = True) -> Usuario:
    return Usuario(
        id=id_usuario,
        nombre=f"Usuario {id_usuario}",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        hash_contrasena=hash_contrasena(CLAVE, iteraciones=1),
    )


def _equipo(codigo: str = "EQ-CLI-01", estado: EstadoEquipo = EstadoEquipo.DISPONIBLE) -> Equipo:
    return Equipo(
        codigo=codigo,
        nombre="Notebook CLI",
        tipo="Notebook",
        descripcion="Equipo para pruebas de CLI",
        estado=estado,
    )


def _prestamo(
    id_prestamo: str = "P-CLI-01",
    *,
    estado: EstadoPrestamo = EstadoPrestamo.APROBADA,
    fecha_inicio: date = date(2026, 9, 10),
    fecha_termino: date = date(2026, 9, 12),
    fecha_aprobacion: date | None = date(2026, 9, 9),
    fecha_entrega: date | None = None,
) -> Prestamo:
    return Prestamo(
        id=id_prestamo,
        id_solicitante="sol-cli",
        equipos=("EQ-CLI-01",),
        motivo="Prueba CLI",
        estado=estado,
        fecha_solicitud=date(2026, 9, 8),
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        fecha_aprobacion=fecha_aprobacion,
        fecha_entrega=fecha_entrega,
    )


def _sembrar_usuario(datos_dir: Path, usuario: Usuario | None = None) -> Usuario:
    usuario = usuario or _usuario("enc-cli")
    repositorio_usuarios(datos_dir).guardar(usuario)
    return usuario


def test_help_lista_subcomandos_y_no_expone_encargado_inicial(ejecutar_cli) -> None:
    resultado = ejecutar_cli("--help")

    assert resultado.returncode == 0
    for subcomando in ("probar-sentry", "usuarios", "equipos", "solicitudes", "prestamos"):
        assert subcomando in resultado.stdout
    assert "crear_encargado_inicial" not in resultado.stdout
    assert "init-demo" not in resultado.stdout
    assert resultado.stderr == ""


def test_sin_subcomando_abre_menu_interactivo(ejecutar_cli) -> None:
    resultado = ejecutar_cli(entrada="0\n")

    assert resultado.returncode == 0
    assert "Sistema de prestamo de equipos" in resultado.stdout
    assert "1. Iniciar sesion" in resultado.stdout
    assert "0. Salir" in resultado.stdout
    assert "Saliendo." in resultado.stdout
    assert resultado.stderr == ""


def test_menu_eof_durante_prompt_interno_sale_con_codigo_cero(ejecutar_cli) -> None:
    resultado = ejecutar_cli(entrada="1\n")

    assert resultado.returncode == 0
    assert "Sistema de prestamo de equipos" in resultado.stdout
    assert "Saliendo." in resultado.stdout
    assert resultado.stderr == ""
    assert "Traceback" not in resultado.stdout + resultado.stderr


def test_menu_maneja_entradas_invalidas_sin_romper_sesion(ejecutar_cli, tmp_path: Path) -> None:
    _sembrar_usuario(tmp_path / "datos")
    entrada = "\n".join(
        [
            "texto",
            "99",
            "1",
            "enc-cli",
            CLAVE,
            "10",
            "futuros",
            "",
            "",
            "fecha-mala",
            "3",
            "0",
        ]
    )

    resultado = ejecutar_cli(entrada=f"{entrada}\n")

    assert resultado.returncode == 0
    assert "Opcion invalida" in resultado.stdout
    assert "Fecha invalida" in resultado.stdout
    assert "Sesion iniciada: enc-cli" in resultado.stdout
    assert "Sin equipos registrados." in resultado.stdout
    assert "Traceback" not in resultado.stdout + resultado.stderr


def test_cli_devuelve_codigo_distinto_de_cero_ante_error_de_dominio(
    ejecutar_cli,
    tmp_path: Path,
) -> None:
    _sembrar_usuario(tmp_path)

    resultado = ejecutar_cli(
        "--datos-dir",
        str(tmp_path),
        "--usuario",
        "enc-cli",
        "--contrasena",
        "incorrecta",
        "equipos",
        "listar",
    )

    assert resultado.returncode == 1
    assert resultado.stdout.strip() == "Error: Credenciales invalidas."
    assert resultado.stderr == ""
    assert "Traceback" not in resultado.stdout + resultado.stderr


def test_cli_fecha_mal_formada_entrega_error_automatizable(ejecutar_cli, tmp_path: Path) -> None:
    _sembrar_usuario(tmp_path)

    resultado = ejecutar_cli(
        "--datos-dir",
        str(tmp_path),
        "--usuario",
        "enc-cli",
        "--contrasena",
        CLAVE,
        "prestamos",
        "entregar",
        "P-CLI-01",
        "--fecha",
        "no-es-fecha",
    )

    assert resultado.returncode == 2
    assert "fecha invalida" in resultado.stderr
    assert "Traceback" not in resultado.stdout + resultado.stderr


def test_punto_de_composicion_comparte_un_solo_servicio_auth(tmp_path: Path) -> None:
    app = cli.crear_aplicacion(datos_dir=tmp_path)

    assert app.usuarios._auth is app.auth
    assert app.equipos._auth is app.auth
    assert app.solicitudes._auth is app.auth


def test_cli_prestamos_obtiene_usuario_fresco_desde_auth_en_cada_operacion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = cli.crear_aplicacion(datos_dir=tmp_path)
    usuario = _sembrar_usuario(tmp_path)
    repositorio_prestamos(tmp_path).guardar(_prestamo())
    repositorio_equipos(tmp_path).guardar(_equipo(estado=EstadoEquipo.RESERVADO))
    app.auth.iniciar_sesion(usuario.id, CLAVE)
    llamadas = 0
    original = app.auth.requiere_sesion

    def requiere_sesion_spy() -> Usuario:
        nonlocal llamadas
        llamadas += 1
        return original()

    monkeypatch.setattr(app.auth, "requiere_sesion", requiere_sesion_spy)
    args = SimpleNamespace(id_prestamo="P-CLI-01", fecha=date(2026, 9, 10))

    cli._cmd_prestamos_entregar(args, app)

    assert llamadas == 1
    assert repositorio_prestamos(tmp_path).obtener("P-CLI-01").estado is EstadoPrestamo.ENTREGADA


def test_menu_prestamos_relee_usuario_y_rechaza_sesion_inactiva_rn02(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = cli.crear_aplicacion(datos_dir=tmp_path)
    usuario = _sembrar_usuario(tmp_path, _usuario("enc-rn02"))
    repositorio_prestamos(tmp_path).guardar(_prestamo("P-RN02"))
    repositorio_equipos(tmp_path).guardar(_equipo(estado=EstadoEquipo.RESERVADO))
    rechazos: list[Exception] = []
    original_requiere_sesion = app.auth.requiere_sesion

    def requiere_sesion_spy() -> Usuario:
        try:
            return original_requiere_sesion()
        except Exception as exc:
            rechazos.append(exc)
            raise

    monkeypatch.setattr(app.auth, "requiere_sesion", requiere_sesion_spy)
    entradas = iter(["1", usuario.id, CLAVE, "7", "P-RN02", "0"])
    usuario_desactivado = False

    def input_fn(_prompt: str) -> str:
        nonlocal usuario_desactivado
        valor = next(entradas)
        if valor == "7" and not usuario_desactivado:
            repositorio_usuarios(tmp_path).guardar(replace(usuario, activo=False))
            usuario_desactivado = True
        return valor

    salidas: list[str] = []

    codigo = menu.ejecutar_menu(app, input_fn=input_fn, output_fn=salidas.append)

    assert codigo == 0
    salida = "\n".join(salidas)
    assert "Sesion iniciada: enc-rn02" in salida
    assert "Error: El usuario esta inactivo y no puede iniciar sesion." in salida
    assert len(rechazos) == 1
    assert getattr(rechazos[0], "regla", None) == "RN-02"
    assert app.auth.usuario_actual is None
    prestamo = repositorio_prestamos(tmp_path).obtener("P-RN02")
    equipo = repositorio_equipos(tmp_path).obtener("EQ-CLI-01")
    assert prestamo.estado is EstadoPrestamo.APROBADA
    assert prestamo.fecha_entrega is None
    assert equipo.estado is EstadoEquipo.RESERVADO


def test_menu_prestamos_obtiene_usuario_fresco_en_cada_consulta() -> None:
    usuario = _usuario("enc-menu")
    llamadas = 0
    usuarios_recibidos: list[str] = []

    class AuthFake:
        def requiere_sesion(self) -> Usuario:
            nonlocal llamadas
            llamadas += 1
            return usuario

    class PrestamosFake:
        def prestamos_futuros(self, usuario: Usuario, **kwargs) -> list[Prestamo]:
            usuarios_recibidos.append(usuario.id)
            return []

        def prestamos_vigentes(self, usuario: Usuario, **kwargs) -> list[Prestamo]:
            usuarios_recibidos.append(usuario.id)
            return []

    app = SimpleNamespace(
        auth=AuthFake(),
        prestamos=PrestamosFake(),
        equipos=None,
        solicitudes=None,
        usuarios=None,
    )
    entradas = iter(["10", "futuros", "", "", "", "10", "vigentes", "", "", "", "0"])
    salidas: list[str] = []

    codigo = menu.ejecutar_menu(
        app,
        input_fn=lambda _: next(entradas),
        output_fn=salidas.append,
    )

    assert codigo == 0
    assert llamadas == 2
    assert usuarios_recibidos == ["enc-menu", "enc-menu"]
