# Issue #21 - Pruebas cruzadas Benjamin (#10 y #11)

Fecha de ejecucion: 2026-09-06
Ejecutado por: IsaiasACF

## Alcance

Se agregaron cinco pruebas nuevas e independientes usando servicios reales y repositorios JSON temporales (`tmp_path`). Las pruebas cruzan las operaciones de usuarios/equipos (#10) con aprobacion y rechazo de solicitudes (#11), verificando efectos secundarios persistidos.

## Casos agregados

| Caso | Cruce validado | Resultado esperado |
| --- | --- | --- |
| CX-01 | Desactivar solicitante y luego aprobar su solicitud | Se rechaza por RN-02; solicitud queda SOLICITADA y equipo DISPONIBLE |
| CX-02 | Enviar equipo a mantencion y luego aprobar solicitud | Se rechaza por RN-05; solicitud queda SOLICITADA y equipo MANTENCION |
| CX-03 | Aprobar solicitud y luego dar de baja el equipo | Se rechaza por RN-21; solicitud queda APROBADA y equipo RESERVADO |
| CX-04 | Rechazar solicitud y luego dar de baja el equipo | Se permite la baja; solicitud queda RECHAZADA con motivo y equipo BAJA |
| CX-05 | Promover solicitante y luego aprobar su propia solicitud | Se rechaza por RN-22; solicitud queda SOLICITADA y equipo DISPONIBLE |

## Defectos

No se detectaron defectos en la ejecucion de las pruebas nuevas.

## Ejecuciones

```bash
PATH=.venv/bin:$PATH pytest tests/cruzadas/test_cruzadas_benjamin.py -v
```

Resultado: `5 passed in 0.49s`.

```bash
PATH=.venv/bin:$PATH pytest
```

Resultado: `298 passed in 22.19s`.
