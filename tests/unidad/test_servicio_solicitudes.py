"""Pruebas de `prestamos.servicios.solicitudes`: crear, aprobar y rechazar (issue #11).

Nombres descriptivos y sin etiqueta CP-XX, igual que `test_servicio_prestamos.py`
y `test_servicio_equipos.py`; ver DEF-01 (issue #43).

El grupo importante es el del solapamiento: comprueba que un equipo RESERVADO
sigue siendo solicitable para ventanas que no chocan con la reserva. Antes de
esta rama ese caso se rechazaba por RN-05 -el escalar `Equipo.estado`- aunque
las fechas no tuvieran nada que ver.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pytest

from prestamos.auth import ServicioAuth
from prestamos.errores import (
    ErrorAutorizacion,
    ErrorValidacion,
    RecursoNoEncontrado,
    TransicionNoPermitida,
)
from prestamos.logging_conf import LOGGER_NAME, configurar_logging
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.repositorios.json_repo import RepositorioJson
from prestamos.servicios.solicitudes import ServicioSolicitudes
from prestamos.servicios.usuarios import ServicioUsuarios, crear_encargado_inicial

CONTRASENA = "clave-de-demostracion"

# Lunes 7 de septiembre de 2026. Las fechas del archivo se eligen sobre semanas
# completas para que RN-08 (5 dias habiles) y RN-09 (20 dias laborales) no
# cambien de significado segun el dia en que corra la suite.
HOY = date(2026, 9, 7)
RESERVA_INICIO = date(2026, 9, 14)  # lunes
RESERVA_TERMINO = date(2026, 9, 18)  # viernes


# ---------------------------------------------------------------- Fixtures


@pytest.fixture
def repo_usuarios(tmp_path: Path) -> RepositorioJson[Usuario]:
    return RepositorioJson(tmp_path / "usuarios.json", Usuario, "id")


@pytest.fixture
def repo_equipos(tmp_path: Path) -> RepositorioJson[Equipo]:
    return RepositorioJson(tmp_path / "equipos.json", Equipo, "codigo")


@pytest.fixture
def repo_prestamos(tmp_path: Path) -> RepositorioJson[Prestamo]:
    return RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")


@pytest.fixture
def log_pruebas(tmp_path: Path):
    ruta = tmp_path / "eventos.log"
    logger = configurar_logging(ruta)
    yield logger, ruta
    for handler in list(logging.getLogger(LOGGER_NAME).handlers):
        if getattr(handler, "_prestamos_log_path", None) == ruta.resolve():
            logger.removeHandler(handler)
            handler.close()


@pytest.fixture
def auth(repo_usuarios, log_pruebas) -> ServicioAuth:
    logger, _ = log_pruebas
    return ServicioAuth(repo_usuarios, logger=logger)


@pytest.fixture
def servicio(auth, repo_prestamos, repo_equipos, repo_usuarios, log_pruebas):
    logger, _ = log_pruebas
    return ServicioSolicitudes(
        auth, repo_prestamos, repo_equipos, repo_usuarios, logger=logger
    )


@pytest.fixture
def padron(auth, repo_usuarios, log_pruebas) -> dict[str, Usuario]:
    """Un encargado y dos solicitantes, sin sesion abierta."""
    logger, _ = log_pruebas
    encargado = crear_encargado_inicial(
        "enc", "Encargada Principal", "encargada@universidad.cl", CONTRASENA,
        repositorio=repo_usuarios, iteraciones_hash=1,
    )
    auth.iniciar_sesion("enc", CONTRASENA)
    servicio_usuarios = ServicioUsuarios(
        auth, repo_usuarios, logger=logger, iteraciones_hash=1
    )
    creados = {"enc": encargado}
    for id_usuario, nombre in (("sol-1", "Solicitante Uno"), ("sol-2", "Solicitante Dos")):
        creados[id_usuario] = servicio_usuarios.registrar_usuario(
            id_usuario, nombre, f"{id_usuario}@universidad.cl", Rol.SOLICITANTE, CONTRASENA
        )
    auth.cerrar_sesion()
    return creados


@pytest.fixture
def catalogo(repo_equipos) -> None:
    for codigo in ("EQ-01", "EQ-02"):
        repo_equipos.guardar(
            Equipo(
                codigo=codigo,
                nombre="Notebook de laboratorio",
                tipo="computador",
                descripcion="Notebook para practicos",
                estado=EstadoEquipo.DISPONIBLE,
            )
        )


def _eventos(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    return [
        json.loads(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _entrar(auth: ServicioAuth, id_usuario: str) -> None:
    auth.cerrar_sesion()
    auth.iniciar_sesion(id_usuario, CONTRASENA)


def _crear(servicio, *, equipos=("EQ-01",), inicio=RESERVA_INICIO, termino=RESERVA_TERMINO):
    return servicio.crear_solicitud(
        equipos, "Practico de laboratorio", inicio, termino, fecha_solicitud=HOY
    )


def _reserva_de(servicio, auth, *, solicitante="sol-2", **ventana) -> Prestamo:
    """Deja una solicitud aprobada, que es lo que reserva el equipo."""
    _entrar(auth, solicitante)
    solicitud = _crear(servicio, **ventana)
    _entrar(auth, "enc")
    return servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)


# ------------------------------------------------------------------ Crear


def test_solicitante_crea_una_solicitud_con_equipo_y_rango_de_fechas(
    servicio, auth, padron, catalogo, repo_prestamos
) -> None:
    _entrar(auth, "sol-1")

    solicitud = _crear(servicio)

    assert solicitud.id == "S-0001"
    assert solicitud.estado is EstadoPrestamo.SOLICITADA
    assert solicitud.id_solicitante == "sol-1"
    assert solicitud.equipos == ("EQ-01",)
    assert solicitud.fecha_inicio == RESERVA_INICIO
    assert solicitud.fecha_termino == RESERVA_TERMINO
    assert solicitud.fecha_solicitud == HOY
    assert repo_prestamos.obtener("S-0001") == solicitud


def test_los_identificadores_son_secuenciales_y_no_reutilizan_los_libres(
    servicio, auth, padron, catalogo, repo_prestamos
) -> None:
    _entrar(auth, "sol-1")

    primera = _crear(servicio)
    segunda = _crear(servicio, equipos=("EQ-02",))

    assert [primera.id, segunda.id] == ["S-0001", "S-0002"]

    # Las fixtures a mano y los archivos editados no siguen el formato: se
    # ignoran para el maximo en vez de romper la generacion.
    repo_prestamos.guardar(
        Prestamo(
            id="P-99",
            id_solicitante="sol-1",
            equipos=("EQ-02",),
            motivo="Registro heredado",
            estado=EstadoPrestamo.DEVUELTA,
            fecha_solicitud=HOY,
            fecha_inicio=RESERVA_INICIO,
            fecha_termino=RESERVA_TERMINO,
        )
    )
    assert _crear(servicio, equipos=("EQ-02",)).id == "S-0003"


def test_el_encargado_no_puede_crear_solicitudes(
    servicio, auth, padron, catalogo
) -> None:
    """T-01 es exclusiva del Solicitante (RN-01)."""
    _entrar(auth, "enc")

    with pytest.raises(ErrorAutorizacion):
        _crear(servicio)


def test_crear_no_persiste_si_el_equipo_no_existe(
    servicio, auth, padron, catalogo, repo_prestamos
) -> None:
    _entrar(auth, "sol-1")

    with pytest.raises(RecursoNoEncontrado):
        _crear(servicio, equipos=("EQ-INEXISTENTE",))

    assert repo_prestamos.listar() == []


def test_crear_aplica_el_plazo_maximo_y_el_limite_de_equipos(
    servicio, auth, padron, catalogo, repo_equipos
) -> None:
    """RN-08 (5 dias habiles) y RN-07 (3 equipos activos) vienen del motor."""
    _entrar(auth, "sol-1")

    with pytest.raises(ErrorValidacion) as exc_plazo:
        _crear(servicio, inicio=RESERVA_INICIO, termino=date(2026, 9, 21))
    assert exc_plazo.value.regla == "RN-08"

    for codigo in ("EQ-03", "EQ-04"):
        repo_equipos.guardar(
            Equipo(
                codigo=codigo,
                nombre="Osciloscopio",
                tipo="instrumento",
                descripcion="Osciloscopio de laboratorio",
                estado=EstadoEquipo.DISPONIBLE,
            )
        )
    with pytest.raises(ErrorValidacion) as exc_cantidad:
        _crear(servicio, equipos=("EQ-01", "EQ-02", "EQ-03", "EQ-04"))
    assert exc_cantidad.value.regla == "RN-06"


# ---------------------------------------------------------------- Aprobar


def test_el_encargado_aprueba_y_el_equipo_queda_reservado(
    servicio, auth, padron, catalogo, repo_prestamos, repo_equipos
) -> None:
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)
    _entrar(auth, "enc")

    aprobada = servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    assert aprobada.estado is EstadoPrestamo.APROBADA
    assert aprobada.fecha_aprobacion == HOY
    assert repo_prestamos.obtener(solicitud.id) == aprobada
    assert repo_equipos.obtener("EQ-01").estado is EstadoEquipo.RESERVADO


def test_el_solicitante_no_puede_aprobar(
    servicio, auth, padron, catalogo, repo_prestamos
) -> None:
    """RN-11: aprobar es exclusivo del Encargado."""
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)

    with pytest.raises(ErrorAutorizacion):
        servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    assert repo_prestamos.obtener(solicitud.id).estado is EstadoPrestamo.SOLICITADA


def test_nadie_aprueba_su_propia_solicitud(
    servicio, auth, padron, catalogo, repo_prestamos, repo_usuarios, log_pruebas
) -> None:
    """RN-22, por el unico camino que lo hace alcanzable: la promocion de rol.

    `sol-1` pide algo, un encargado lo promueve, y ahora tiene el rol necesario
    para aprobar lo suyo.
    """
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)

    logger, _ = log_pruebas
    _entrar(auth, "enc")
    ServicioUsuarios(
        auth, repo_usuarios, logger=logger, iteraciones_hash=1
    ).editar_usuario("sol-1", rol=Rol.ENCARGADO)
    _entrar(auth, "sol-1")

    with pytest.raises(ErrorAutorizacion) as exc:
        servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    assert exc.value.regla == "RN-22"
    assert repo_prestamos.obtener(solicitud.id).estado is EstadoPrestamo.SOLICITADA


def test_solo_se_aprueba_desde_solicitada(
    servicio, auth, padron, catalogo
) -> None:
    """RN-12: una solicitud ya aprobada no vuelve a aprobarse."""
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)
    _entrar(auth, "enc")
    servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    with pytest.raises(TransicionNoPermitida) as exc:
        servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    assert exc.value.regla == "RN-12"


def test_aprobar_no_persiste_si_el_solicitante_fue_dado_de_baja(
    servicio, auth, padron, catalogo, repo_prestamos, repo_usuarios, log_pruebas
) -> None:
    """RN-02 se revalida al aprobar, no solo al crear."""
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)

    logger, _ = log_pruebas
    _entrar(auth, "enc")
    ServicioUsuarios(
        auth, repo_usuarios, logger=logger, iteraciones_hash=1
    ).desactivar("sol-1")

    with pytest.raises(ErrorValidacion) as exc:
        servicio.aprobar(solicitud.id, fecha_aprobacion=HOY)

    assert exc.value.regla == "RN-02"
    assert repo_prestamos.obtener(solicitud.id).estado is EstadoPrestamo.SOLICITADA


# --------------------------------------------------------------- Rechazar


def test_el_encargado_rechaza_y_el_motivo_queda_registrado(
    servicio, auth, padron, catalogo, repo_prestamos, repo_equipos
) -> None:
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)
    _entrar(auth, "enc")

    rechazada = servicio.rechazar(solicitud.id, "No hay cupo en el periodo")

    assert rechazada.estado is EstadoPrestamo.RECHAZADA
    assert rechazada.motivo_rechazo == "No hay cupo en el periodo"
    assert repo_prestamos.obtener(solicitud.id) == rechazada
    # Una solicitud rechazada nunca llego a comprometer inventario.
    assert repo_equipos.obtener("EQ-01").estado is EstadoEquipo.DISPONIBLE


@pytest.mark.parametrize("motivo", ["", "   "])
def test_el_rechazo_exige_motivo(
    servicio, auth, padron, catalogo, repo_prestamos, motivo: str
) -> None:
    _entrar(auth, "sol-1")
    solicitud = _crear(servicio)
    _entrar(auth, "enc")

    with pytest.raises(ErrorValidacion) as exc:
        servicio.rechazar(solicitud.id, motivo)

    assert exc.value.regla == "RN-17"
    assert repo_prestamos.obtener(solicitud.id).estado is EstadoPrestamo.SOLICITADA


# ------------------------------------------------------------ Solapamiento


def test_un_equipo_reservado_admite_una_ventana_que_no_solapa(
    servicio, auth, padron, catalogo, repo_equipos
) -> None:
    """El caso que esta rama vuelve posible.

    `EQ-01` esta RESERVADO del 14 al 18. Una solicitud del 21 al 25 no toca esa
    ventana y debe aprobarse. Antes se rechazaba por RN-05, mirando el escalar.
    """
    _reserva_de(servicio, auth)
    assert repo_equipos.obtener("EQ-01").estado is EstadoEquipo.RESERVADO

    _entrar(auth, "sol-1")
    segunda = _crear(servicio, inicio=date(2026, 9, 21), termino=date(2026, 9, 25))
    _entrar(auth, "enc")
    aprobada = servicio.aprobar(segunda.id, fecha_aprobacion=HOY)

    assert aprobada.estado is EstadoPrestamo.APROBADA
    assert repo_equipos.obtener("EQ-01").estado is EstadoEquipo.RESERVADO


def test_un_equipo_reservado_rechaza_la_ventana_que_solapa(
    servicio, auth, padron, catalogo, repo_prestamos
) -> None:
    """El otro lado del mismo borde: del 16 al 22 pisa la reserva.

    El rechazo llega ya al *crear*: RN-05 se comprueba "al crear o aprobar", asi
    que la solicitud imposible ni siquiera se persiste. La regla citada es
    RN-05 porque es el momento de la creacion; el mismo choque, evaluado al
    aprobar, se cita como RN-10 (ver `test_reglas.py`).
    """
    _reserva_de(servicio, auth)

    _entrar(auth, "sol-1")
    with pytest.raises(ErrorValidacion) as exc:
        _crear(servicio, inicio=date(2026, 9, 16), termino=date(2026, 9, 22))

    assert exc.value.regla == "RN-05"
    assert [p.id for p in repo_prestamos.listar()] == ["S-0001"]


# ------------------------------------------------------------------- Logs


def test_las_tres_operaciones_quedan_en_el_log_con_su_resultado(
    servicio, auth, padron, catalogo, log_pruebas
) -> None:
    """RN-18 nombra explicitamente crear, aprobar y rechazar."""
    _, ruta = log_pruebas
    _entrar(auth, "sol-1")
    primera = _crear(servicio)
    segunda = _crear(servicio, equipos=("EQ-02",))
    _entrar(auth, "enc")
    servicio.aprobar(primera.id, fecha_aprobacion=HOY)
    servicio.rechazar(segunda.id, "Sin cupo")
    with pytest.raises(TransicionNoPermitida):
        servicio.aprobar(segunda.id, fecha_aprobacion=HOY)

    registrados = [
        (evento["accion"], evento["resultado"])
        for evento in _eventos(ruta)
        if evento["accion"].startswith("solicitud_")
    ]

    assert ("solicitud_creada", "ok") in registrados
    assert ("solicitud_aprobada", "ok") in registrados
    assert ("solicitud_rechazada", "ok") in registrados
    # `f413186`: tambien se registra lo que no cambia de estado.
    assert ("solicitud_aprobada", "error") in registrados


def test_el_log_no_incluye_el_hash_de_la_contrasena(
    servicio, auth, padron, catalogo, log_pruebas
) -> None:
    """RN-18/RNF-04."""
    _, ruta = log_pruebas
    _entrar(auth, "sol-1")
    _crear(servicio)

    assert "hash_contrasena" not in ruta.read_text(encoding="utf-8")
