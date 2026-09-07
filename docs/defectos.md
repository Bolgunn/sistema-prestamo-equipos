# Defectos, correcciones y reejecuciones

Cada defecto se registra ademas como Issue en GitHub.

| ID | Issue | Caso que lo detecto | Severidad (justificada) | Estado | Commit/PR de correccion | Reejecucion |
| --- | --- | --- | --- | --- | --- | --- |
| DEF-01 | #43 | Revision documental de RN contra CP | Media: la documentacion de reglas apuntaba a CP inexistentes, lo que rompia trazabilidad aunque la suite pasara. | Corregido | Rama de cierre final / issue #43 | Se auditaron `docs/reglas-negocio.md`, `docs/estados-transiciones.md`, `docs/matriz-trazabilidad.md`, `docs/estrategia-pruebas.md`, `docs/casos-de-prueba.md` y `tests/`; no quedan referencias CP a casos inexistentes. Reejecución final: `PATH=.venv/bin:$PATH pytest` terminó con `306 passed in 24.26s`. |
| DEF-02 | #47 | PC20-04 reproduce/confirma el defecto detectado previamente | Media: las mutaciones de prestamos cambian el inventario fisico y deben quedar auditadas por RN-18. | Corregido | Rama de cierre final / issue #47 | `PATH=.venv/bin:$PATH pytest tests/cruzadas/test_integrante_1_revisa_integrante_2.py -v`: `5 passed in 2.62s`; PC20-04 pasa normalmente. Reejecución final: `PATH=.venv/bin:$PATH pytest` terminó con `306 passed in 24.26s`. |

## Si la aplicacion no fallo

| Issue | Casos | Resultado | Evidencia |
| --- | --- | --- | --- |
| #21 | Pruebas cruzadas sobre usuarios/equipos y aprobacion/rechazo | Sin defectos detectados | `PATH=.venv/bin:$PATH pytest tests/cruzadas/test_cruzadas_benjamin.py -v` |

En el issue #21 se aplicaron pruebas cruzadas nuevas e independientes sobre la funcionalidad de usuarios/equipos (#10) y aprobacion/rechazo de solicitudes (#11), usando servicios reales y repositorios JSON temporales sobre `tmp_path`.

Los casos cubrieron efectos secundarios entre modulos: desactivacion de solicitante antes de aprobar, envio de equipo a mantencion antes de aprobar, baja bloqueada por solicitud aprobada, baja permitida tras rechazo y promocion de un solicitante que luego intenta aprobar su propia solicitud. En esta ejecucion no se detectaron defectos: las operaciones rechazadas conservaron la solicitud/equipo sin cambios indebidos y las operaciones permitidas persistieron los estados esperados.

Riesgos que permanecen: estas pruebas no sustituyen pruebas de concurrencia entre procesos, ni cubren la interfaz CLI, ni validan integraciones futuras de entrega/devolucion fuera del cruce especifico entre #10 y #11.
