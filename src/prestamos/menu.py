"""Menu interactivo para la demostracion en vivo.

Capa delgada sobre los mismos servicios que usa cli.py. No decide reglas de
negocio: convierte texto ingresado por la persona en llamadas a servicios y
muestra sus resultados o errores de dominio.
"""

from __future__ import annotations

import getpass
from datetime import date
from typing import Callable, Protocol

from prestamos.errores import ErrorDominio
from prestamos.modelos import Equipo, Prestamo

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class AplicacionMenu(Protocol):
    """Parte de la aplicacion compuesta que necesita el menu."""

    auth: object
    usuarios: object
    equipos: object
    solicitudes: object
    prestamos: object


def ejecutar_menu(
    app: AplicacionMenu,
    *,
    input_fn: InputFn = input,
    password_input_fn: InputFn | None = None,
    output_fn: OutputFn = print,
) -> int:
    """Ejecuta el menu interactivo hasta que la persona salga.

    Las entradas invalidas se informan y el bucle continua. Si stdin se cierra
    durante una ejecucion no interactiva, se sale con codigo 0: alcanzar EOF en
    el menu equivale a elegir salir, no a un traceback. Ctrl+C tambien equivale
    a salir limpiamente.
    """

    if password_input_fn is None:
        password_input_fn = getpass.getpass

    output_fn("Sistema de prestamo de equipos")
    try:
        while True:
            _mostrar_menu(output_fn)
            try:
                opcion = _pedir(input_fn, "Seleccione una opcion: ")
            except EOFError:
                output_fn("Saliendo.")
                return 0

            if opcion == "0":
                output_fn("Saliendo.")
                return 0
            try:
                _ejecutar_opcion(
                    app,
                    opcion,
                    input_fn=input_fn,
                    password_input_fn=password_input_fn,
                    output_fn=output_fn,
                )
            except EOFError:
                output_fn("Saliendo.")
                return 0
            except ErrorDominio as exc:
                output_fn(f"Error: {exc.mensaje}")
            except ValueError as exc:
                output_fn(f"Error: {exc}")
    except KeyboardInterrupt:
        output_fn("Saliendo.")
        return 0


def _mostrar_menu(output_fn: OutputFn) -> None:
    output_fn("")
    output_fn("1. Iniciar sesion")
    output_fn("2. Cerrar sesion")
    output_fn("3. Listar equipos")
    output_fn("4. Crear solicitud")
    output_fn("5. Aprobar solicitud")
    output_fn("6. Rechazar solicitud")
    output_fn("7. Registrar entrega")
    output_fn("8. Registrar devolucion")
    output_fn("9. Cancelar solicitud/prestamo")
    output_fn("10. Consultar prestamos")
    output_fn("0. Salir")


def _pedir(input_fn: InputFn, mensaje: str) -> str:
    return input_fn(mensaje).strip()


def _ejecutar_opcion(
    app: AplicacionMenu,
    opcion: str,
    *,
    input_fn: InputFn,
    password_input_fn: InputFn,
    output_fn: OutputFn,
) -> None:
    if opcion == "1":
        identificador = _pedir(input_fn, "Usuario o correo: ")
        contrasena = _pedir(password_input_fn, "Contrasena: ")
        sesion = app.auth.iniciar_sesion(identificador, contrasena)
        output_fn(f"Sesion iniciada: {sesion.usuario.id} ({sesion.usuario.rol.value})")
        return

    if opcion == "2":
        app.auth.cerrar_sesion()
        output_fn("Sesion cerrada.")
        return

    if opcion == "3":
        equipos = app.equipos.listar(incluir_dados_de_baja=True)
        _mostrar_equipos(equipos, output_fn)
        return

    if opcion == "4":
        codigos = _pedir(input_fn, "Codigos de equipos separados por coma: ")
        motivo = _pedir(input_fn, "Motivo: ")
        fecha_inicio = _pedir_fecha(input_fn, "Fecha inicio (AAAA-MM-DD): ")
        fecha_termino = _pedir_fecha(input_fn, "Fecha termino (AAAA-MM-DD): ")
        solicitud = app.solicitudes.crear_solicitud(
            _lista_csv(codigos), motivo, fecha_inicio, fecha_termino
        )
        output_fn(f"Solicitud creada: {solicitud.id}")
        return

    if opcion == "5":
        id_solicitud = _pedir(input_fn, "ID solicitud: ")
        aprobada = app.solicitudes.aprobar(id_solicitud)
        output_fn(f"Solicitud aprobada: {aprobada.id}")
        return

    if opcion == "6":
        id_solicitud = _pedir(input_fn, "ID solicitud: ")
        motivo = _pedir(input_fn, "Motivo de rechazo: ")
        rechazada = app.solicitudes.rechazar(id_solicitud, motivo)
        output_fn(f"Solicitud rechazada: {rechazada.id}")
        return

    if opcion == "7":
        id_prestamo = _pedir(input_fn, "ID prestamo/solicitud: ")
        usuario = app.auth.requiere_sesion()
        entregado = app.prestamos.registrar_entrega(id_prestamo, usuario)
        output_fn(f"Entrega registrada: {entregado.id}")
        return

    if opcion == "8":
        id_prestamo = _pedir(input_fn, "ID prestamo/solicitud: ")
        usuario = app.auth.requiere_sesion()
        devuelto = app.prestamos.registrar_devolucion(id_prestamo, usuario)
        output_fn(f"Devolucion registrada: {devuelto.id}")
        return

    if opcion == "9":
        id_prestamo = _pedir(input_fn, "ID prestamo/solicitud: ")
        motivo = _pedir(input_fn, "Motivo de cancelacion: ")
        usuario = app.auth.requiere_sesion()
        cancelado = app.prestamos.cancelar(id_prestamo, usuario, motivo)
        output_fn(f"Cancelacion registrada: {cancelado.id}")
        return

    if opcion == "10":
        tipo = _pedir(input_fn, "Tipo (futuros/vigentes/atrasados): ").casefold()
        id_usuario = _pedir_opcional(input_fn, "Filtro usuario (opcional): ")
        codigo_equipo = _pedir_opcional(input_fn, "Filtro equipo (opcional): ")
        fecha_actual = _pedir_fecha_opcional(input_fn, "Fecha actual opcional (AAAA-MM-DD): ")
        usuario = app.auth.requiere_sesion()
        if tipo == "futuros":
            prestamos = app.prestamos.prestamos_futuros(
                usuario,
                fecha_actual=fecha_actual,
                id_usuario=id_usuario,
                codigo_equipo=codigo_equipo,
            )
        elif tipo == "vigentes":
            prestamos = app.prestamos.prestamos_vigentes(
                usuario,
                fecha_actual=fecha_actual,
                id_usuario=id_usuario,
                codigo_equipo=codigo_equipo,
            )
        elif tipo == "atrasados":
            prestamos = app.prestamos.prestamos_atrasados(
                usuario,
                fecha_actual=fecha_actual,
                id_usuario=id_usuario,
                codigo_equipo=codigo_equipo,
            )
        else:
            raise ValueError("Tipo de consulta invalido: use futuros, vigentes o atrasados.")
        _mostrar_prestamos(prestamos, output_fn)
        return

    raise ValueError("Opcion invalida: ingrese un numero disponible del menu.")


def _pedir_opcional(input_fn: InputFn, mensaje: str) -> str | None:
    valor = _pedir(input_fn, mensaje)
    return valor or None


def _pedir_fecha(input_fn: InputFn, mensaje: str) -> date:
    return _parsear_fecha(_pedir(input_fn, mensaje))


def _pedir_fecha_opcional(input_fn: InputFn, mensaje: str) -> date | None:
    valor = _pedir(input_fn, mensaje)
    return _parsear_fecha(valor) if valor else None


def _parsear_fecha(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise ValueError("Fecha invalida: use el formato AAAA-MM-DD.") from exc


def _lista_csv(valor: str) -> tuple[str, ...]:
    return tuple(parte.strip() for parte in valor.split(",") if parte.strip())


def _mostrar_equipos(equipos: list[Equipo], output_fn: OutputFn) -> None:
    if not equipos:
        output_fn("Sin equipos registrados.")
        return
    for equipo in equipos:
        output_fn(f"{equipo.codigo} | {equipo.estado.value} | {equipo.nombre}")


def _mostrar_prestamos(prestamos: list[Prestamo], output_fn: OutputFn) -> None:
    if not prestamos:
        output_fn("Sin prestamos para mostrar.")
        return
    for prestamo in prestamos:
        equipos = ",".join(prestamo.equipos)
        output_fn(
            f"{prestamo.id} | {prestamo.estado.value} | {prestamo.id_solicitante} | "
            f"{equipos} | {prestamo.fecha_inicio.isoformat()} -> "
            f"{prestamo.fecha_termino.isoformat()}"
        )
