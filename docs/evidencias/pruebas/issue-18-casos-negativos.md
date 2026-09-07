# Evidencia issue #18 - CP-10 a CP-12 negativos

Ejecutado por: nonmeeeeeeeeeeeeeee (B. Olguin)  
Fecha: 2026-09-06  
Rama: test/casos-negativos

## Comando ejecutado: `.venv/Scripts/pytest.exe tests/negativos/test_negativos.py -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Dev\sistema-prestamo-equipos\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Dev\sistema-prestamo-equipos
configfile: pyproject.toml
collecting ... collected 3 items

tests/negativos/test_negativos.py::test_CP10_RF10_devolver_prestamo_aprobado_nunca_entregado_rechaza_por_rn14 PASSED [ 33%]
tests/negativos/test_negativos.py::test_CP11_RF08_solicitante_no_puede_aprobar_solicitud_por_rn11 PASSED [ 66%]
tests/negativos/test_negativos.py::test_CP12_RF05_fecha_termino_anterior_al_inicio_rechaza_por_rn17 PASSED [100%]

============================== 3 passed in 0.07s ==============================
```

## Comando ejecutado: `.venv/Scripts/pytest.exe -m negativo -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Dev\sistema-prestamo-equipos\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Dev\sistema-prestamo-equipos
configfile: pyproject.toml
testpaths: tests
collecting ... collected 266 items / 263 deselected / 3 selected

tests/negativos/test_negativos.py::test_CP10_RF10_devolver_prestamo_aprobado_nunca_entregado_rechaza_por_rn14 PASSED [ 33%]
tests/negativos/test_negativos.py::test_CP11_RF08_solicitante_no_puede_aprobar_solicitud_por_rn11 PASSED [ 66%]
tests/negativos/test_negativos.py::test_CP12_RF05_fecha_termino_anterior_al_inicio_rechaza_por_rn17 PASSED [100%]

====================== 3 passed, 263 deselected in 0.14s ======================
```

## Comando ejecutado: `.venv/Scripts/pytest.exe`

```text
collected 266 items

============================= 266 passed in 8.58s =============================
```

## Comando ejecutado: `git diff --check`

```text
Sin salida; exit code 0.
```

## Decisiones de diseno de los casos

Registradas aqui porque condicionan que afirma cada CP y por que no coincide
con el idiom de `tests/borde/test_borde.py`.

### Los tres casos entran por la operacion real, no por el motor

`tests/unidad/test_reglas.py` ya cubre RN-11 y las transiciones prohibidas
llamando `validar_transicion` directamente. Repetirlo aqui no habria agregado
nada, y las filas del documento de casos de prueba habrian tenido que describir
como paso "invocar una funcion interna del motor". Entrando por el servicio,
cada caso puede afirmar ademas que **no se persistio nada**, que es la forma
literal de RN-17.

### El mensaje se afirma por igualdad, no por subcadena

`test_borde.py` usa `assert "RN-10" in exc.mensaje`. Ese idiom no es aplicable:

| Asercion | Mensaje | Nombra su regla |
| --- | --- | --- |
| CP-10 | `La transicion REGISTRAR_DEVOLUCION no esta permitida desde APROBADA (RN-14).` | si |
| CP-11 (auth) | `No tiene permisos para realizar esta operacion.` | no |
| CP-11 (motor) | `El rol SOLICITANTE no esta autorizado para APROBAR_SOLICITUD (RN-11).` | si |
| CP-12 | `La fecha de inicio no puede ser posterior a la fecha de termino.` | no |

En CP-11 y CP-12 la regla solo vive en el atributo `.regla`. Se afirma entonces
la terna completa `codigo` + `regla` + `mensaje` textual, mas los `detalles`
que `ErrorDominio.para_log()` manda a los logs y a Sentry y que hasta ahora
ninguna prueba verificaba. La fragilidad ante un cambio de redaccion es
deseada: `errores.py` establece que la CLI muestra solo `mensaje`, asi que ese
texto es interfaz de usuario.

### CP-10 devuelve desde `APROBADA`, no desde `SOLICITADA`

Ningun test de la suite intentaba una devolucion desde un estado distinto de
`ENTREGADA` o `ATRASADA`, asi que el caso cubre un hueco real. Se eligio
`APROBADA` porque es el unico estado donde la asercion de no-efecto no es
trivial: el equipo esta `RESERVADO` y una devolucion indebida liberaria una
reserva viva. Con `SOLICITADA` el equipo ya estaria `DISPONIBLE` y la asercion
no probaria nada.

La fecha de devolucion es posterior a la de termino a proposito: el caso
comprueba de paso que `ServicioPrestamos._preparar_atraso_si_corresponde` no
promueve un `APROBADA` a `ATRASADA`. Nunca hubo custodia fisica, asi que no hay
atraso que marcar.

### CP-11 afirma dos capas

`ServicioSolicitudes.aprobar` llama `auth.requiere_rol(Rol.ENCARGADO)` en su
primera linea, **antes** de leer la solicitud del repositorio. Consecuencias:

1. El mensaje alcanzable por el servicio es el generico de `auth`, no el
   especifico de `reglas._validar_usuario_operador`, que queda inalcanzable por
   esa via.
2. La excepcion se levantaria aunque la solicitud no existiera. Por eso el caso
   siembra una solicitud `SOLICITADA` real: sin ella, las aserciones de
   no-efecto serian vacias.

La segunda asercion invoca el motor directamente para dejar constancia de que
la guarda de dominio existe, es redundante respecto de la de `auth`, y produce
el mensaje especifico con rol y transicion.

### CP-12 entra por el servicio y ancla la invariante en el modelo

La invariante vive en `Prestamo.__post_init__`, pero llega por la puerta del
usuario: `crear_solicitud` recibe `fecha_inicio` y `fecha_termino` sueltas y
construye la entidad adentro. El caso afirma que no quedo nada en el JSON y que
el correlativo no se consumio -la primera solicitud valida posterior sigue
siendo `S-0001`- y recien despues repite la construccion directa del modelo,
que hasta ahora ninguna prueba ejercitaba: no existe `tests/unidad/test_modelos.py`.

## Observaciones para el registro de defectos

Detectadas al escribir estos casos; no se corrigieron en esta rama porque no
son parte del DoD del issue #18.

1. **Comentario desactualizado en `src/prestamos/servicios/solicitudes.py`.** El
   docstring del constructor justifica inyectar `logger` diciendo que
   `datos/logs/eventos.log` "esta versionado". No lo esta: `.gitignore` lo
   excluye con `*.log` y `logs/`. La inyeccion sigue siendo correcta por otra
   razon -evitar que la suite escriba en el log local de ejecucion-, pero el
   motivo declarado es falso.
2. **Numeracion de casos divergente entre documentos.** `docs/casos-de-prueba.md`
   numera CP-01 a CP-15, mientras `docs/reglas-negocio.md` y
   `docs/estados-transiciones.md` referencian CP-07 a CP-32 con otro criterio.
   Las columnas "Casos de prueba" de esos dos documentos no son navegables
   contra la tabla de casos.
