"""Casos de combinacion de reglas y escenario completo: CP-13 a CP-15.

CP-13 y CP-14 combinan RN-16 y RN-15 con RN-07 desde los dos lados del mismo
contador. RN-07 no es una regla independiente: su limite de tres equipos
activos se calcula recorriendo la maquina de estados, sumando solo los
prestamos cuyo estado esta en `ESTADOS_DISPONIBILIDAD_BLOQUEADA`.

    if existente.estado in ESTADOS_DISPONIBILIDAD_BLOQUEADA:
        activos += len(existente.equipos)

`ATRASADA` esta dentro de ese conjunto y `CANCELADA` no. De ahi las dos
direcciones que prueban los casos: atrasarse **retiene** el cupo, cancelar lo
**libera**, y en ambos la aritmetica se afirma leyendo `detalles` del error, que
es lo unico que distingue "el contador funciono" de "el contador coincidio".

CP-15 no prueba una regla: prueba que los cinco servicios comparten estado a
traves de los archivos JSON durante un ciclo de vida completo. Por eso releen
del repositorio en cada paso en vez de encadenar el objeto devuelto por la
llamada anterior; encadenarlo probaria que los servicios devuelven lo que
prometen, no que lo persisten.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from prestamos.auth import ServicioAuth, hash_contrasena
from prestamos.errores import ErrorValidacion
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.repositorios.json_repo import RepositorioJson
from prestamos.servicios.equipos import ServicioEquipos
from prestamos.servicios.prestamos import ServicioPrestamos
from prestamos.servicios.solicitudes import ServicioSolicitudes
from prestamos.servicios.usuarios import ServicioUsuarios, crear_encargado_inicial

CONTRASENA_INTEGRACION = "Clave-Integracion-2026"

# Jueves 10 de septiembre de 2026 para CP-13 y CP-14, la misma ancla que usan
# los casos funcionales, de borde y negativos. CP-15 arranca el lunes 7 porque
# necesita recorrer dos semanas completas: RN-08 cuenta dias habiles y RN-16
# exige que el termino quede vencido, y ambas cosas cambian de significado si
# el escenario empieza un viernes.
FECHA_CONTROL = date(2026, 9, 10)

# Mismo criterio que `tests/negativos/test_negativos.py`: logger propio sin
# handlers de archivo, para que `registrar_evento` no caiga en
# `configurar_logging()` y deje un `FileHandler` vivo despues de la prueba.
_LOGGER_PRUEBAS = logging.getLogger("pruebas.integracion")
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
        nombre=f"Usuario integracion {id_usuario}",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        hash_contrasena=hash_contrasena(CONTRASENA_INTEGRACION, iteraciones=1),
    )


def _encargado(id_usuario: str = "enc-integracion") -> Usuario:
    return _usuario(id_usuario, rol=Rol.ENCARGADO)


def _solicitante(id_usuario: str = "sol-integracion") -> Usuario:
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
        descripcion="Equipo para caso de integracion",
        estado=estado,
    )


def _prestamo(
    id_prestamo: str,
    *,
    id_solicitante: str = "sol-integracion",
    equipos: tuple[str, ...] = ("EQ-INT-01",),
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
        motivo="Caso de integracion documentado",
        estado=estado,
        fecha_solicitud=fecha_solicitud,
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        fecha_aprobacion=fecha_aprobacion,
        fecha_entrega=fecha_entrega,
        fecha_devolucion=fecha_devolucion,
    )


@dataclass
class Sistema:
    """Los cinco servicios montados sobre los mismos tres archivos JSON.

    Compartir las instancias de repositorio es el punto: si cada servicio
    abriera su propio `RepositorioJson`, el escenario seguiria pasando y no
    probaria nada sobre la integracion.
    """

    repo_prestamos: RepositorioJson[Prestamo]
    repo_equipos: RepositorioJson[Equipo]
    repo_usuarios: RepositorioJson[Usuario]
    auth: ServicioAuth
    usuarios: ServicioUsuarios
    equipos: ServicioEquipos
    solicitudes: ServicioSolicitudes
    prestamos: ServicioPrestamos


def _sistema(tmp_path: Path) -> Sistema:
    repo_prestamos = RepositorioJson(tmp_path / "solicitudes.json", Prestamo, "id")
    repo_equipos = RepositorioJson(tmp_path / "equipos.json", Equipo, "codigo")
    repo_usuarios = RepositorioJson(tmp_path / "usuarios.json", Usuario, "id")
    auth = ServicioAuth(repo_usuarios, logger=_LOGGER_PRUEBAS)
    return Sistema(
        repo_prestamos=repo_prestamos,
        repo_equipos=repo_equipos,
        repo_usuarios=repo_usuarios,
        auth=auth,
        usuarios=ServicioUsuarios(
            auth, repo_usuarios, logger=_LOGGER_PRUEBAS, iteraciones_hash=1
        ),
        equipos=ServicioEquipos(
            auth, repo_equipos, repo_prestamos, logger=_LOGGER_PRUEBAS
        ),
        solicitudes=ServicioSolicitudes(
            auth,
            repo_prestamos,
            repo_equipos,
            repo_usuarios,
            logger=_LOGGER_PRUEBAS,
        ),
        prestamos=ServicioPrestamos(repo_prestamos, repo_equipos),
    )


@pytest.mark.combinacion
def test_CP13_RF07_el_atraso_retiene_el_cupo_de_equipos_activos_rn16_y_rn07(
    tmp_path: Path,
) -> None:
    """RN-16 x RN-07: vencer el plazo no devuelve el cupo, lo congela.

    La intuicion equivocada que el caso descarta es que un prestamo cuyo plazo
    ya vencio deja de "estar activo". RN-16 lo mueve a `ATRASADA`, que sigue
    dentro de `ESTADOS_DISPONIBILIDAD_BLOQUEADA`, asi que RN-07 lo cuenta igual.

    La asercion que prueba la interaccion es `detalles["equipos_activos"] == 3`:
    ese 3 solo puede venir del prestamo atrasado. Si `ATRASADA` saliera del
    conjunto, caeria a 0 y el caso fallaria senalando exactamente que se rompio.
    """

    sistema = _sistema(tmp_path)
    solicitante = _solicitante()
    sistema.repo_usuarios.guardar(solicitante)
    sistema.repo_usuarios.guardar(_encargado())
    for codigo in ("EQ-INT-01", "EQ-INT-02", "EQ-INT-03"):
        sistema.repo_equipos.guardar(_equipo(codigo, estado=EstadoEquipo.PRESTADO))
    sistema.repo_equipos.guardar(_equipo("EQ-INT-04"))
    sistema.repo_prestamos.guardar(
        _prestamo(
            "P-TRES-ENTREGADOS",
            equipos=("EQ-INT-01", "EQ-INT-02", "EQ-INT-03"),
            estado=EstadoPrestamo.ENTREGADA,
            fecha_inicio=date(2026, 9, 7),
            fecha_termino=date(2026, 9, 9),
            fecha_solicitud=date(2026, 9, 4),
            fecha_aprobacion=date(2026, 9, 4),
            fecha_entrega=date(2026, 9, 7),
        )
    )

    atrasado = sistema.prestamos.marcar_atraso(
        "P-TRES-ENTREGADOS",
        usuario=_encargado(),
        fecha_actual=FECHA_CONTROL,
    )

    assert atrasado.estado is EstadoPrestamo.ATRASADA
    assert sistema.repo_prestamos.obtener("P-TRES-ENTREGADOS").estado is EstadoPrestamo.ATRASADA

    sistema.auth.iniciar_sesion(solicitante.id, CONTRASENA_INTEGRACION)

    with pytest.raises(ErrorValidacion) as exc_info:
        sistema.solicitudes.crear_solicitud(
            ["EQ-INT-04"],
            "Cuarto equipo mientras el prestamo sigue atrasado",
            date(2026, 9, 14),
            date(2026, 9, 16),
            fecha_solicitud=FECHA_CONTROL,
        )

    error = exc_info.value
    assert error.codigo == "ERROR_VALIDACION"
    assert error.regla == "RN-07"
    assert error.mensaje == "El solicitante no puede superar 3 equipos activos (RN-07)."
    assert error.detalles == {
        "id_solicitante": "sol-integracion",
        "equipos_activos": 3,
        "equipos_solicitados": 1,
        "total": 4,
    }
    assert [p.id for p in sistema.repo_prestamos.listar()] == ["P-TRES-ENTREGADOS"]
    assert sistema.repo_equipos.obtener("EQ-INT-04").estado is EstadoEquipo.DISPONIBLE


@pytest.mark.combinacion
def test_CP14_RF07_la_cancelacion_libera_solo_el_cupo_cancelado_rn15_y_rn07(
    tmp_path: Path,
) -> None:
    """RN-15 x RN-07: cancelar libera cupo, y libera exactamente el que ocupaba.

    El cupo se reparte 2 + 1 en dos reservas a proposito. Cancelando la de tres
    equipos el contador caeria a 0 y cualquier solicitud posterior pasaria: el
    caso no distinguiria un contador correcto de uno que se reinicia. Cancelando
    la de un equipo, el limite queda en 2 y la aritmetica se vuelve exigente:
    una solicitud de dos equipos sigue rechazada y una de uno pasa.
    """

    sistema = _sistema(tmp_path)
    solicitante = _solicitante()
    sistema.repo_usuarios.guardar(solicitante)
    for codigo in ("EQ-INT-01", "EQ-INT-02", "EQ-INT-03"):
        sistema.repo_equipos.guardar(_equipo(codigo, estado=EstadoEquipo.RESERVADO))
    for codigo in ("EQ-INT-04", "EQ-INT-05"):
        sistema.repo_equipos.guardar(_equipo(codigo))
    sistema.repo_prestamos.guardar(
        _prestamo(
            "P-DOS-EQUIPOS",
            equipos=("EQ-INT-01", "EQ-INT-02"),
            estado=EstadoPrestamo.APROBADA,
            fecha_aprobacion=FECHA_CONTROL,
        )
    )
    sistema.repo_prestamos.guardar(
        _prestamo(
            "P-UN-EQUIPO",
            equipos=("EQ-INT-03",),
            estado=EstadoPrestamo.APROBADA,
            fecha_aprobacion=FECHA_CONTROL,
        )
    )
    sistema.auth.iniciar_sesion(solicitante.id, CONTRASENA_INTEGRACION)

    # Punto de partida: 3 equipos activos, el limite exacto de RN-07.
    with pytest.raises(ErrorValidacion) as exc_saturado:
        sistema.solicitudes.crear_solicitud(
            ["EQ-INT-04", "EQ-INT-05"],
            "Dos equipos mas con el cupo saturado",
            date(2026, 9, 14),
            date(2026, 9, 16),
            fecha_solicitud=FECHA_CONTROL,
        )

    assert exc_saturado.value.regla == "RN-07"
    assert exc_saturado.value.detalles["equipos_activos"] == 3
    assert exc_saturado.value.detalles["total"] == 5

    cancelado = sistema.prestamos.cancelar(
        "P-UN-EQUIPO",
        solicitante,
        "Ya no se necesita el tercer equipo",
        fecha_actual=FECHA_CONTROL,
    )

    assert cancelado.estado is EstadoPrestamo.CANCELADA
    assert sistema.repo_prestamos.obtener("P-UN-EQUIPO").estado is EstadoPrestamo.CANCELADA
    assert sistema.repo_equipos.obtener("EQ-INT-03").estado is EstadoEquipo.DISPONIBLE

    # RN-15 libero un equipo, no los tres: dos siguen activos en P-DOS-EQUIPOS.
    with pytest.raises(ErrorValidacion) as exc_parcial:
        sistema.solicitudes.crear_solicitud(
            ["EQ-INT-04", "EQ-INT-05"],
            "Dos equipos con un solo cupo liberado",
            date(2026, 9, 14),
            date(2026, 9, 16),
            fecha_solicitud=FECHA_CONTROL,
        )

    assert exc_parcial.value.regla == "RN-07"
    assert exc_parcial.value.detalles["equipos_activos"] == 2
    assert exc_parcial.value.detalles["total"] == 4

    creada = sistema.solicitudes.crear_solicitud(
        ["EQ-INT-04"],
        "Un equipo, que es justo el cupo liberado",
        date(2026, 9, 14),
        date(2026, 9, 16),
        fecha_solicitud=FECHA_CONTROL,
    )

    assert creada.estado is EstadoPrestamo.SOLICITADA
    assert creada.equipos == ("EQ-INT-04",)
    assert sistema.repo_prestamos.obtener(creada.id).estado is EstadoPrestamo.SOLICITADA
    assert sistema.repo_equipos.obtener("EQ-INT-05").estado is EstadoEquipo.DISPONIBLE


@pytest.mark.escenario
def test_CP15_RF01_a_RF12_ciclo_completo_sobre_persistencia_real(
    tmp_path: Path,
) -> None:
    """Escenario de punta a punta sobre los archivos JSON reales.

    Recorre login, registro de usuario y equipos, solicitud, aprobacion,
    entrega, atraso, devolucion y consulta final, avanzando un calendario
    explicito. Ningun paso usa mocks ni dobles: los cinco servicios escriben en
    los mismos `usuarios.json`, `equipos.json` y `solicitudes.json` de
    `tmp_path`, y cada asercion relee del repositorio.

    La reserva futura B existe para que la consulta final discrimine. Con un
    solo prestamo el cierre devolveria tres listas vacias, que no distinguiria
    un clasificador correcto de uno que no devuelve nada.
    """

    sistema = _sistema(tmp_path)
    lunes = date(2026, 9, 7)

    # --- RF-01 / RF-02: primer encargado y sesion -------------------------
    encargado = crear_encargado_inicial(
        "enc-e2e",
        "Encargada del laboratorio",
        "enc-e2e@usm.cl",
        CONTRASENA_INTEGRACION,
        repositorio=sistema.repo_usuarios,
        logger=_LOGGER_PRUEBAS,
        iteraciones_hash=1,
    )
    sesion = sistema.auth.iniciar_sesion("enc-e2e", CONTRASENA_INTEGRACION)

    assert sesion.usuario.id == "enc-e2e"
    assert sistema.repo_usuarios.obtener("enc-e2e").rol is Rol.ENCARGADO
    assert CONTRASENA_INTEGRACION not in sistema.repo_usuarios.obtener(
        "enc-e2e"
    ).a_dict()["hash_contrasena"]

    # --- RF-01 / RF-03: registro de solicitante y catalogo ----------------
    sistema.usuarios.registrar_usuario(
        "sol-e2e",
        "Solicitante del laboratorio",
        "sol-e2e@usm.cl",
        Rol.SOLICITANTE,
        CONTRASENA_INTEGRACION,
    )
    sistema.equipos.registrar_equipo(
        "EQ-E2E-01", "Osciloscopio", "instrumento", "Osciloscopio de banco"
    )
    sistema.equipos.registrar_equipo(
        "EQ-E2E-02", "Multimetro", "instrumento", "Multimetro de precision"
    )

    assert sistema.repo_usuarios.obtener("sol-e2e").activo is True
    assert sistema.repo_equipos.obtener("EQ-E2E-01").estado is EstadoEquipo.DISPONIBLE
    assert sistema.repo_equipos.obtener("EQ-E2E-02").estado is EstadoEquipo.DISPONIBLE

    # --- RF-05: el solicitante pide el equipo principal -------------------
    sistema.auth.cerrar_sesion()
    sistema.auth.iniciar_sesion("sol-e2e", CONTRASENA_INTEGRACION)
    solicitud_a = sistema.solicitudes.crear_solicitud(
        ["EQ-E2E-01"],
        "Practico de mediciones",
        date(2026, 9, 8),
        date(2026, 9, 10),
        fecha_solicitud=lunes,
    )
    solicitud_b = sistema.solicitudes.crear_solicitud(
        ["EQ-E2E-02"],
        "Practico de la semana siguiente",
        date(2026, 9, 15),
        date(2026, 9, 17),
        fecha_solicitud=lunes,
    )

    assert sistema.repo_prestamos.obtener(solicitud_a.id).estado is EstadoPrestamo.SOLICITADA
    assert sistema.repo_prestamos.obtener(solicitud_b.id).estado is EstadoPrestamo.SOLICITADA

    # --- RF-08: el encargado aprueba las dos ------------------------------
    sistema.auth.cerrar_sesion()
    sistema.auth.iniciar_sesion("enc-e2e", CONTRASENA_INTEGRACION)
    sistema.solicitudes.aprobar(solicitud_a.id, fecha_aprobacion=lunes)
    sistema.solicitudes.aprobar(solicitud_b.id, fecha_aprobacion=lunes)

    assert sistema.repo_prestamos.obtener(solicitud_a.id).estado is EstadoPrestamo.APROBADA
    assert sistema.repo_prestamos.obtener(solicitud_b.id).estado is EstadoPrestamo.APROBADA
    assert sistema.repo_equipos.obtener("EQ-E2E-01").estado is EstadoEquipo.RESERVADO
    assert sistema.repo_equipos.obtener("EQ-E2E-02").estado is EstadoEquipo.RESERVADO

    # --- RF-09: entrega del equipo principal ------------------------------
    sistema.prestamos.registrar_entrega(
        solicitud_a.id,
        encargado,
        fecha_entrega=date(2026, 9, 8),
    )

    assert sistema.repo_prestamos.obtener(solicitud_a.id).estado is EstadoPrestamo.ENTREGADA
    assert sistema.repo_prestamos.obtener(solicitud_a.id).fecha_entrega == date(2026, 9, 8)
    assert sistema.repo_equipos.obtener("EQ-E2E-01").estado is EstadoEquipo.PRESTADO
    # La reserva futura de otro equipo no se ve afectada por la entrega.
    assert sistema.repo_equipos.obtener("EQ-E2E-02").estado is EstadoEquipo.RESERVADO

    # --- RN-16: el plazo vence y se marca el atraso -----------------------
    viernes = date(2026, 9, 11)
    sistema.prestamos.marcar_atraso(
        solicitud_a.id,
        usuario=encargado,
        fecha_actual=viernes,
    )

    assert sistema.repo_prestamos.obtener(solicitud_a.id).estado is EstadoPrestamo.ATRASADA
    assert sistema.prestamos.prestamos_atrasados(encargado, fecha_actual=viernes) == [
        sistema.repo_prestamos.obtener(solicitud_a.id)
    ]

    # --- RF-10: devolucion atrasada, que transita T-09 y no T-08 ----------
    lunes_siguiente = date(2026, 9, 14)
    devuelto = sistema.prestamos.registrar_devolucion(
        solicitud_a.id,
        encargado,
        fecha_devolucion=lunes_siguiente,
    )

    persistido = sistema.repo_prestamos.obtener(solicitud_a.id)
    assert devuelto.estado is EstadoPrestamo.DEVUELTA
    assert persistido.estado is EstadoPrestamo.DEVUELTA
    assert persistido.fecha_devolucion == lunes_siguiente
    assert persistido.fecha_entrega == date(2026, 9, 8)
    assert sistema.repo_equipos.obtener("EQ-E2E-01").estado is EstadoEquipo.DISPONIBLE

    # --- RF-12: consulta final ---------------------------------------------
    reserva_viva = sistema.repo_prestamos.obtener(solicitud_b.id)
    futuros = sistema.prestamos.prestamos_futuros(encargado, fecha_actual=lunes_siguiente)
    vigentes = sistema.prestamos.prestamos_vigentes(encargado, fecha_actual=lunes_siguiente)
    atrasados = sistema.prestamos.prestamos_atrasados(encargado, fecha_actual=lunes_siguiente)

    assert [p.id for p in futuros] == [solicitud_b.id]
    assert reserva_viva.estado is EstadoPrestamo.APROBADA
    assert vigentes == []
    assert atrasados == []
    assert {p.id for p in sistema.repo_prestamos.listar()} == {
        solicitud_a.id,
        solicitud_b.id,
    }
