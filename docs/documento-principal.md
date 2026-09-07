# Documento principal - Sistema de prestamo de equipos

Este documento integra la entrega final de la Tarea 1 sin duplicar los archivos
detallados. Cada seccion resume el estado del entregable correspondiente y enlaza
la evidencia real del repositorio.

Repositorio publico: [nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos)

## 1. Codificar requerimiento

Se implemento una aplicacion CLI en Python para administrar prestamos de equipos
de laboratorio. El requerimiento mejorado esta documentado en
[analisis-requerimiento.md](analisis-requerimiento.md): parte de las
ambiguedades AMB-01 a AMB-14, formula preguntas al cliente y deriva RF-01 a
RF-14.

La implementacion vive en `src/prestamos/` y cubre persistencia JSON,
autenticacion, usuarios/equipos, motor de reglas, solicitudes, entrega,
devolucion, cancelacion, consultas, CLI/menu, observabilidad y datos demo.

Documentos de referencia:

- [analisis-requerimiento.md](analisis-requerimiento.md): ambiguedades, preguntas y RF/RNF.
- [reglas-negocio.md](reglas-negocio.md): RN-01 a RN-22, alcance, exclusiones y supuestos.
- [estados-transiciones.md](estados-transiciones.md): estados, transiciones T-01 a T-09 y disponibilidad.

Issues/PRs representativos:

- [Issue #12](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/12): entrega, devolucion y cancelacion.
- [Issue #13](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/13): consultas de prestamos.
- [Issue #14](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/14): CLI y menu interactivo.
- [Issue #15](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/15): datos demo e `init-demo`.
- [PR #53](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/53): solicitudes y ajuste documental de RN-22 en T-02.
- [PR #55](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/55): CLI/menu y correcciones de seguridad/UX.
- [PR #57](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/57): datos demo e `init-demo` reproducible.

## 2. Probar aplicacion

La estrategia de pruebas esta resumida en [estrategia-pruebas.md](estrategia-pruebas.md)
y los casos CP-01 a CP-15 estan en [casos-de-prueba.md](casos-de-prueba.md). La
suite cubre casos funcionales, borde, negativos, combinados, escenario completo,
CLI, observabilidad, datos demo y pruebas cruzadas.

Resultado consolidado existente: `pytest -v` recolecto 303 pruebas y termino con
`302 passed, 1 xfailed`; el `xfail` corresponde al defecto abierto DEF-02/#47.
La evidencia literal esta enlazada desde [verificacion-validacion.md](verificacion-validacion.md)
y en [issue-22-pytest-v.txt](evidencias/verificacion/issue-22-pytest-v.txt).

Evidencias principales:

- [issue-16-casos-funcionales.md](evidencias/pruebas/issue-16-casos-funcionales.md): CP-01 a CP-05.
- [issue-17-casos-borde.md](evidencias/pruebas/issue-17-casos-borde.md): CP-06 a CP-09.
- [issue-18-casos-negativos.md](evidencias/pruebas/issue-18-casos-negativos.md): CP-10 a CP-12.
- [issue-19-casos-combinados-escenario.md](evidencias/pruebas/issue-19-casos-combinados-escenario.md): CP-13 a CP-15.
- [issue-20-pruebas-cruzadas-integrante-1.md](evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md): pruebas cruzadas sobre #12 a #15.
- [issue-21-pruebas-cruzadas-benjamin.md](evidencias/pruebas/issue-21-pruebas-cruzadas-benjamin.md): pruebas cruzadas sobre #10 y #11.

Issues/PRs representativos:

- [Issue #16](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/16): CP-01 a CP-05 funcionales.
- [Issue #17](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/17): CP-06 a CP-09 de borde.
- [PR #58](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/58): pruebas cruzadas del integrante 1.
- [PR #59](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/59): pruebas cruzadas del integrante 2.

## 3. Incluir logs y Sentry

La observabilidad se implemento en `src/prestamos/logging_conf.py`,
`src/prestamos/observabilidad.py` y `src/prestamos/errores.py`. La CLI captura
errores de dominio e inesperados sin mostrar tracebacks al usuario, y Sentry se
inicializa desde `SENTRY_DSN` cuando existe; sin DSN, la aplicacion sigue
funcionando.

Evidencia disponible:

- `tests/funcionales/test_observabilidad.py`: pruebas automatizadas de logs, Sentry sin DSN, errores de dominio y sanitizacion.
- `tests/funcionales/test_cli_errores.py`: ausencia de traceback en errores de CLI.
- [sentry-evento-prueba.png](evidencias/validacion/sentry-evento-prueba.png): evidencia visual de un evento real en Sentry.
- [defectos.md](defectos.md): DEF-02/#47 mantiene abierto que algunas operaciones de prestamos todavia no registran auditoria completa.

Issue/PR representativo:

- [Issue #8](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/8): errores de dominio, logs y Sentry.
- [PR #55](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/55): correcciones de no filtrar variables locales a Sentry y manejo seguro de CLI.

## 4. Enlace al repositorio publico

El repositorio publico esta en GitHub:

- [https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos)

La organizacion del trabajo esta documentada en [trabajo-colaborativo.md](trabajo-colaborativo.md):
flujo Git, ramas, Pull Requests, tablero, hitos, reparto por rebanadas verticales
y criterios de revision.

PRs representativos de integracion y revision:

- [PR #50](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/50): gestion de usuarios/equipos; revision produjo el commit `f413186` sobre logs idempotentes.
- [PR #53](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/53): solicitudes; revision produjo el commit `7f25fd1` sobre documentacion de RN-22.
- [PR #55](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/55): CLI/menu; revision produjo el commit `7fc57ab`.
- [PR #57](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/57): datos demo; revision produjo el commit `a734f26`.
- [PR #58](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/58) y [PR #59](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/59): pruebas cruzadas.

## 5. README con descripcion, tecnologias, instalacion, ejecucion, demo, autores y licencia

El README principal existe y enlaza los documentos de entrega:
[README.md](../README.md). Incluye descripcion del sistema, tecnologias,
instrucciones de instalacion, comandos de ejecucion, datos de demostracion,
credenciales ficticias, autores y licencia.

Los datos demo se describen en [datos/demo/README.md](../datos/demo/README.md) y
representan el laboratorio al `2026-09-10`. El comando documentado es:

```bash
python -m prestamos init-demo
python -m prestamos --datos-dir datos/demo --usuario enc-demo prestamos atrasados --fecha 2026-09-10
```

Issues/PRs representativos:

- [Issue #15](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/15) y [PR #57](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/57): datos demo e instrucciones reproducibles.
- [Issue #28](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/28): README final para instalacion, ejecucion y datos demo.

## 6. Documento principal en el repositorio

Este archivo cumple la funcion de documento integrador final. Enlaza los
documentos detallados y evita repetirlos completos. La estructura sigue el orden
de los nueve entregables del enunciado.

Documentos enlazados desde este integrador:

- [analisis-requerimiento.md](analisis-requerimiento.md)
- [reglas-negocio.md](reglas-negocio.md)
- [estados-transiciones.md](estados-transiciones.md)
- [matriz-trazabilidad.md](matriz-trazabilidad.md)
- [estrategia-pruebas.md](estrategia-pruebas.md)
- [casos-de-prueba.md](casos-de-prueba.md)
- [defectos.md](defectos.md)
- [verificacion-validacion.md](verificacion-validacion.md)
- [trabajo-colaborativo.md](trabajo-colaborativo.md)
- [uso-ia.md](uso-ia.md)
- [reflexiones/](reflexiones/)

Issue representativo:

- [Issue #25](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/25): documento principal integrador.

## 7. Planilla o archivo de casos de prueba

La planilla de casos esta en [casos-de-prueba.md](casos-de-prueba.md). Contiene
CP-01 a CP-15 con requerimiento, categoria, precondiciones, pasos, datos,
resultado esperado, resultado obtenido real, estado, evidencia, ejecutor y fecha.

Resumen por categoria, segun [estrategia-pruebas.md](estrategia-pruebas.md):

| Categoria | Casos | Resultado |
| --- | --- | --- |
| Funcionales | CP-01 a CP-05 | 5 ejecutados, 5 exitosos |
| Borde | CP-06 a CP-09 | 4 ejecutados, 4 exitosos |
| Negativos | CP-10 a CP-12 | 3 ejecutados, 3 exitosos |
| Combinacion | CP-13 y CP-14 | 2 ejecutados, 2 exitosos |
| Escenario completo | CP-15 | 1 ejecutado, 1 exitoso |

Tambien existen pruebas adicionales sin ID CP, incluyendo CLI, observabilidad,
servicios, motor de reglas, datos demo y pruebas cruzadas.

Issues representativos:

- [Issue #16](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/16): casos funcionales.
- [Issue #17](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/17): casos de borde.
- [Issue #20](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/20) y [Issue #21](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/21): pruebas cruzadas.

## 8. Evidencias de ejecucion

Las evidencias se guardan bajo `docs/evidencias/` y estan enlazadas desde los
documentos de pruebas y verificacion.

Evidencias principales:

- [evidencias/pruebas/issue-16-casos-funcionales.md](evidencias/pruebas/issue-16-casos-funcionales.md)
- [evidencias/pruebas/issue-17-casos-borde.md](evidencias/pruebas/issue-17-casos-borde.md)
- [evidencias/pruebas/issue-18-casos-negativos.md](evidencias/pruebas/issue-18-casos-negativos.md)
- [evidencias/pruebas/issue-19-casos-combinados-escenario.md](evidencias/pruebas/issue-19-casos-combinados-escenario.md)
- [evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md](evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md)
- [evidencias/pruebas/issue-21-pruebas-cruzadas-benjamin.md](evidencias/pruebas/issue-21-pruebas-cruzadas-benjamin.md)
- [evidencias/pruebas/issue-24-pytest-v.txt](evidencias/pruebas/issue-24-pytest-v.txt)
- [evidencias/verificacion/issue-22-pytest-v.txt](evidencias/verificacion/issue-22-pytest-v.txt)
- [evidencias/validacion/sentry-evento-prueba.png](evidencias/validacion/sentry-evento-prueba.png)

## 9. Issues y Pull Requests utilizados durante el proyecto

El proyecto se organizo con GitHub Issues, ramas cortas y Pull Requests hacia
`develop`. El reparto y la metodologia estan en [trabajo-colaborativo.md](trabajo-colaborativo.md)
y el grafo de dependencias en [dag-dependencias.md](dag-dependencias.md).

Issues destacados:

- [#8](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/8): observabilidad.
- [#12](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/12): entrega, devolucion y cancelacion.
- [#13](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/13): consultas.
- [#14](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/14): CLI y menu.
- [#15](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/15): datos demo.
- [#16](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/16) y [#17](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/17): CP funcionales y de borde.
- [#20](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/20) y [#21](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/21): pruebas cruzadas.
- [#22](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/22): verificacion y validacion.
- [#23](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/23): matriz de trazabilidad.
- [#24](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/24): estrategia y evidencias de pruebas.
- [#25](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/25): este documento principal.
- [#26](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/26): declaracion de uso de IA.
- [#27](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/27): reflexiones individuales.
- [#28](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/28): README final.
- [#43](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/43) y [#47](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/issues/47): defectos abiertos documentados.

PRs destacados:

- [PR #50](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/50): usuarios/equipos y cambio por revision sobre logs idempotentes.
- [PR #53](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/53): solicitudes y documentacion de RN-22.
- [PR #55](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/55): CLI/menu con correcciones de seguridad/UX.
- [PR #57](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/57): datos demo reproducibles.
- [PR #58](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/58): pruebas cruzadas del integrante 1.
- [PR #59](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/59): pruebas cruzadas del integrante 2.
- [PR #62](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/62): declaracion de uso de IA.
- [PR #63](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/63): reflexion individual de IsaiasACF.
- [PR #64](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/64): matriz de trazabilidad completa.
- [PR #67](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/pull/67): reflexion individual de Benjamin.

## Supuestos y decisiones consolidadas

Los supuestos completos estan en [reglas-negocio.md](reglas-negocio.md). Las
decisiones mas relevantes para entender la entrega son:

- La aplicacion es de linea de comando; no se implementa interfaz web ni movil.
- La persistencia usa archivos JSON locales, sin base de datos externa.
- Solo hay dos roles operativos: `SOLICITANTE` y `ENCARGADO`.
- La autenticacion es local y basica; las contrasenas reales no se versionan. Las credenciales demo son ficticias y se guardan como hash.
- Las bajas de usuarios y equipos son logicas y reversibles para conservar historial.
- Los codigos de equipo no se reutilizan, incluso si el equipo fue dado de baja.
- El prestamo se modela con estados `SOLICITADA`, `APROBADA`, `RECHAZADA`, `CANCELADA`, `ENTREGADA`, `ATRASADA` y `DEVUELTA`.
- Las transiciones validas estan centralizadas en el motor de reglas; la CLI no replica reglas de negocio.
- La disponibilidad no depende solo de `Equipo.estado`: tambien se calcula con fechas y prestamos existentes.
- El rango de fechas usa dias habiles/laborales como lunes a viernes; no se modelan feriados.
- Las consultas de prestamos clasifican sin mutar ni persistir estados.
- `init-demo --force` debe ser reproducible byte a byte, por eso los hashes demo son fijos solo en `demo.py`.
- Las pruebas CP-01 a CP-15 son el minimo de la tarea; la suite incluye mas pruebas sin ID CP.

## Estado de pendientes conocidos

Los pendientes que este documento mantiene visibles son los defectos abiertos registrados en [defectos.md](defectos.md):

- DEF-01/#43: inconsistencia historica de numeracion CP-XX en documentos.
- DEF-02/#47: falta de logs de auditoria en algunas operaciones de prestamos, reproducida por la prueba cruzada PC20-04.
