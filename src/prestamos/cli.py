"""Capa de linea de comandos.

Esta capa solo traduce argumentos a llamadas de los servicios; no contiene
reglas de negocio (eso vive en prestamos.reglas y prestamos.servicios).
"""

from __future__ import annotations

import argparse
import getpass
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from prestamos import __version__
from prestamos.demo import inicializar_datos_demo
from prestamos.auth import ServicioAuth
from prestamos.errores import ErrorAutenticacion, ErrorDominio
from prestamos.logging_conf import configurar_logging, registrar_evento
from prestamos.menu import ejecutar_menu
from prestamos.modelos import Equipo, Prestamo, Rol, Usuario
from prestamos.observabilidad import (
    cargar_env,
    capturar_excepcion,
    capturar_mensaje,
    inicializar_sentry,
)
from prestamos.repositorios.fabricas import (
    repositorio_equipos,
    repositorio_prestamos,
    repositorio_usuarios,
)
from prestamos.servicios.equipos import ServicioEquipos
from prestamos.servicios.prestamos import ServicioPrestamos
from prestamos.servicios.solicitudes import ServicioSolicitudes
from prestamos.servicios.usuarios import ServicioUsuarios


@dataclass(frozen=True)
class Aplicacion:
    """Servicios compuestos para una ejecucion de CLI o menu."""

    auth: ServicioAuth
    usuarios: ServicioUsuarios
    equipos: ServicioEquipos
    solicitudes: ServicioSolicitudes
    prestamos: ServicioPrestamos


def crear_aplicacion(*, datos_dir: str | Path | None = None) -> Aplicacion:
    """Crea todos los servicios compartiendo repositorios y un solo ServicioAuth."""

    repo_usuarios = repositorio_usuarios(datos_dir)
    repo_equipos = repositorio_equipos(datos_dir)
    repo_prestamos = repositorio_prestamos(datos_dir)
    auth = ServicioAuth(repo_usuarios)
    return Aplicacion(
        auth=auth,
        usuarios=ServicioUsuarios(auth, repo_usuarios, datos_dir=datos_dir),
        equipos=ServicioEquipos(
            auth,
            repo_equipos,
            repo_prestamos,
            datos_dir=datos_dir,
        ),
        solicitudes=ServicioSolicitudes(
            auth,
            repo_prestamos,
            repo_equipos,
            repo_usuarios,
            datos_dir=datos_dir,
        ),
        prestamos=ServicioPrestamos(repo_prestamos, repo_equipos, datos_dir=datos_dir),
    )


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prestamos",
        description="Sistema de prestamo de equipos de laboratorio",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--datos-dir",
        help="directorio con usuarios.json, equipos.json y solicitudes.json",
    )
    parser.add_argument("--usuario", help="id o correo para autenticar esta ejecucion")
    parser.add_argument(
        "--contrasena",
        help="contrasena opcional; si se omite en subcomandos se pedira sin eco",
    )

    subparsers = parser.add_subparsers(dest="comando")
    subparsers.add_parser(
        "probar-sentry",
        help="envia un evento de prueba a Sentry si SENTRY_DSN esta configurado",
    ).set_defaults(func=_cmd_probar_sentry)

    init_demo = subparsers.add_parser(
        "init-demo",
        help="crea datos de demostracion en datos/demo o en --datos-dir",
    )
    init_demo.add_argument(
        "--force",
        action="store_true",
        help="regenera los datos demo sobrescribiendo usuarios/equipos/solicitudes",
    )
    init_demo.set_defaults(func=_cmd_init_demo)

    _agregar_comandos_usuarios(subparsers)
    _agregar_comandos_equipos(subparsers)
    _agregar_comandos_solicitudes(subparsers)
    _agregar_comandos_prestamos(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        cargar_env()
        configurar_logging()
        inicializar_sentry()

        args = construir_parser().parse_args(argv)
        if args.comando is None and (args.usuario or args.contrasena):
            raise ErrorAutenticacion(
                "No indique --usuario ni --contrasena al abrir el menu interactivo.",
                detalles={"motivo": "credenciales_cli_no_permitidas_en_menu"},
            )

        app = crear_aplicacion(datos_dir=args.datos_dir)
        if args.comando is None:
            registrar_evento("cli_menu_inicio", resultado="ok")
            return ejecutar_menu(app)

        if getattr(args, "requiere_auth", False):
            _abrir_sesion_cli(app.auth, args)
        resultado = args.func(args, app)
        return 0 if resultado is None else resultado
    except ErrorDominio as exc:
        _reportar_error(exc)
        print(f"Error: {exc.mensaje}")
        return 1
    except Exception as exc:
        _reportar_error(exc)
        print("Error: No se pudo completar la operacion.")
        return 1


def _agregar_comandos_usuarios(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("usuarios", help="gestiona usuarios autorizados")
    acciones = parser.add_subparsers(dest="accion", required=True)

    listar = acciones.add_parser("listar", help="lista usuarios")
    listar.add_argument("--solo-activos", action="store_true")
    listar.set_defaults(func=_cmd_usuarios_listar, requiere_auth=True)

    registrar = acciones.add_parser("registrar", help="registra un usuario")
    registrar.add_argument("--id", required=True, dest="id_usuario")
    registrar.add_argument("--nombre", required=True)
    registrar.add_argument("--correo", required=True)
    registrar.add_argument("--rol", required=True, type=_rol)
    registrar.add_argument("--nueva-contrasena", required=True)
    registrar.set_defaults(func=_cmd_usuarios_registrar, requiere_auth=True)

    editar = acciones.add_parser("editar", help="edita nombre, correo o rol")
    editar.add_argument("id_usuario")
    editar.add_argument("--nombre")
    editar.add_argument("--correo")
    editar.add_argument("--rol", type=_rol)
    editar.set_defaults(func=_cmd_usuarios_editar, requiere_auth=True)

    desactivar = acciones.add_parser("desactivar", help="desactiva un usuario")
    desactivar.add_argument("id_usuario")
    desactivar.set_defaults(func=_cmd_usuarios_desactivar, requiere_auth=True)

    reactivar = acciones.add_parser("reactivar", help="reactiva un usuario")
    reactivar.add_argument("id_usuario")
    reactivar.set_defaults(func=_cmd_usuarios_reactivar, requiere_auth=True)

    cambiar = acciones.add_parser("cambiar-contrasena", help="cambia una contrasena")
    cambiar.add_argument("id_usuario")
    cambiar.add_argument("--nueva-contrasena", required=True)
    cambiar.set_defaults(func=_cmd_usuarios_cambiar_contrasena, requiere_auth=True)


def _agregar_comandos_equipos(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("equipos", help="gestiona el catalogo de equipos")
    acciones = parser.add_subparsers(dest="accion", required=True)

    listar = acciones.add_parser("listar", help="lista equipos")
    listar.add_argument("--sin-bajas", action="store_true")
    listar.set_defaults(func=_cmd_equipos_listar, requiere_auth=True)

    registrar = acciones.add_parser("registrar", help="registra un equipo")
    registrar.add_argument("--codigo", required=True)
    registrar.add_argument("--nombre", required=True)
    registrar.add_argument("--tipo", required=True)
    registrar.add_argument("--descripcion", required=True)
    registrar.set_defaults(func=_cmd_equipos_registrar, requiere_auth=True)

    editar = acciones.add_parser("editar", help="edita datos descriptivos de un equipo")
    editar.add_argument("codigo")
    editar.add_argument("--nombre")
    editar.add_argument("--tipo")
    editar.add_argument("--descripcion")
    editar.set_defaults(func=_cmd_equipos_editar, requiere_auth=True)

    baja = acciones.add_parser("baja", help="da de baja un equipo")
    baja.add_argument("codigo")
    baja.set_defaults(func=_cmd_equipos_baja, requiere_auth=True)

    mantencion = acciones.add_parser("mantencion", help="envia un equipo a mantencion")
    mantencion.add_argument("codigo")
    mantencion.set_defaults(func=_cmd_equipos_mantencion, requiere_auth=True)

    reactivar = acciones.add_parser("reactivar", help="reactiva un equipo")
    reactivar.add_argument("codigo")
    reactivar.set_defaults(func=_cmd_equipos_reactivar, requiere_auth=True)


def _agregar_comandos_solicitudes(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("solicitudes", help="crea, aprueba y rechaza solicitudes")
    acciones = parser.add_subparsers(dest="accion", required=True)

    crear = acciones.add_parser("crear", help="crea una solicitud")
    crear.add_argument("--equipos", nargs="+", required=True)
    crear.add_argument("--motivo", required=True)
    crear.add_argument("--fecha-inicio", required=True, type=_fecha)
    crear.add_argument("--fecha-termino", required=True, type=_fecha)
    crear.set_defaults(func=_cmd_solicitudes_crear, requiere_auth=True)

    aprobar = acciones.add_parser("aprobar", help="aprueba una solicitud")
    aprobar.add_argument("id_solicitud")
    aprobar.add_argument("--fecha", type=_fecha)
    aprobar.set_defaults(func=_cmd_solicitudes_aprobar, requiere_auth=True)

    rechazar = acciones.add_parser("rechazar", help="rechaza una solicitud")
    rechazar.add_argument("id_solicitud")
    rechazar.add_argument("--motivo", required=True)
    rechazar.set_defaults(func=_cmd_solicitudes_rechazar, requiere_auth=True)


def _agregar_comandos_prestamos(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("prestamos", help="opera y consulta prestamos")
    acciones = parser.add_subparsers(dest="accion", required=True)

    entregar = acciones.add_parser("entregar", help="registra una entrega")
    entregar.add_argument("id_prestamo")
    entregar.add_argument("--fecha", type=_fecha)
    entregar.set_defaults(func=_cmd_prestamos_entregar, requiere_auth=True)

    devolver = acciones.add_parser("devolver", help="registra una devolucion")
    devolver.add_argument("id_prestamo")
    devolver.add_argument("--fecha", type=_fecha)
    devolver.add_argument("--equipos-devueltos", nargs="+")
    devolver.set_defaults(func=_cmd_prestamos_devolver, requiere_auth=True)

    cancelar = acciones.add_parser("cancelar", help="cancela antes de la entrega")
    cancelar.add_argument("id_prestamo")
    cancelar.add_argument("--motivo", required=True)
    cancelar.set_defaults(func=_cmd_prestamos_cancelar, requiere_auth=True)

    atraso = acciones.add_parser("marcar-atraso", help="marca atraso de un prestamo")
    atraso.add_argument("id_prestamo")
    atraso.add_argument("--fecha", type=_fecha)
    atraso.set_defaults(func=_cmd_prestamos_marcar_atraso, requiere_auth=True)

    for nombre, funcion in (
        ("futuros", _cmd_prestamos_futuros),
        ("vigentes", _cmd_prestamos_vigentes),
        ("atrasados", _cmd_prestamos_atrasados),
    ):
        consulta = acciones.add_parser(nombre, help=f"consulta prestamos {nombre}")
        consulta.add_argument("--fecha", type=_fecha)
        consulta.add_argument("--id-usuario")
        consulta.add_argument("--codigo-equipo")
        consulta.set_defaults(func=funcion, requiere_auth=True)


def _cmd_init_demo(args: argparse.Namespace, app: Aplicacion) -> int:
    del app
    resultado = inicializar_datos_demo(args.datos_dir, sobrescribir=args.force)
    print(resultado.mensaje)
    return 0


def _cmd_probar_sentry(args: argparse.Namespace, app: Aplicacion) -> int:
    del args, app
    enviado = capturar_mensaje(
        "Evento de prueba desde sistema-prestamo-equipos",
        usuario="revisor",
        contexto={"origen": "cli"},
    )
    if enviado:
        print("Evento de prueba enviado a Sentry.")
        return 0
    print("Sentry no esta configurado. Define SENTRY_DSN en .env.")
    return 1


def _cmd_usuarios_listar(args: argparse.Namespace, app: Aplicacion) -> None:
    _imprimir_usuarios(app.usuarios.listar(incluir_inactivos=not args.solo_activos))


def _cmd_usuarios_registrar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.usuarios.registrar_usuario(
        args.id_usuario,
        args.nombre,
        args.correo,
        args.rol,
        args.nueva_contrasena,
    )
    print(f"Usuario registrado: {usuario.id}")


def _cmd_usuarios_editar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.usuarios.editar_usuario(
        args.id_usuario,
        nombre=args.nombre,
        correo=args.correo,
        rol=args.rol,
    )
    print(f"Usuario editado: {usuario.id}")


def _cmd_usuarios_desactivar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.usuarios.desactivar(args.id_usuario)
    print(f"Usuario desactivado: {usuario.id}")


def _cmd_usuarios_reactivar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.usuarios.reactivar(args.id_usuario)
    print(f"Usuario reactivado: {usuario.id}")


def _cmd_usuarios_cambiar_contrasena(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.usuarios.cambiar_contrasena(args.id_usuario, args.nueva_contrasena)
    print(f"Contrasena actualizada: {usuario.id}")


def _cmd_equipos_listar(args: argparse.Namespace, app: Aplicacion) -> None:
    _imprimir_equipos(app.equipos.listar(incluir_dados_de_baja=not args.sin_bajas))


def _cmd_equipos_registrar(args: argparse.Namespace, app: Aplicacion) -> None:
    equipo = app.equipos.registrar_equipo(
        args.codigo,
        args.nombre,
        args.tipo,
        args.descripcion,
    )
    print(f"Equipo registrado: {equipo.codigo}")


def _cmd_equipos_editar(args: argparse.Namespace, app: Aplicacion) -> None:
    equipo = app.equipos.editar_equipo(
        args.codigo,
        nombre=args.nombre,
        tipo=args.tipo,
        descripcion=args.descripcion,
    )
    print(f"Equipo editado: {equipo.codigo}")


def _cmd_equipos_baja(args: argparse.Namespace, app: Aplicacion) -> None:
    equipo = app.equipos.dar_de_baja(args.codigo)
    print(f"Equipo dado de baja: {equipo.codigo}")


def _cmd_equipos_mantencion(args: argparse.Namespace, app: Aplicacion) -> None:
    equipo = app.equipos.enviar_a_mantencion(args.codigo)
    print(f"Equipo en mantencion: {equipo.codigo}")


def _cmd_equipos_reactivar(args: argparse.Namespace, app: Aplicacion) -> None:
    equipo = app.equipos.reactivar(args.codigo)
    print(f"Equipo reactivado: {equipo.codigo}")


def _cmd_solicitudes_crear(args: argparse.Namespace, app: Aplicacion) -> None:
    solicitud = app.solicitudes.crear_solicitud(
        args.equipos,
        args.motivo,
        args.fecha_inicio,
        args.fecha_termino,
    )
    print(f"Solicitud creada: {solicitud.id}")


def _cmd_solicitudes_aprobar(args: argparse.Namespace, app: Aplicacion) -> None:
    solicitud = app.solicitudes.aprobar(args.id_solicitud, fecha_aprobacion=args.fecha)
    print(f"Solicitud aprobada: {solicitud.id}")


def _cmd_solicitudes_rechazar(args: argparse.Namespace, app: Aplicacion) -> None:
    solicitud = app.solicitudes.rechazar(args.id_solicitud, args.motivo)
    print(f"Solicitud rechazada: {solicitud.id}")


def _cmd_prestamos_entregar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    prestamo = app.prestamos.registrar_entrega(
        args.id_prestamo,
        usuario,
        fecha_entrega=args.fecha,
    )
    print(f"Entrega registrada: {prestamo.id}")


def _cmd_prestamos_devolver(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    prestamo = app.prestamos.registrar_devolucion(
        args.id_prestamo,
        usuario,
        fecha_devolucion=args.fecha,
        equipos_devueltos=args.equipos_devueltos,
    )
    print(f"Devolucion registrada: {prestamo.id}")


def _cmd_prestamos_cancelar(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    prestamo = app.prestamos.cancelar(args.id_prestamo, usuario, args.motivo)
    print(f"Cancelacion registrada: {prestamo.id}")


def _cmd_prestamos_marcar_atraso(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    prestamo = app.prestamos.marcar_atraso(
        args.id_prestamo,
        usuario=usuario,
        fecha_actual=args.fecha,
    )
    print(f"Atraso registrado: {prestamo.id}")


def _cmd_prestamos_futuros(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    _imprimir_prestamos(
        app.prestamos.prestamos_futuros(
            usuario,
            fecha_actual=args.fecha,
            id_usuario=args.id_usuario,
            codigo_equipo=args.codigo_equipo,
        )
    )


def _cmd_prestamos_vigentes(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    _imprimir_prestamos(
        app.prestamos.prestamos_vigentes(
            usuario,
            fecha_actual=args.fecha,
            id_usuario=args.id_usuario,
            codigo_equipo=args.codigo_equipo,
        )
    )


def _cmd_prestamos_atrasados(args: argparse.Namespace, app: Aplicacion) -> None:
    usuario = app.auth.requiere_sesion()
    _imprimir_prestamos(
        app.prestamos.prestamos_atrasados(
            usuario,
            fecha_actual=args.fecha,
            id_usuario=args.id_usuario,
            codigo_equipo=args.codigo_equipo,
        )
    )


def _abrir_sesion_cli(auth: ServicioAuth, args: argparse.Namespace) -> None:
    if not args.usuario:
        raise ErrorAutenticacion(
            "Debe indicar --usuario para ejecutar este comando.",
            detalles={"motivo": "usuario_cli_requerido"},
        )
    contrasena = (
        args.contrasena
        if args.contrasena is not None
        else getpass.getpass("Contrasena: ")
    )
    auth.iniciar_sesion(args.usuario, contrasena)


def _rol(valor: str) -> Rol:
    try:
        return Rol(valor.strip().upper())
    except ValueError as exc:
        validos = ", ".join(rol.value for rol in Rol)
        raise argparse.ArgumentTypeError(f"rol invalido: use {validos}") from exc


def _fecha(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "fecha invalida: use el formato AAAA-MM-DD"
        ) from exc


def _imprimir_usuarios(usuarios: Iterable[Usuario]) -> None:
    filas = list(usuarios)
    if not filas:
        print("Sin usuarios registrados.")
        return
    for usuario in filas:
        estado = "activo" if usuario.activo else "inactivo"
        print(f"{usuario.id} | {usuario.rol.value} | {estado} | {usuario.correo}")


def _imprimir_equipos(equipos: Iterable[Equipo]) -> None:
    filas = list(equipos)
    if not filas:
        print("Sin equipos registrados.")
        return
    for equipo in filas:
        print(f"{equipo.codigo} | {equipo.estado.value} | {equipo.nombre}")


def _imprimir_prestamos(prestamos: Iterable[Prestamo]) -> None:
    filas = list(prestamos)
    if not filas:
        print("Sin prestamos para mostrar.")
        return
    for prestamo in filas:
        equipos = ",".join(prestamo.equipos)
        print(
            f"{prestamo.id} | {prestamo.estado.value} | {prestamo.id_solicitante} | "
            f"{equipos} | {prestamo.fecha_inicio.isoformat()} -> "
            f"{prestamo.fecha_termino.isoformat()}"
        )


def _reportar_error(error: Exception) -> None:
    """Intenta reportar el error sin depender de que observabilidad funcione."""
    try:
        contexto = error.para_log() if isinstance(error, ErrorDominio) else None
        capturar_excepcion(error, contexto=contexto)
    except Exception:
        # No volver a usar logging/Sentry: pueden ser la causa del fallo.
        pass
