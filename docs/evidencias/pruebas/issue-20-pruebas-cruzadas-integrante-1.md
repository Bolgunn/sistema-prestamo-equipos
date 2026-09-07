# Issue #20 - Pruebas cruzadas integrante 1 sobre integrante 2

Rama: test/cruzadas-integrante-1

Fecha: 2026-09-07

Ejecutado por: nonmeeeeeeeeeeeeeee

## Alcance

Segun docs/trabajo-colaborativo.md, Integrante 2 desarrolla principalmente:

- #12 entrega/devolucion/cancelacion.
- #13 consultas de prestamos.
- #14 CLI y menu.
- #15 datos demo e init-demo.

Los casos se disenaron desde docs/analisis-requerimiento.md, docs/reglas-negocio.md
y docs/trabajo-colaborativo.md antes de revisar el codigo del companero. Tras
la integracion de #15 en develop, la prueba cruzada automatizada cubre #12,
#13, #14 y #15.

## Casos disenados

| ID | Requerimiento / regla | Objetivo | Resultado esperado |
| --- | --- | --- | --- |
| PC20-01 | RF-10 / RN-14 | Intentar devolver solo parte de los equipos de un prestamo entregado. | La devolucion parcial se rechaza, el prestamo sigue ENTREGADA y todos los equipos siguen PRESTADO. |
| PC20-02 | RF-12 / RN-19 | Consultar atrasados como Solicitante con prestamos propios y ajenos. | El Solicitante ve solo los propios; si filtra por otro usuario recibe ErrorAutorizacion RN-19. |
| PC20-03 | RF-12 / RN-17 / RNF-01 | Ejecutar el subcomando CLI `prestamos futuros` con filtro por usuario y equipo. | La salida muestra solo el prestamo que cumple ambos filtros y no imprime tracebacks. |
| PC20-04 | RN-18 | Verificar que registrar entrega deja evidencia de auditoria en logs. | Debe existir un evento de entrega sin contrasenas. Hoy queda XFAIL por DEF-02 / #47. |
| PC20-05 | RF-14 / RNF-03 | Ejecutar `init-demo` y luego una consulta CLI con las credenciales documentadas. | El revisor puede crear datos demo, autenticarse como `enc-demo` y consultar el prestamo atrasado `S-0004`. |

## Ejecucion

Comando:

```powershell
.venv\Scripts\pytest.exe tests\cruzadas\test_integrante_1_revisa_integrante_2.py -v
```

Resultado inicial:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Dev\sistema-prestamo-equipos\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Dev\sistema-prestamo-equipos
configfile: pyproject.toml
collecting ... collected 5 items

tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_01_RF10_devolucion_parcial_no_libera_prestamo_ni_equipos PASSED [ 20%]
tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_02_RF12_solicitante_solo_ve_sus_prestamos_atrasados PASSED [ 40%]
tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_03_RF12_cli_futuros_filtra_por_usuario_y_equipo PASSED [ 60%]
tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_04_RN18_entrega_debe_quedar_en_log_de_auditoria XFAIL [ 80%]
tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_05_RF14_init_demo_permita_consulta_manual_documentada PASSED [100%]

======================== 4 passed, 1 xfailed in 1.85s =========================
```

Reejecucion de regresion completa:

```powershell
.venv\Scripts\pytest.exe -v
```

Resumen:

```text
======================= 297 passed, 1 xfailed in 17.97s =======================
```

## Defectos

| ID | Issue | Caso que lo detecto | Severidad | Estado |
| --- | --- | --- | --- | --- |
| DEF-02 | #47 | PC20-04 reproduce/confirma el defecto detectado previamente | Media: las entregas, devoluciones y cancelaciones modifican inventario fisico, pero no quedan auditadas pese a RN-18. | Abierto |

## Riesgo pendiente

PC20-05 valida el flujo minimo de revisor sobre #15. Permanece pendiente la
correccion de DEF-02 / #47 para que PC20-04 deje de ser XFAIL y pase como
regresion normal.
