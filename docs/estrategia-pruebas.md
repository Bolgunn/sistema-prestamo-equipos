# Estrategia de pruebas

## 1. Objetivos

La estrategia de pruebas busca demostrar que el sistema CLI de prestamo de
equipos cumple los flujos principales definidos para la Tarea 1: autenticacion,
gestion de usuarios y equipos, creacion/aprobacion/rechazo de solicitudes,
entrega, devolucion, cancelacion, consultas, reglas de borde y rechazos por
entradas invalidas.

Tambien busca dejar evidencia reproducible. Por eso los casos CP-01 a CP-15 se
ejecutan con `pytest`, sobre repositorios JSON temporales, y cada resultado queda
vinculado a un archivo de evidencia en `docs/evidencias/pruebas/`.

## 2. Alcance (que se prueba y que no)

Se prueba el comportamiento observable de los servicios y del motor de reglas
que ya existen en el repositorio: persistencia JSON, cambios de estado,
validaciones de dominio, permisos por rol, efectos secundarios sobre equipos y
consultas de prestamos. Los casos funcionales, de borde, negativos, combinados y
el escenario completo cubren el minimo exigido de CP-01 a CP-15.

No se prueba concurrencia entre procesos ni tolerancia a edicion manual
simultanea de los JSON. Tampoco se incluyen pruebas manuales de interfaz de
terminal dentro de CP-01 a CP-15: la CLI tiene cobertura automatizada propia en
`tests/funcionales/`, pero esos tests no se cuentan como parte del minimo CP-01 a
CP-15 para no mezclar numeraciones historicas.

## 3. Responsabilidades

Pruebas cruzadas: cada integrante disena una parte de las pruebas y ejecuta o
revisa casos sobre funcionalidades desarrolladas principalmente por el otro.

| Integrante | Funcionalidades que desarrolla | Casos que disena | Casos que ejecuta (del otro) |
| --- | --- | --- | --- |
| IsaiasACF | Casos funcionales, borde, observabilidad/CLI y datos demo segun issues asignados | CP-01 a CP-09 y pruebas automatizadas asociadas a issues posteriores | Pruebas cruzadas sobre funcionalidades de usuarios/equipos y aprobacion/rechazo |
| Benjamin | Funcionalidades de usuarios/equipos y aprobacion/rechazo segun issues #10 y #11 | CP-10 a CP-15 y casos negativos/combinados/escenario | Revision cruzada de funcionalidades implementadas por IsaiasACF |

## 4. Ambiente de pruebas

Las pruebas se ejecutan con `pytest` sobre Python 3.11 o superior
(`requires-python = ">=3.11"` en `pyproject.toml`), usando el entorno virtual del
proyecto cuando esta disponible. La configuracion de pytest esta en
`pyproject.toml`, con `pythonpath = ["src"]` y `testpaths = ["tests"]`. La suite
es independiente del sistema operativo: la evidencia registrada para #24 se
tomo en Windows con Python 3.14.5, y la cabecera de cada archivo de evidencia
deja constancia del entorno exacto de esa corrida.

Cada prueba usa `tmp_path` o repositorios inyectados para aislar `usuarios.json`,
`equipos.json` y `solicitudes.json`. Los tests no escriben en los datos reales
del proyecto; cuando necesitan logging, usan loggers de prueba o verifican
salidas controladas.

## 5. Datos de prueba

Los datos de los CP automatizados se construyen dentro de cada prueba. Se usan
usuarios concretos como `sol-funcional`, `enc-funcional`, `sol-borde`,
`sol-negativo` y `sol-integracion`; equipos como `EQ-FUNC-01`, `EQ-BORDE-01`,
`EQ-NEG-01` y `EQ-INT-01`; y fechas fijas de septiembre de 2026 para evitar
dependencia del reloj real.

El dataset de demostracion en `datos/demo/` no reemplaza estos datos de prueba:
sirve para reproduccion manual y revision, mientras que CP-01 a CP-15 son
hermeticos y crean su propio estado inicial.

## 6. Criterios de entrada y de salida

Criterios de entrada:

- Los documentos de reglas y transiciones estan disponibles: `docs/reglas-negocio.md` y `docs/estados-transiciones.md`.
- La suite automatizada puede ejecutarse con `pytest` desde la raiz del repositorio.
- Los servicios y repositorios reales importan correctamente desde `src/prestamos/`.
- Cada caso CP tiene precondiciones, pasos, datos concretos y resultado esperado en `docs/casos-de-prueba.md`.

Criterios de salida:

- CP-01 a CP-15 tienen resultado obtenido real, estado y evidencia asociada.
- La suite completa finaliza sin fallos. Se admiten XFAIL siempre que esten
  documentados como defecto en `docs/defectos.md` con su issue asociado.
- La evidencia de ejecucion de `pytest -v` queda guardada en `docs/evidencias/pruebas/`.
- `git diff --check` no reporta errores de whitespace.
- Los defectos detectados, si los hubiera, se documentan en `docs/defectos.md` antes de corregirlos.

## 7. Registro de evidencias

Las evidencias se guardan en `docs/evidencias/pruebas/`. Para CP-01 a CP-15, la
evidencia principal esta repartida por issue:

- CP-01 a CP-05: `issue-16-casos-funcionales.md`.
- CP-06 a CP-09: `issue-17-casos-borde.md`.
- CP-10 a CP-12: `issue-18-casos-negativos.md`.
- CP-13 a CP-15: `issue-19-casos-combinados-escenario.md`.
- Suite completa actual: `issue-24-pytest-v.txt`.

Casos CLI no automatizables: no hay casos CLI manuales incluidos en CP-01 a
CP-15. Si se pidiera evidencia manual adicional de la CLI, faltarian capturas o
transcripciones de terminal para: `python -m prestamos --help`, apertura del menu
interactivo con `python -m prestamos`, manejo de entrada invalida en menu y salida
limpia ante EOF/KeyboardInterrupt. No se adjuntan esas capturas aqui porque no
fueron ejecutadas manualmente en esta rama; la cobertura automatizada de CLI vive
en `tests/funcionales/test_cli_menu.py` y `tests/funcionales/test_cli_errores.py`.

## 8. Resultados

Cierre al 2026-09-06, con CP-15 terminado. Los 15 casos del minimo exigido
estan disenados, ejecutados y en verde; el detalle de cada uno vive en
`docs/casos-de-prueba.md` y su salida literal de pytest en las evidencias.

| Categoria | Minimo exigido | Disenados | Ejecutados | OK | Fallidos |
| --- | --- | --- | --- | --- | --- |
| Funcionales | 5 | 5 | 5 | 5 | 0 |
| Borde | 4 | 4 | 4 | 4 | 0 |
| Negativos / entradas invalidas | 3 | 3 | 3 | 3 | 0 |
| Combinacion de reglas | 2 | 2 | 2 | 2 | 0 |
| Escenario completo | 1 | 1 | 1 | 1 | 0 |
| Total | 15 | 15 | 15 | 15 | 0 |

Resumen de CP-01 a CP-15 con resultado real:

| Caso | Requerimiento | Categoria | Test automatizado | Resultado real | Evidencia |
| --- | --- | --- | --- | --- | --- |
| CP-01 | RF-02 | Funcional | `test_CP01_RF02_login_valido_abre_sesion_sin_exponer_contrasena` | PASSED / Exitoso | `issue-16-casos-funcionales.md` |
| CP-02 | RF-09 | Funcional | `test_CP02_RF09_registrar_entrega_aprobada_persiste_prestamo_y_equipo` | PASSED / Exitoso | `issue-16-casos-funcionales.md` |
| CP-03 | RF-10 | Funcional | `test_CP03_RF10_registrar_devolucion_en_plazo_persiste_prestamo_y_equipo` | PASSED / Exitoso | `issue-16-casos-funcionales.md` |
| CP-04 | RF-11 | Funcional | `test_CP04_RF11_cancelar_aprobada_antes_de_entrega_persiste_y_libera_equipo` | PASSED / Exitoso | `issue-16-casos-funcionales.md` |
| CP-05 | RF-12 | Funcional | `test_CP05_RF12_consultar_prestamos_clasifica_respeta_encargado_y_no_muta` | PASSED / Exitoso | `issue-16-casos-funcionales.md` |
| CP-06 | RF-07 | Borde | `test_CP06_RF07_limite_exacto_tres_equipos_activos_es_permitido` | PASSED / Exitoso | `issue-17-casos-borde.md` |
| CP-07 | RF-10 | Borde | `test_CP07_RF10_devolucion_exactamente_en_fecha_termino_no_genera_atraso` | PASSED / Exitoso | `issue-17-casos-borde.md` |
| CP-08 | RF-08 | Borde | `test_CP08_RF08_inicio_igual_a_termino_de_reserva_existente_rechaza_por_rn10` | PASSED / Exitoso | `issue-17-casos-borde.md` |
| CP-09 | RF-06 | Borde | `test_CP09_RF06_fecha_inicio_igual_a_fecha_termino_habil_cuenta_un_dia` | PASSED / Exitoso | `issue-17-casos-borde.md` |
| CP-10 | RF-10 | Negativo | `test_CP10_RF10_devolver_prestamo_aprobado_nunca_entregado_rechaza_por_rn14` | PASSED / Exitoso | `issue-18-casos-negativos.md` |
| CP-11 | RF-08 | Negativo | `test_CP11_RF08_solicitante_no_puede_aprobar_solicitud_por_rn11` | PASSED / Exitoso | `issue-18-casos-negativos.md` |
| CP-12 | RF-05 | Negativo | `test_CP12_RF05_fecha_termino_anterior_al_inicio_rechaza_por_rn17` | PASSED / Exitoso | `issue-18-casos-negativos.md` |
| CP-13 | RF-07 | Combinacion | `test_CP13_RF07_el_atraso_retiene_el_cupo_de_equipos_activos_rn16_y_rn07` | PASSED / Exitoso | `issue-19-casos-combinados-escenario.md` |
| CP-14 | RF-07 | Combinacion | `test_CP14_RF07_la_cancelacion_libera_solo_el_cupo_cancelado_rn15_y_rn07` | PASSED / Exitoso | `issue-19-casos-combinados-escenario.md` |
| CP-15 | RF-01, RF-02, RF-03, RF-05, RF-08, RF-09, RF-10, RF-12 | Escenario completo | `test_CP15_RF01_a_RF12_ciclo_completo_sobre_persistencia_real` | PASSED / Exitoso | `issue-19-casos-combinados-escenario.md` |

Trazabilidad de la tabla a los archivos que la sustentan:

| Categoria | Casos | Marcador | Archivo | Evidencia |
| --- | --- | --- | --- | --- |
| Funcionales | CP-01 a CP-05 | `funcional` | `tests/funcionales/test_funcionales.py` | `issue-16-casos-funcionales.md` |
| Borde | CP-06 a CP-09 | `borde` | `tests/borde/test_borde.py` | `issue-17-casos-borde.md` |
| Negativos | CP-10 a CP-12 | `negativo` | `tests/negativos/test_negativos.py` | `issue-18-casos-negativos.md` |
| Combinacion | CP-13, CP-14 | `combinacion` | `tests/integracion/test_escenario_completo.py` | `issue-19-casos-combinados-escenario.md` |
| Escenario completo | CP-15 | `escenario` | `tests/integracion/test_escenario_completo.py` | `issue-19-casos-combinados-escenario.md` |

Los 15 casos son los que responden al minimo exigido, no el total de la suite.
Tras integrar #15 y agregar las pruebas cruzadas de #20, `pytest` recolecta 303
pruebas: 302 quedan en verde y 1 queda como XFAIL documentado por DEF-02 /
issue #47. Las 288 pruebas restantes cubren modulos, flujos y pruebas cruzadas
sin etiqueta CP-XX. Esa separacion es deliberada y esta anotada en los docstrings
de esas pruebas (ver DEF-01, issue #43): usan nombres descriptivos, y la etiqueta
CP-XX queda reservada para los casos que este documento contabiliza.

Ejecucion completa registrada para #24: `pytest -v` termino con
`302 passed, 1 xfailed in 17.64s`; los 15 casos CP-01 a CP-15 salieron PASSED y
el unico XFAIL es
`tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_04_RN18_entrega_debe_quedar_en_log_de_auditoria`.
La salida literal esta en `docs/evidencias/pruebas/issue-24-pytest-v.txt`.

La matriz de trazabilidad sigue pendiente: exige un criterio de aceptacion por
RF que no forma parte de ninguno de los issues de pruebas.
