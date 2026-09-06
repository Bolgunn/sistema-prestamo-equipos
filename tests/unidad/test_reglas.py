"""Pruebas unitarias del motor de reglas y transiciones (issue #9)."""

from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import date, timedelta

import pytest

import prestamos.reglas as reglas
from prestamos.errores import ErrorAutorizacion, ErrorValidacion, TransicionNoPermitida
from prestamos.modelos import Equipo, EstadoEquipo, EstadoPrestamo, Prestamo, Rol, Usuario
from prestamos.reglas import (
    EventoTransicion,
    TRANSICIONES_PERMITIDAS,
    validar_transicion,
)


HOY = date(2026, 9, 7)


def usuario(
    id_usuario: str = "sol-1",
    rol: Rol = Rol.SOLICITANTE,
    *,
    activo: bool = True,
) -> Usuario:
    return Usuario(
        id=id_usuario,
        nombre="Usuario de prueba",
        correo=f"{id_usuario}@usm.cl",
        rol=rol,
        activo=activo,
        hash_contrasena="pbkdf2$1$sal$digest",
    )


def equipo(
    codigo: str = "EQ-01",
    estado: EstadoEquipo = EstadoEquipo.DISPONIBLE,
) -> Equipo:
    return Equipo(
        codigo=codigo,
        nombre="Notebook",
        tipo="computador",
        descripcion="Notebook de laboratorio",
        estado=estado,
    )


def prestamo(
    *,
    id_prestamo: str = "P-01",
    id_solicitante: str = "sol-1",
    equipos: tuple[str, ...] = ("EQ-01",),
    estado: EstadoPrestamo = EstadoPrestamo.SOLICITADA,
    fecha_inicio: date = date(2026, 9, 8),
    fecha_termino: date = date(2026, 9, 10),
    fecha_aprobacion: date | None = None,
    fecha_entrega: date | None = None,
    fecha_devolucion: date | None = None,
    motivo_rechazo: str | None = None,
    motivo_cancelacion: str | None = None,
) -> Prestamo:
    return Prestamo(
        id=id_prestamo,
        id_solicitante=id_solicitante,
        equipos=equipos,
        motivo="Proyecto de electronica",
        estado=estado,
        fecha_solicitud=HOY,
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        fecha_aprobacion=fecha_aprobacion,
        fecha_entrega=fecha_entrega,
        fecha_devolucion=fecha_devolucion,
        motivo_rechazo=motivo_rechazo,
        motivo_cancelacion=motivo_cancelacion,
    )


def test_tabla_contiene_las_nueve_transiciones_documentadas() -> None:
    assert {transicion.id for transicion in TRANSICIONES_PERMITIDAS.values()} == {
        "T-01",
        "T-02",
        "T-03",
        "T-04",
        "T-05",
        "T-06",
        "T-07",
        "T-08",
        "T-09",
    }
    assert (
        TRANSICIONES_PERMITIDAS[
            (EstadoPrestamo.SOLICITADA, EventoTransicion.APROBAR_SOLICITUD)
        ].destino
        is EstadoPrestamo.APROBADA
    )


def test_transiciones_t01_a_t09_tienen_casos_exitosos() -> None:
    casos = [
        (
            "T-01",
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            {
                "fecha_actual": HOY,
                "equipos": [equipo()],
                "prestamos_existentes": [],
            },
        ),
        (
            "T-02",
            prestamo(),
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            {
                "fecha_actual": HOY,
                "equipos": [equipo()],
                "prestamos_existentes": [],
                "solicitante": usuario(),
            },
        ),
        (
            "T-03",
            prestamo(),
            EventoTransicion.RECHAZAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            {"fecha_actual": HOY, "motivo_rechazo": "No cumple prioridad"},
        ),
        (
            "T-04",
            prestamo(),
            EventoTransicion.CANCELAR_SOLICITUD,
            usuario(),
            {"fecha_actual": HOY, "motivo_cancelacion": "Ya no se requiere"},
        ),
        (
            "T-05",
            prestamo(estado=EstadoPrestamo.APROBADA),
            EventoTransicion.CANCELAR_SOLICITUD,
            usuario(),
            {"fecha_actual": HOY, "motivo_cancelacion": "Cambio de plan"},
        ),
        (
            "T-06",
            prestamo(
                estado=EstadoPrestamo.APROBADA,
                fecha_aprobacion=date(2026, 9, 7),
            ),
            EventoTransicion.REGISTRAR_ENTREGA,
            usuario("enc-1", Rol.ENCARGADO),
            {
                "fecha_actual": HOY,
                "fecha_operacion": date(2026, 9, 8),
                "equipos": [equipo()],
            },
        ),
        (
            "T-07",
            prestamo(
                estado=EstadoPrestamo.ENTREGADA,
                fecha_termino=date(2026, 9, 8),
            ),
            EventoTransicion.MARCAR_ATRASO,
            None,
            {"fecha_actual": date(2026, 9, 9)},
        ),
        (
            "T-08",
            prestamo(
                estado=EstadoPrestamo.ENTREGADA,
                fecha_entrega=date(2026, 9, 8),
            ),
            EventoTransicion.REGISTRAR_DEVOLUCION,
            usuario("enc-1", Rol.ENCARGADO),
            {
                "fecha_actual": HOY,
                "fecha_operacion": date(2026, 9, 10),
                "equipos_devueltos": ["EQ-01"],
            },
        ),
        (
            "T-09",
            prestamo(
                estado=EstadoPrestamo.ATRASADA,
                fecha_entrega=date(2026, 9, 8),
            ),
            EventoTransicion.REGISTRAR_DEVOLUCION_ATRASADA,
            usuario("enc-1", Rol.ENCARGADO),
            {
                "fecha_actual": date(2026, 9, 12),
                "fecha_operacion": date(2026, 9, 12),
                "equipos_devueltos": ["EQ-01"],
            },
        ),
    ]

    for id_transicion, solicitud, evento, operador, contexto in casos:
        transicion = validar_transicion(solicitud, evento, operador, **contexto)

        assert transicion.id == id_transicion


def test_validar_transicion_no_depende_de_auth_py() -> None:
    assert "prestamos.auth" not in inspect.getsource(reglas)


def test_crear_solicitud_valida_estado_rol_fechas_equipos_y_limite() -> None:
    transicion = validar_transicion(
        prestamo(equipos=("EQ-01", "EQ-02")),
        "crear solicitud",
        usuario(),
        fecha_actual=HOY,
        equipos=[equipo("EQ-01"), equipo("EQ-02")],
        prestamos_existentes=[
            prestamo(
                id_prestamo="P-00",
                equipos=("EQ-03",),
                estado=EstadoPrestamo.DEVUELTA,
            )
        ],
    )

    assert transicion.id == "T-01"
    assert transicion.destino is EstadoPrestamo.SOLICITADA


def test_crear_solicitud_rechaza_equipo_no_disponible_con_rn05() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            equipos=[equipo(estado=EstadoEquipo.MANTENCION)],
            prestamos_existentes=[],
        )

    assert exc_info.value.regla == "RN-05"
    assert "RN-05" in exc_info.value.mensaje


def test_crear_solicitud_rechaza_mas_de_tres_equipos_activos_con_rn07() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(equipos=("EQ-01", "EQ-02")),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            equipos=[equipo("EQ-01"), equipo("EQ-02")],
            prestamos_existentes=[
                prestamo(
                    id_prestamo="P-00",
                    equipos=("EQ-03", "EQ-04"),
                    estado=EstadoPrestamo.APROBADA,
                )
            ],
        )

    assert exc_info.value.regla == "RN-07"
    assert "RN-07" in exc_info.value.mensaje


def test_crear_solicitud_rechaza_duracion_mayor_a_cinco_habiles_con_rn08() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(fecha_inicio=date(2026, 9, 7), fecha_termino=date(2026, 9, 15)),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            prestamos_existentes=[],
        )

    assert exc_info.value.regla == "RN-08"
    assert "RN-08" in exc_info.value.mensaje


def test_crear_solicitud_rechaza_inicio_fuera_de_ventana_con_rn09() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(fecha_inicio=date(2026, 10, 6), fecha_termino=date(2026, 10, 7)),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            prestamos_existentes=[],
        )

    assert exc_info.value.regla == "RN-09"
    assert "RN-09" in exc_info.value.mensaje


def test_aprobar_revalida_disponibilidad_y_solapamiento_con_rn10() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            equipos=[equipo()],
            prestamos_existentes=[
                prestamo(
                    id_prestamo="P-00",
                    estado=EstadoPrestamo.APROBADA,
                    fecha_inicio=date(2026, 9, 10),
                    fecha_termino=date(2026, 9, 11),
                )
            ],
            solicitante=usuario(),
        )

    assert exc_info.value.regla == "RN-10"
    assert "RN-10" in exc_info.value.mensaje


def test_aprobar_rechaza_usuario_sin_rol_encargado_con_rn11() -> None:
    with pytest.raises(ErrorAutorizacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.APROBAR_SOLICITUD,
            usuario(rol=Rol.SOLICITANTE),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-11"
    assert "RN-11" in exc_info.value.mensaje


def test_aprobar_estado_no_solicitado_falla_con_rn12() -> None:
    with pytest.raises(TransicionNoPermitida) as exc_info:
        validar_transicion(
            prestamo(estado=EstadoPrestamo.APROBADA),
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-12"
    assert "RN-12" in exc_info.value.mensaje


def test_rechazar_exige_motivo_con_rn17() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.RECHAZAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-17"
    assert "RN-17" in exc_info.value.mensaje


def test_cancelar_permite_solicitante_dueno_y_bloquea_terceros_con_rn15() -> None:
    valida = validar_transicion(
        prestamo(),
        EventoTransicion.CANCELAR_SOLICITUD,
        usuario(),
        fecha_actual=HOY,
        motivo_cancelacion="Ya no se usara",
    )
    assert valida.id == "T-04"

    with pytest.raises(ErrorAutorizacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.CANCELAR_SOLICITUD,
            usuario("otro-sol", Rol.SOLICITANTE),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-15"
    assert "RN-15" in exc_info.value.mensaje


def test_cancelar_por_encargado_exige_motivo_con_rn15() -> None:
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.CANCELAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-15"
    assert "RN-15" in exc_info.value.mensaje


def test_entrega_exige_aprobada_y_fecha_no_anterior_a_aprobacion_con_rn13() -> None:
    with pytest.raises(TransicionNoPermitida) as exc_estado:
        validar_transicion(
            prestamo(estado=EstadoPrestamo.SOLICITADA),
            EventoTransicion.REGISTRAR_ENTREGA,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_estado.value.regla == "RN-13"

    with pytest.raises(ErrorValidacion) as exc_fecha:
        validar_transicion(
            prestamo(
                estado=EstadoPrestamo.APROBADA,
                fecha_aprobacion=date(2026, 9, 9),
            ),
            EventoTransicion.REGISTRAR_ENTREGA,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            fecha_operacion=date(2026, 9, 8),
        )

    assert exc_fecha.value.regla == "RN-13"
    assert "RN-13" in exc_fecha.value.mensaje


def test_devolucion_exige_estado_y_todos_los_equipos_con_rn14() -> None:
    with pytest.raises(TransicionNoPermitida) as exc_estado:
        validar_transicion(
            prestamo(estado=EstadoPrestamo.APROBADA),
            EventoTransicion.REGISTRAR_DEVOLUCION,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_estado.value.regla == "RN-14"

    with pytest.raises(ErrorValidacion) as exc_equipos:
        validar_transicion(
            prestamo(
                equipos=("EQ-01", "EQ-02"),
                estado=EstadoPrestamo.ENTREGADA,
                fecha_entrega=date(2026, 9, 8),
            ),
            EventoTransicion.REGISTRAR_DEVOLUCION,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            fecha_operacion=date(2026, 9, 10),
            equipos_devueltos=["EQ-01"],
        )

    assert exc_equipos.value.regla == "RN-14"
    assert "RN-14" in exc_equipos.value.mensaje


def test_cancelar_entregada_no_esta_permitido_con_rn15() -> None:
    with pytest.raises(TransicionNoPermitida) as exc_info:
        validar_transicion(
            prestamo(estado=EstadoPrestamo.ENTREGADA),
            EventoTransicion.CANCELAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-15"
    assert "RN-15" in exc_info.value.mensaje


def test_marcar_atraso_solo_despues_del_dia_de_termino_con_rn16() -> None:
    dentro_de_plazo = prestamo(
        estado=EstadoPrestamo.ENTREGADA,
        fecha_termino=date(2026, 9, 10),
    )
    with pytest.raises(ErrorValidacion) as exc_info:
        validar_transicion(
            dentro_de_plazo,
            EventoTransicion.MARCAR_ATRASO,
            None,
            fecha_actual=date(2026, 9, 10),
        )

    assert exc_info.value.regla == "RN-16"
    assert "RN-16" in exc_info.value.mensaje

    transicion = validar_transicion(
        dentro_de_plazo,
        EventoTransicion.MARCAR_ATRASO,
        None,
        fecha_actual=date(2026, 9, 11),
    )
    assert transicion.id == "T-07"


def test_usuario_inactivo_no_puede_operar_con_rn02() -> None:
    with pytest.raises(ErrorAutorizacion) as exc_info:
        validar_transicion(
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(activo=False),
            fecha_actual=HOY,
        )

    assert exc_info.value.regla == "RN-02"
    assert "RN-02" in exc_info.value.mensaje


def test_equipo_atrasado_bloquea_disponibilidad_sin_importar_el_rango() -> None:
    disponible = reglas.equipo_disponible(
        equipo(),
        date(2026, 10, 1),
        date(2026, 10, 2),
        prestamos_existentes=[
            prestamo(
                id_prestamo="P-00",
                estado=EstadoPrestamo.ATRASADA,
                fecha_inicio=date(2026, 9, 1),
                fecha_termino=date(2026, 9, 3),
            )
        ],
    )

    assert disponible is False


def test_solapamiento_es_inclusivo() -> None:
    assert reglas.hay_solapamiento(
        date(2026, 9, 3),
        date(2026, 9, 4),
        date(2026, 9, 1),
        date(2026, 9, 3),
    )
    assert not reglas.hay_solapamiento(
        date(2026, 9, 4),
        date(2026, 9, 5),
        date(2026, 9, 1),
        date(2026, 9, 3),
    )


def test_validar_transicion_no_muta_el_prestamo() -> None:
    original = prestamo()
    copia = replace(original)

    validar_transicion(
        original,
        EventoTransicion.APROBAR_SOLICITUD,
        usuario("enc-1", Rol.ENCARGADO),
        fecha_actual=HOY,
        equipos=[equipo()],
        prestamos_existentes=[],
        solicitante=usuario(),
    )

    assert original == copia


def test_crear_y_aprobar_exigen_contexto_para_guardas_de_disponibilidad() -> None:
    with pytest.raises(ErrorValidacion) as exc_prestamos:
        validar_transicion(
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            equipos=[equipo()],
        )

    assert exc_prestamos.value.regla == "RN-17"
    assert exc_prestamos.value.detalles["contexto_requerido"] == "prestamos_existentes"

    with pytest.raises(ErrorValidacion) as exc_equipos:
        validar_transicion(
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            prestamos_existentes=[],
        )

    assert exc_equipos.value.regla == "RN-17"
    assert exc_equipos.value.detalles["contexto_requerido"] == "equipos"

    with pytest.raises(ErrorValidacion) as exc_solicitante:
        validar_transicion(
            prestamo(),
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            equipos=[equipo()],
            prestamos_existentes=[],
        )

    assert exc_solicitante.value.regla == "RN-17"
    assert exc_solicitante.value.detalles["contexto_requerido"] == "solicitante"


def test_entrega_y_devolucion_exigen_contexto_para_guardas_propias() -> None:
    with pytest.raises(ErrorValidacion) as exc_equipos:
        validar_transicion(
            prestamo(
                estado=EstadoPrestamo.APROBADA,
                fecha_aprobacion=date(2026, 9, 7),
            ),
            EventoTransicion.REGISTRAR_ENTREGA,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            fecha_operacion=date(2026, 9, 8),
        )

    assert exc_equipos.value.regla == "RN-17"
    assert exc_equipos.value.detalles["contexto_requerido"] == "equipos"

    with pytest.raises(ErrorValidacion) as exc_devueltos:
        validar_transicion(
            prestamo(
                estado=EstadoPrestamo.ENTREGADA,
                fecha_entrega=date(2026, 9, 8),
            ),
            EventoTransicion.REGISTRAR_DEVOLUCION,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            fecha_operacion=date(2026, 9, 10),
        )

    assert exc_devueltos.value.regla == "RN-17"
    assert exc_devueltos.value.detalles["contexto_requerido"] == "equipos_devueltos"


# --------------------------------------------------- Disponibilidad derivada


RESERVA_INICIO = date(2026, 9, 14)
RESERVA_TERMINO = date(2026, 9, 18)


def reserva_ajena(
    *,
    estado: EstadoPrestamo = EstadoPrestamo.APROBADA,
    id_prestamo: str = "P-RESERVA",
) -> Prestamo:
    """Una reserva aprobada de otra persona sobre EQ-01, del 14 al 18."""
    return prestamo(
        id_prestamo=id_prestamo,
        id_solicitante="sol-2",
        estado=estado,
        fecha_inicio=RESERVA_INICIO,
        fecha_termino=RESERVA_TERMINO,
        fecha_aprobacion=HOY,
    )


@pytest.mark.parametrize(
    "inicio, termino, permitida",
    [
        # Termina el viernes anterior al lunes en que empieza la reserva.
        (date(2026, 9, 8), date(2026, 9, 11), True),
        # Termina *el mismo dia* en que empieza: hay_solapamiento es inclusivo.
        (date(2026, 9, 8), date(2026, 9, 14), False),
        # Empieza el lunes siguiente al viernes en que termina la reserva.
        (date(2026, 9, 21), date(2026, 9, 25), True),
    ],
)
def test_una_reserva_solo_bloquea_su_propia_ventana(
    inicio: date, termino: date, permitida: bool
) -> None:
    """El borde completo del solapamiento, que es toda la regla.

    Un equipo RESERVADO sigue siendo solicitable para cualquier ventana que no
    solape. Si alguien vuelve a apretar el escalar de RN-05 a "solo
    DISPONIBLE", los dos casos permitidos fallan de inmediato.

    La regla citada al rechazar depende del momento: al crear se cita RN-05
    ("solo equipos disponibles pueden ser solicitados") y al aprobar RN-10
    ("no se puede aprobar si existe solapamiento"), tal como las describe
    docs/reglas-negocio.md. La comprobacion es la misma en ambos casos.
    """
    solicitud = prestamo(fecha_inicio=inicio, fecha_termino=termino)
    equipos = [equipo(estado=EstadoEquipo.RESERVADO)]
    existentes = [reserva_ajena()]

    def crear() -> None:
        validar_transicion(
            solicitud,
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            equipos=equipos,
            prestamos_existentes=existentes,
        )

    def aprobar() -> None:
        validar_transicion(
            solicitud,
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("enc-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            equipos=equipos,
            prestamos_existentes=existentes,
            solicitante=usuario(),
        )

    if permitida:
        crear()
        aprobar()
        return

    with pytest.raises(ErrorValidacion) as exc_crear:
        crear()
    assert exc_crear.value.regla == "RN-05"

    with pytest.raises(ErrorValidacion) as exc_aprobar:
        aprobar()
    assert exc_aprobar.value.regla == "RN-10"


def test_equipo_prestado_admite_una_reserva_futura_sin_solapamiento() -> None:
    """Lo mismo que RESERVADO, para el equipo que hoy esta en manos de alguien.

    Un prestamo entregado que termina el 18 no puede impedir una reserva para
    el 21: el escalar PRESTADO describe hoy, no las proximas tres semanas.
    """
    validar_transicion(
        prestamo(fecha_inicio=date(2026, 9, 21), fecha_termino=date(2026, 9, 25)),
        EventoTransicion.CREAR_SOLICITUD,
        usuario(),
        fecha_actual=HOY,
        equipos=[equipo(estado=EstadoEquipo.PRESTADO)],
        prestamos_existentes=[
            reserva_ajena(estado=EstadoPrestamo.ENTREGADA),
        ],
    )


@pytest.mark.parametrize(
    "estado", [EstadoEquipo.MANTENCION, EstadoEquipo.BAJA]
)
def test_mantencion_y_baja_siguen_bloqueando_por_si_solas_con_rn05(
    estado: EstadoEquipo,
) -> None:
    """Los dos unicos estados que quedan como compuerta escalar."""
    with pytest.raises(ErrorValidacion) as exc:
        validar_transicion(
            prestamo(),
            EventoTransicion.CREAR_SOLICITUD,
            usuario(),
            fecha_actual=HOY,
            equipos=[equipo(estado=estado)],
            prestamos_existentes=[],
        )

    assert exc.value.regla == "RN-05"
    assert exc.value.detalles["estado"] == estado.value


def test_estado_por_compromiso_conserva_los_estados_administrativos() -> None:
    """Una reserva no puede reactivar un equipo dado de baja o en mantencion."""
    for estado in (EstadoEquipo.MANTENCION, EstadoEquipo.BAJA):
        derivado = reglas.estado_por_compromiso(
            equipo(estado=estado),
            [reserva_ajena()],
            fecha_actual=HOY,
        )
        assert derivado is estado


def test_estado_por_compromiso_la_custodia_manda_sobre_la_reserva() -> None:
    """ENTREGADA/ATRASADA pesan mas que cualquier reserva futura."""
    entregado = prestamo(
        id_prestamo="P-ENTREGADO",
        estado=EstadoPrestamo.ENTREGADA,
        fecha_entrega=date(2026, 9, 8),
    )

    assert (
        reglas.estado_por_compromiso(
            equipo(), [entregado, reserva_ajena()], fecha_actual=HOY
        )
        is EstadoEquipo.PRESTADO
    )
    assert (
        reglas.estado_por_compromiso(equipo(), [reserva_ajena()], fecha_actual=HOY)
        is EstadoEquipo.RESERVADO
    )
    assert (
        reglas.estado_por_compromiso(equipo(), [], fecha_actual=HOY)
        is EstadoEquipo.DISPONIBLE
    )


def test_estado_por_compromiso_ignora_las_reservas_vencidas() -> None:
    """No hay transicion de expiracion: sin esto el equipo queda RESERVADO para siempre."""
    vencida = reserva_ajena()
    despues = RESERVA_TERMINO + timedelta(days=1)

    assert (
        reglas.estado_por_compromiso(equipo(), [vencida], fecha_actual=RESERVA_TERMINO)
        is EstadoEquipo.RESERVADO
    )
    assert (
        reglas.estado_por_compromiso(equipo(), [vencida], fecha_actual=despues)
        is EstadoEquipo.DISPONIBLE
    )


def test_estado_por_compromiso_prefiere_el_prestamo_actual_al_persistido() -> None:
    """El llamador pasa lo que acaba de decidir, no lo que hay en disco.

    Asi el resultado no depende de si la escritura ya aterrizo (ver el orden
    resolver-antes-de-escribir en los servicios).
    """
    persistido = reserva_ajena()
    cancelado = replace(
        persistido,
        estado=EstadoPrestamo.CANCELADA,
        motivo_cancelacion="Cambio de plan",
    )

    assert (
        reglas.estado_por_compromiso(
            equipo(),
            [persistido],
            prestamo_actual=cancelado,
            fecha_actual=HOY,
        )
        is EstadoEquipo.DISPONIBLE
    )

    nuevo = reserva_ajena(id_prestamo="P-NUEVO")
    assert (
        reglas.estado_por_compromiso(
            equipo(), [], prestamo_actual=nuevo, fecha_actual=HOY
        )
        is EstadoEquipo.RESERVADO
    )


def test_estado_por_compromiso_compara_codigos_sin_distinguir_mayusculas() -> None:
    """Mismo criterio que RN-04 y que equipos._exigir_sin_prestamo_activo."""
    reserva = replace(reserva_ajena(), equipos=(" eq-01 ",))

    assert (
        reglas.estado_por_compromiso(equipo("EQ-01"), [reserva], fecha_actual=HOY)
        is EstadoEquipo.RESERVADO
    )


def test_nadie_aprueba_su_propia_solicitud_con_rn22() -> None:
    """RN-22.

    Con roles estaticos el caso es inalcanzable -T-01 exige SOLICITANTE y T-02
    ENCARGADO, y un Usuario tiene un solo rol-, pero `editar_usuario` puede
    promover a un solicitante y dejarlo aprobando lo que el mismo pidio.
    """
    promovido = usuario("sol-1", Rol.ENCARGADO)
    solicitud = prestamo(estado=EstadoPrestamo.SOLICITADA, id_solicitante="sol-1")

    with pytest.raises(ErrorAutorizacion) as exc:
        validar_transicion(
            solicitud,
            EventoTransicion.APROBAR_SOLICITUD,
            promovido,
            fecha_actual=HOY,
            equipos=[equipo()],
            prestamos_existentes=[],
            solicitante=usuario("sol-1"),
        )

    assert exc.value.regla == "RN-22"
    assert exc.value.detalles["usuario"] == "sol-1"
    assert exc.value.detalles["id_solicitante"] == "sol-1"


def test_otro_encargado_si_puede_aprobar_la_solicitud() -> None:
    """RN-22 no debe estorbar el camino normal."""
    validar_transicion(
        prestamo(estado=EstadoPrestamo.SOLICITADA, id_solicitante="sol-1"),
        EventoTransicion.APROBAR_SOLICITUD,
        usuario("enc-1", Rol.ENCARGADO),
        fecha_actual=HOY,
        equipos=[equipo()],
        prestamos_existentes=[],
        solicitante=usuario("sol-1"),
    )


def test_rechazar_la_propia_solicitud_sigue_permitido() -> None:
    """RN-22 cubre solo la aprobacion.

    Rechazar lo propio equivale a cancelarlo, cosa que RN-15 ya permite al
    solicitante: no hay nada que proteger.
    """
    validar_transicion(
        prestamo(estado=EstadoPrestamo.SOLICITADA, id_solicitante="sol-1"),
        EventoTransicion.RECHAZAR_SOLICITUD,
        usuario("sol-1", Rol.ENCARGADO),
        fecha_actual=HOY,
        motivo_rechazo="Ya no lo necesito",
    )


def test_rn22_ignora_espacios_alrededor_del_identificador() -> None:
    """Mismo criterio que la correccion de RN-21: se recortan espacios, no mayusculas."""
    solicitud = prestamo(estado=EstadoPrestamo.SOLICITADA, id_solicitante="sol-1 ")

    with pytest.raises(ErrorAutorizacion) as exc:
        validar_transicion(
            solicitud,
            EventoTransicion.APROBAR_SOLICITUD,
            usuario("sol-1", Rol.ENCARGADO),
            fecha_actual=HOY,
            equipos=[equipo()],
            prestamos_existentes=[],
            solicitante=usuario("sol-1"),
        )

    assert exc.value.regla == "RN-22"
