# Defectos, correcciones y reejecuciones

Cada defecto se registra ademas como Issue en GitHub.

| ID | Issue | Caso que lo detecto | Severidad (justificada) | Estado | Commit/PR de correccion | Reejecucion |
| --- | --- | --- | --- | --- | --- | --- |
| DEF-01 | #43 | Revision documental de RN contra CP | Media: la documentacion de reglas apuntaba a CP inexistentes, lo que rompia trazabilidad aunque la suite pasara. | Abierto | Pendiente | Pendiente |
| DEF-02 | #47 | PC20-04 | Media: las mutaciones de prestamos cambian el inventario fisico, pero no registran eventos de auditoria exigidos por RN-18. | Abierto | Pendiente | XFAIL en `tests/cruzadas/test_integrante_1_revisa_integrante_2.py::test_PC20_04_RN18_entrega_debe_quedar_en_log_de_auditoria` |

## Si la aplicacion no fallo

Explicar las tecnicas de prueba utilizadas y que riesgos permanecen.
