"""Casos de borde canonicos CP-06 a CP-09."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from prestamos.errores import ErrorValidacion
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.reglas import EventoTransicion, dias_habiles, validar_transicion
from prestamos.repositorios.json_repo import RepositorioJson
import prestamos.servicios.prestamos as servicio_prestamos_mod
from prestamos.servicios.prestamos import ServicioPrestamos

FECHA_CONTROL = date(2026, 9, 10)


def _usuario(
    id_usuario: str,
    *,
    rol: Rol,
    activo: bool = True,
) -> Usuario:
    return Usuario(
        id=id_usuario,
        nombre=f"Usuario borde {id_usuario}",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        hash_contrasena="pbkdf2_sha256$1$00112233445566778899aabbccddeeff$"
        "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
    )


def _encargado(id_usuario: str = "enc-borde") -> Usuario:
    return _usuario(id_usuario, rol=Rol.ENCARGADO)


def _solicitante(id_usuario: str = "sol-borde") -> Usuario:
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
        descripcion="Equipo para caso de borde",
        estado=estado,
    )


def _prestamo(
    id_prestamo: str,
    *,
    id_solicitante: str = "sol-borde",
    equipos: tuple[str, ...] = ("EQ-BORDE-01",),
    estado: EstadoPrestamo = EstadoPrestamo.SOLICITADA,
    fecha_inicio: date = date(2026, 9, 14),
    fecha_termino: date = date(2026, 9, 16),
    fecha_solicitud: date = date(2026, 9, 10),
    fecha_aprobacion: date | None = None,
    fecha_entrega: date | None = None,
    fecha_devolucion: date | None = None,
) -> Prestamo:
    return Prestamo(
        id=id_prestamo,
        id_solicitante=id_solicitante,
        equipos=equipos,
        motivo="Caso de borde documentado",
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


@pytest.mark.borde
def test_CP06_RF07_limite_exacto_tres_equipos_activos_es_permitido(
    tmp_path: Path,
) -> None:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    existente = _prestamo(
        "PREST-DOS-ACTIVOS",
        equipos=("EQ-ACT-01", "EQ-ACT-02"),
        estado=EstadoPrestamo.APROBADA,
        fecha_inicio=date(2026, 9, 14),
        fecha_termino=date(2026, 9, 16),
        fecha_aprobacion=date(2026, 9, 10),
    )
    candidato = _prestamo(
        "PREST-TERCER-EQUIPO",
        equipos=("EQ-ACT-03",),
        estado=EstadoPrestamo.SOLICITADA,
        fecha_inicio=date(2026, 9, 14),
        fecha_termino=date(2026, 9, 16),
    )
    repo_prestamos.guardar(existente)
    repo_prestamos.guardar(candidato)

    transicion = validar_transicion(
        candidato,
        EventoTransicion.APROBAR_SOLICITUD,
        _encargado(),
        fecha_actual=FECHA_CONTROL,
        equipos={"EQ-ACT-03": _equipo("EQ-ACT-03")},
        prestamos_existentes=repo_prestamos.listar(),
        solicitante=_solicitante(),
    )

    assert transicion.id == "T-02"
    assert transicion.destino is EstadoPrestamo.APROBADA
    assert repo_prestamos.obtener("PREST-TERCER-EQUIPO").estado is EstadoPrestamo.SOLICITADA


@pytest.mark.borde
def test_CP07_RF10_devolucion_exactamente_en_fecha_termino_no_genera_atraso(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_prestamos, repo_equipos, servicio = _repos_prestamos(tmp_path)
    repo_prestamos.guardar(
        _prestamo(
            "PREST-DEVUELTO-LIMITE",
            estado=EstadoPrestamo.ENTREGADA,
            fecha_inicio=date(2026, 9, 10),
            fecha_termino=date(2026, 9, 12),
            fecha_aprobacion=date(2026, 9, 9),
            fecha_entrega=date(2026, 9, 10),
        )
    )
    repo_equipos.guardar(_equipo("EQ-BORDE-01", estado=EstadoEquipo.PRESTADO))
    eventos: list[EventoTransicion] = []
    validar_original = servicio_prestamos_mod.validar_transicion

    def validar_spy(*args, **kwargs):
        eventos.append(args[1])
        return validar_original(*args, **kwargs)

    monkeypatch.setattr(servicio_prestamos_mod, "validar_transicion", validar_spy)

    devuelto = servicio.registrar_devolucion(
        "PREST-DEVUELTO-LIMITE",
        _encargado(),
        fecha_devolucion=date(2026, 9, 12),
    )

    persistido = repo_prestamos.obtener("PREST-DEVUELTO-LIMITE")
    assert eventos == [EventoTransicion.REGISTRAR_DEVOLUCION]
    assert EventoTransicion.MARCAR_ATRASO not in eventos
    assert devuelto.estado is EstadoPrestamo.DEVUELTA
    assert persistido.estado is EstadoPrestamo.DEVUELTA
    assert persistido.estado is not EstadoPrestamo.ATRASADA
    assert persistido.fecha_devolucion == date(2026, 9, 12)
    assert repo_equipos.obtener("EQ-BORDE-01").estado is EstadoEquipo.DISPONIBLE


@pytest.mark.borde
def test_CP08_RF08_inicio_igual_a_termino_de_reserva_existente_rechaza_por_rn10(
    tmp_path: Path,
) -> None:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    existente = _prestamo(
        "PREST-EXISTENTE",
        equipos=("EQ-SOLAPE",),
        estado=EstadoPrestamo.APROBADA,
        fecha_inicio=date(2026, 9, 10),
        fecha_termino=date(2026, 9, 14),
        fecha_aprobacion=date(2026, 9, 10),
    )
    candidato = _prestamo(
        "PREST-SOLAPE-LIMITE",
        equipos=("EQ-SOLAPE",),
        estado=EstadoPrestamo.SOLICITADA,
        fecha_inicio=date(2026, 9, 14),
        fecha_termino=date(2026, 9, 16),
    )
    equipo_disponible_fisicamente = _equipo("EQ-SOLAPE", estado=EstadoEquipo.DISPONIBLE)
    repo_prestamos.guardar(existente)
    repo_prestamos.guardar(candidato)

    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            candidato,
            EventoTransicion.APROBAR_SOLICITUD,
            _encargado(),
            fecha_actual=FECHA_CONTROL,
            equipos={"EQ-SOLAPE": equipo_disponible_fisicamente},
            prestamos_existentes=repo_prestamos.listar(),
            solicitante=_solicitante(),
        )

    assert equipo_disponible_fisicamente.estado is EstadoEquipo.DISPONIBLE
    assert exc_info.value.regla == "RN-10"
    assert "RN-10" in exc_info.value.mensaje
    assert repo_prestamos.obtener("PREST-SOLAPE-LIMITE").estado is EstadoPrestamo.SOLICITADA


@pytest.mark.borde
def test_CP09_RF06_fecha_inicio_igual_a_fecha_termino_habil_cuenta_un_dia(
    tmp_path: Path,
) -> None:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    fecha_un_dia_habil = date(2026, 9, 14)
    solicitud = _prestamo(
        "PREST-UN-DIA",
        equipos=("EQ-UN-DIA",),
        estado=EstadoPrestamo.SOLICITADA,
        fecha_inicio=fecha_un_dia_habil,
        fecha_termino=fecha_un_dia_habil,
    )
    repo_prestamos.guardar(solicitud)

    transicion = validar_transicion(
        solicitud,
        EventoTransicion.CREAR_SOLICITUD,
        _solicitante(),
        fecha_actual=FECHA_CONTROL,
        equipos={"EQ-UN-DIA": _equipo("EQ-UN-DIA")},
        prestamos_existentes=repo_prestamos.listar(),
    )

    assert fecha_un_dia_habil.weekday() < 5
    assert dias_habiles(fecha_un_dia_habil, fecha_un_dia_habil) == 1
    assert transicion.id == "T-01"
    assert transicion.destino is EstadoPrestamo.SOLICITADA
    assert repo_prestamos.obtener("PREST-UN-DIA") == solicitud
