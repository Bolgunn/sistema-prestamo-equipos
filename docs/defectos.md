# Defectos, correcciones y reejecuciones

Cada defecto se registra ademas como Issue en GitHub.

| ID | Issue | Caso que lo detecto | Severidad (justificada) | Estado | Commit/PR de correccion | Reejecucion |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | Issue #21: pruebas cruzadas sobre usuarios/equipos y aprobacion/rechazo | - | Sin defectos detectados | No aplica | `PATH=.venv/bin:$PATH pytest tests/cruzadas/test_cruzadas_benjamin.py -v` |

## Si la aplicacion no fallo

En el issue #21 se aplicaron pruebas cruzadas nuevas e independientes sobre la funcionalidad de usuarios/equipos (#10) y aprobacion/rechazo de solicitudes (#11), usando servicios reales y repositorios JSON temporales sobre `tmp_path`.

Los casos cubrieron efectos secundarios entre modulos: desactivacion de solicitante antes de aprobar, envio de equipo a mantencion antes de aprobar, baja bloqueada por solicitud aprobada, baja permitida tras rechazo y promocion de un solicitante que luego intenta aprobar su propia solicitud. En esta ejecucion no se detectaron defectos: las operaciones rechazadas conservaron la solicitud/equipo sin cambios indebidos y las operaciones permitidas persistieron los estados esperados.

Riesgos que permanecen: estas pruebas no sustituyen pruebas de concurrencia entre procesos, ni cubren la interfaz CLI, ni validan integraciones futuras de entrega/devolucion fuera del cruce especifico entre #10 y #11.
