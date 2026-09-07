# Matriz de trazabilidad

Traza los 14 requerimientos funcionales del sistema (RF-01 a RF-14) contra las
reglas de negocio que los gobiernan, el código que los implementa y los casos de
prueba que los verifican. Los IDs son idénticos en este documento, el código,
las pruebas y los Issues.

- Requerimientos y criterios de aceptación: `docs/analisis-requerimiento.md`
- Reglas de negocio: `docs/reglas-negocio.md`
- Casos de prueba: `docs/casos-de-prueba.md`
- Defectos: `docs/defectos.md`

Los criterios de aceptación se transcriben literalmente desde
`docs/analisis-requerimiento.md` para que no existan dos versiones del contrato.
La columna de implementación cita la función que rompería el criterio si se
eliminara, con una segunda referencia cuando la regla se reparte entre la capa
que orquesta y la guarda que la valida.

Respaldo de ejecución de cierre: `PATH=.venv/bin:$PATH pytest` recolecto 306
pruebas y termino con `306 passed in 24.26s`. PC20-04 pasa normalmente: DEF-02
(#47) fue corregido al auditar las mutaciones de `ServicioPrestamos`.

## Matriz

| RF | Criterio de aceptación | RN relacionadas | Implementación (archivo:línea) | Casos de prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| RF-01 | Dado un usuario con ID, nombre, correo, rol, estado y contraseña válidos, el sistema lo persiste; si falta un dato obligatorio o el ID/correo ya existe, rechaza el registro. | RN-01, RN-03, RN-17, RN-20 | `src/prestamos/servicios/usuarios.py:105` (`ServicioUsuarios.registrar_usuario`) (orquesta), `src/prestamos/servicios/usuarios.py:354` (`_proteger_ultimo_encargado`) (guarda RN-20) | CP-15 | Verificado |
| RF-02 | Dadas credenciales válidas de un usuario activo, se inicia sesión; dadas credenciales inválidas o usuario inactivo, se rechaza el acceso sin mostrar contraseñas. | RN-01, RN-02 | `src/prestamos/auth.py:223` (`ServicioAuth.iniciar_sesion`) | CP-01, CP-15 | Verificado |
| RF-03 | Dado un equipo con código, nombre, tipo, descripción y estado válido, se guarda; si el código ya existe o falta un campo obligatorio, se rechaza. | RN-04, RN-17, RN-21 | `src/prestamos/servicios/equipos.py:100` (`ServicioEquipos.registrar_equipo`) (orquesta), `src/prestamos/servicios/equipos.py:319` (`_exigir_sin_prestamo_activo`) (guarda RN-21) | CP-15, CX03, CX04 | Verificado |
| RF-04 | Al consultar equipos, el sistema muestra equipos registrados y permite identificar si están disponibles para un período solicitado. | RN-05, RN-10 | `src/prestamos/servicios/equipos.py:78` (`ServicioEquipos.listar`) (orquesta), `src/prestamos/reglas.py:361` (`equipo_disponible`) (guarda) | CP-08, CX02 | Verificado |
| RF-05 | Dada una solicitud con solicitante activo, 1 a 3 equipos, fechas válidas y motivo, el sistema la crea en estado solicitada. | RN-05, RN-06, RN-17 | `src/prestamos/servicios/solicitudes.py:108` (`ServicioSolicitudes.crear_solicitud`) (orquesta), `src/prestamos/reglas.py:756` (`_validar_cantidad_equipos`) (guarda RN-06) | CP-12, CP-15 | Verificado |
| RF-06 | Si la solicitud supera 5 días hábiles o empieza a más de 20 días laborales, el sistema la rechaza con mensaje claro. | RN-08, RN-09 | `src/prestamos/reglas.py:772` (`_validar_fechas_reserva`) | CP-09 | Verificado |
| RF-07 | Si el solicitante supera 3 equipos activos al sumar reservas aprobadas y préstamos vigentes, el sistema rechaza la nueva solicitud o aprobación. | RN-07 | `src/prestamos/reglas.py:852` (`_validar_limite_equipos_activos`) | CP-06, CP-13, CP-14 | Verificado |
| RF-08 | Un encargado puede aprobar una solicitud solicitada solo si cumple reglas; también puede rechazarla indicando motivo. | RN-05, RN-10, RN-11, RN-12, RN-22 | `src/prestamos/servicios/solicitudes.py:163` (`ServicioSolicitudes.aprobar`) (orquesta), `src/prestamos/reglas.py:577` (`_validar_aprobacion`) (guarda) | CP-08, CP-11, CP-15, CX01, CX02, CX05 | Verificado |
| RF-09 | Una solicitud aprobada puede pasar a entregada; una solicitud rechazada, cancelada, devuelta o sin aprobar no puede entregarse. | RN-13 | `src/prestamos/servicios/prestamos.py:40` (`ServicioPrestamos.registrar_entrega`) (orquesta), `src/prestamos/reglas.py:664` (`_validar_entrega`) (guarda) | CP-02, CP-15, PC20-04 | Verificado |
| RF-10 | Una solicitud entregada puede pasar a devuelta y liberar sus equipos; otro estado no puede devolverse. | RN-14 | `src/prestamos/servicios/prestamos.py:71` (`ServicioPrestamos.registrar_devolucion`) (orquesta), `src/prestamos/reglas.py:719` (`_validar_devolucion`) (guarda) | CP-03, CP-07, CP-10, CP-15, PC20-01 | Verificado |
| RF-11 | Una solicitud solicitada o aprobada puede cancelarse antes de la entrega; una solicitud entregada o devuelta no puede cancelarse. | RN-15 | `src/prestamos/servicios/prestamos.py:116` (`ServicioPrestamos.cancelar`) (orquesta), `src/prestamos/reglas.py:636` (`_validar_cancelacion`) (guarda) | CP-04, CP-14 | Verificado |
| RF-12 | El sistema clasifica futuros, vigentes y atrasados según fecha actual, estado y fecha de término. | RN-16, RN-19 | `src/prestamos/servicios/prestamos.py:269` (`ServicioPrestamos._consultar`) (clasifica y filtra), `src/prestamos/servicios/prestamos.py:289` (`_id_usuario_visible`) (guarda RN-19) | CP-05, CP-15, PC20-02, PC20-03 | Verificado |
| RF-13 | Login exitoso/fallido, creación, aprobación, rechazo, entrega, devolución, cancelación y errores quedan registrados sin incluir contraseñas. | RN-18 | `src/prestamos/logging_conf.py:47` (`registrar_evento`) (orquesta), `src/prestamos/logging_conf.py:70` (`sanitizar`) (guarda), `src/prestamos/servicios/prestamos.py` (mutaciones de préstamos) | CP-32, CP-33, CP-34, PC20-04 | Verificado |
| RF-14 | El comando de carga demo crea usuarios, equipos y datos suficientes para probar el flujo principal desde solicitud hasta devolución. | Sin RN asociada | `src/prestamos/demo.py:62` (`inicializar_datos_demo`) | PC20-05 | Verificado |

## Notas de trazabilidad

1. **Cobertura de reglas.** Las 22 reglas documentadas en `docs/reglas-negocio.md`
   aparecen al menos una vez en la columna "RN relacionadas": RN-01 a RN-22 sin
   huecos. RF-14 es el único requerimiento sin RN asociada, porque la carga de
   datos de demostración no impone restricciones de negocio propias.

2. **Origen de cada columna.** La columna "RN relacionadas" se deriva invirtiendo
   la columna de origen (`AMB-xx / RF-xx`) de `docs/reglas-negocio.md`, y la
   columna de casos se deriva de las pruebas efectivamente ejecutadas. No se usa
   la columna de casos de `docs/reglas-negocio.md`, porque su mapeo RN-CP no es
   confiable: apunta a casos que no existen y también a casos que existen pero
   verifican otra regla. Por ejemplo, allí RN-07 figura cubierta por CP-11 y
   CP-12, cuando CP-11 verifica RN-11 y CP-12 verifica RN-17; el límite de
   equipos activos lo prueban en realidad CP-06, CP-13 y CP-14.

3. **Sin pruebas huérfanas.** Toda prueba ejecutada con identificador propio
   aparece en al menos una fila: CP-01 a CP-15, CP-32 a CP-34, PC20-01 a PC20-05
   y CX01 a CX05.

4. **Identificadores adicionales.** CX01 a CX05 (pruebas cruzadas del issue #21,
   en `tests/cruzadas/test_cruzadas_benjamin.py`) se ejecutan y pasan. CP-32 a
   CP-34 son casos adicionales de observabilidad de RF-13, documentados en
   `docs/casos-de-prueba.md` y ejecutados en
   `tests/funcionales/test_observabilidad.py`.

5. **Casos inexistentes removidos.** La auditoría de DEF-01/#43 confirmó que
   los IDs históricos intermedios entre CP-15 y CP-32 no existen como tests.
   Las referencias a esos IDs se reemplazaron por CP-01 a CP-15, CP-32 a
   CP-34, PC20 o CX según la prueba real que corresponde.

6. **RF-04 sin caso dedicado.** Ningún CP lleva RF-04 en su nombre. El
   requerimiento se verifica de forma indirecta mediante CP-08 (solapamiento de
   fechas, RN-10) y CX02 (equipo en mantención no puede comprometerse, RN-05),
   además de las pruebas unitarias de catálogo y disponibilidad en
   `tests/unidad/test_servicio_equipos.py` y `tests/unidad/test_reglas.py`, que no
   llevan identificador CP.

7. **Estado de verificación.** `Verificado` significa que existe al menos una
   prueba ejecutada y en verde que cubre el criterio de aceptación. Tras la
   corrección de DEF-02/#47, no queda ninguna fila en estado
   `Verificado con defecto`.
