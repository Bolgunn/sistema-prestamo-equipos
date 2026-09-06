# PLAN — Issue #11: solicitud, aprobación y rechazo de préstamos

Rama: `feat/solicitudes` (creada desde `origin/develop` @ `edc9573`).

Este documento registra las decisiones de diseño acordadas antes de implementar.
Cada sección explica **qué** se hace y **por qué**, para que la revisión no tenga
que reconstruir el razonamiento desde el diff.

---

## 0. Contexto: por qué este issue es más chico y más grande de lo que parece

`src/prestamos/servicios/solicitudes.py` es hoy un stub de una línea, pero
`reglas.py` ya implementa casi todo lo que pide la Definition of Done: las
transiciones T-01/T-02/T-03, el solapamiento (RN-10), el límite de equipos
activos (RN-07) y el plazo máximo (RN-08). El servicio es, por lo tanto, una
capa delgada de orquestación.

Lo que sí falta, y no estaba anotado en el issue:

1. **Nadie puede aprobar su propia solicitud** no corresponde a ninguna RN
   existente, y `_validar_aprobacion` descarta explícitamente al operador
   (`del usuario`).
2. **Nadie escribe `EstadoEquipo.RESERVADO`.** `equipos.py:328` y
   `test_servicio_equipos.py:259` dejan comentarios diciendo que la aprobación
   (#11) debería hacerlo.

El punto 2 arrastra un cambio en `reglas.py` que es la parte más delicada de la
rama, y está explicado en la sección 3.

---

## 1. Convención de autorización: B

`ServicioSolicitudes` recibe un `ServicioAuth` inyectado y llama
`auth.requiere_rol(...)` por dentro, como `ServicioUsuarios` y `ServicioEquipos`.
No recibe `Usuario` por parámetro.

**Por qué:** el issue #48 documenta que conviven dos convenciones y que la A
(`Usuario` como parámetro, usada por `ServicioPrestamos`) solo es correcta si
todos sus llamadores obtienen el usuario con `requiere_sesion()` fresco antes de
cada llamada, cosa que nada verifica. Siendo este un archivo nuevo, B no cuesta
nada extra y evita escribir código que #48 ya planea reescribir. Además la
aprobación es justamente la operación donde la trampa de #48 más duele: es la
que compromete inventario.

**Fuera de alcance:** migrar `ServicioPrestamos` a B. Eso es #48.

---

## 2. Superficie pública

```python
ServicioSolicitudes(
    auth, repo_prestamos=None, repo_equipos=None, repo_usuarios=None,
    *, datos_dir=None, logger=None,
)

crear_solicitud(equipos, motivo, fecha_inicio, fecha_termino,
                *, fecha_solicitud=None) -> Prestamo
aprobar(id_solicitud, *, fecha_aprobacion=None) -> Prestamo
rechazar(id_solicitud, motivo) -> Prestamo
```

- **Cuatro colaboradores.** `repo_usuarios` es necesario porque
  `reglas._validar_aprobacion` exige un `solicitante: Usuario` y `ServicioAuth`
  solo sabe resolver al usuario *actual*. Debe ser la misma instancia que usa
  `auth`: `usuarios.py:60` documenta que si apuntan a archivos distintos, una
  baja lógica no invalida la sesión correspondiente.
- **Sin funciones envoltorio a nivel de módulo.** `usuarios.py` y `equipos.py`
  no las tienen; las de `prestamos.py` son el acompañamiento de la convención A.
- **Fechas inyectables** (`fecha_solicitud`, `fecha_aprobacion`) con
  `date.today()` por defecto, igual que `fecha_entrega`/`fecha_devolucion` en
  `prestamos.py`. No es estilo: RN-08 y RN-09 dependen enteramente de la
  relación entre hoy y la ventana pedida, y `sumar_dias_laborales` salta fines
  de semana, así que una ventana fija cambia de significado según el día en que
  corra la suite. `rechazar` no lleva fecha: no registra ninguna.
- **`motivo` posicional y obligatorio en `rechazar`**, porque la DoD dice que el
  rechazo lo exige.

**`cancelar` NO se mueve.** `docs/reglas-negocio.md` mapea RN-15 a
`servicios/solicitudes.py`, pero la cancelación ya está implementada y probada en
`prestamos.py:113` y era un ítem de la DoD del issue #12, cerrado. La fila del
documento está desactualizada, no el código. El corte real es: **`solicitudes.py`
es la fase de decisión (SOLICITADA → APROBADA/RECHAZADA); `prestamos.py` es la
fase de custodia, más la cancelación**, que abarca ambas porque T-04 y T-05
cancelan desde cualquiera de los dos estados.

---

## 3. `RESERVADO` y el relajamiento del chequeo escalar

### El problema

`_validar_equipos_y_disponibilidad` rechaza cualquier equipo cuyo
`estado is not EstadoEquipo.DISPONIBLE` (RN-05), y corre tanto al crear como al
**aprobar**. Si la aprobación escribe `RESERVADO`:

1. `S-0001` reserva `EQ-01` para el 10–14 de junio → `EQ-01` queda `RESERVADO`.
2. `S-0002` pide `EQ-01` para el 17–21 de junio — **sin solapamiento alguno**.
3. La aprobación de `S-0002` falla por RN-05.

La causa raíz: `Equipo.estado` es un **escalar**, pero una reserva es un **rango
de fechas**. Un solo campo no puede expresar "reservado la próxima semana, libre
esta".

### La decisión

`aprobar` **sí** escribe `RESERVADO`, y a cambio el chequeo escalar se relaja:

> El escalar bloquea **únicamente** `MANTENCION` y `BAJA`.
> `RESERVADO` y `PRESTADO` caen al bucle de solapamiento de fechas.

Esto le da a las dos reglas significados limpios y disjuntos:

| Regla | Significado |
| --- | --- |
| RN-05 (escalar) | el equipo está inutilizable, punto |
| RN-10 (bucle de fechas) | el equipo está tomado para estas fechas |

`MANTENCION` y `BAJA` son los únicos dos estados que son hechos atemporales
sobre el equipo y no sobre una reserva. Todo lo demás es consecuencia de un
`Prestamo`, y `solicitudes.json` es la autoridad sobre eso — que es la posición
que `equipos.py` ya defendía.

### Qué se permite exactamente

Cualquier ventana que no solape. Con una reserva del 10 al 14 de junio:

| Ventana pedida | Resultado | Motivo |
| --- | --- | --- |
| 5–9 jun | permitida | termina el día antes de que empiece la reserva |
| 5–10 jun | rechazada RN-10 | `hay_solapamiento` es inclusivo |
| 17–21 jun | permitida | empieza después de que termina la reserva |

No hace falta escribir ninguna regla de borde: `hay_solapamiento` ya es
inclusivo, así que "se puede prestar hasta el día anterior al inicio de la
reserva" **es** exactamente su comportamiento actual. Solo hay que dejar de
cortocircuitarlo con el escalar.

### Lo que no cambia

- `_validar_entrega` (RN-13) sigue bloqueando `PRESTADO`: la entrega es una
  transferencia física que ocurre *ahora*, y ahí el escalar es la fuente de
  verdad correcta.
- `ATRASADA` sigue bloqueando incondicionalmente en `equipo_disponible`: nadie
  sabe cuándo vuelve un equipo atrasado.
- La entrega sigue escribiendo `PRESTADO` y la devolución sigue disparando el
  recálculo.

### Costo aceptado

`Equipo.estado` deja de ser una señal confiable de "¿puedo reservar esto?".
`DISPONIBLE` ya no significa "sin reservas" y `PRESTADO` no significa
"no reservable". Se documenta en el docstring de `EstadoEquipo` en `modelos.py`
para que quien construya una UI de catálogo no lo asuma.

---

## 4. `reglas.estado_por_compromiso`: derivar, no mantener

```python
estado_por_compromiso(
    equipo, prestamos, *, prestamo_actual=None, fecha_actual=None
) -> EstadoEquipo
```

Escribir `RESERVADO` incrementalmente en cada evento exige que cinco puntos de
escritura repartidos en dos servicios respeten la misma invariante. Así
aparecieron los dos defectos que arregla esta rama:

1. **Dos reservas, una cancelada.** `_liberar_reservas` (`prestamos.py:333`)
   escribe `RESERVADO → DISPONIBLE` a ciegas, aunque otra reserva siga viva.
2. **Después de la devolución.** `_marcar_equipos(..., DISPONIBLE)` borra el
   `RESERVADO` que otra solicitud aprobada todavía justifica.
3. **Reserva vencida.** No existe transición de expiración, así que un equipo
   reservado y nunca retirado queda `RESERVADO` para siempre.

Una única función "dado este equipo, ¿qué dicen los préstamos vivos?" resuelve
las tres. Reutiliza `ESTADOS_DISPONIBILIDAD_BLOQUEADA`, la misma definición de
"comprometido" que ya comparten `reglas` y `equipos`.

**Dónde vive:** en `reglas.py`. No puede vivir en `solicitudes.py` ni en
`prestamos.py` porque ambos la llaman, y un servicio importando a su hermano es
una dependencia que el paquete `servicios/` hoy no tiene en ninguna parte.
`reglas.py` ya es dueño de los dos ingredientes y es deliberadamente libre de
repositorios.

**Reglas de precedencia:**

1. **Los estados administrativos no se sobrescriben nunca.** Si el equipo está
   en `MANTENCION` o `BAJA`, se devuelve tal cual. Son los únicos dos estados
   que siguen siendo compuertas reales; que una aprobación reactivara en
   silencio un equipo dado de baja sería un defecto de corrección, no cosmético.
2. **La custodia física manda sobre la reserva.** Si algún préstamo del equipo
   está `ENTREGADA` o `ATRASADA` → `PRESTADO`. Si no, pero alguno `APROBADA`
   todavía lo retiene → `RESERVADO`. Si no → `DISPONIBLE`.
3. **Las reservas vencidas dejan de contar** (`fecha_termino < hoy`). El
   préstamo sigue `APROBADA` en los datos —no hay transición de expiración—,
   esto solo afecta el valor derivado.

**Nota sobre la desactualización:** dado el relajamiento de la sección 3, un
`RESERVADO` obsoleto ya no puede provocar un rechazo incorrecto. Se verificó
que nada lo consulta: `equipos._exigir_sin_prestamo_activo` pregunta por
`solicitudes.json` y `ESTADOS_REACTIVABLES` (`equipos.py:49`) excluye a
propósito `RESERVADO`/`PRESTADO`. La corrección es de exactitud de los datos, no
de decisiones.

---

## 5. RN-22 — nadie aprueba su propia solicitud

Se agrega como regla numerada en `reglas._validar_aprobacion`, eliminando el
`del usuario`.

**Alcance:** solo la aprobación. Rechazar la propia solicitud es inofensivo:
equivale a cancelarla, cosa que RN-15 ya permite al solicitante.

**Comparación:** `normalizar_identificador` y `!=` sensible a mayúsculas sobre
`id`, igual que la corrección de RN-21 en `3a65156`. Los ids no se normalizan en
mayúsculas en ninguna otra parte del sistema.

**Nota sobre alcanzabilidad:** con roles estáticos esto es inalcanzable —
`_validar_usuario_operador` exige `SOLICITANTE` para T-01 y `ENCARGADO` para
T-02, y un `Usuario` tiene un solo rol. El camino real es la mutación de rol:
`usuarios.py:146 editar_usuario(..., rol=...)` puede promover a un solicitante.
La guarda cuesta dos líneas, hace verificable el ítem de la DoD y es defensiva
frente a la extensión futura donde los roles sean múltiples.

---

## 6. Generación de identificadores

`crear_solicitud` genera el id: secuencial con relleno de ceros, `S-0001`,
tomando el mayor sufijo numérico existente en el repositorio.

- **El servicio lo genera, no el llamador.** `json_repo.guardar` es un *upsert*:
  un id repetido **reemplaza** la solicitud existente en silencio. Con el id
  como parámetro, cada llamador puede provocar esa pérdida de datos; generándolo
  adentro, el chequeo de colisión vive en un solo lugar.
- **Secuencial y no UUID.** La persistencia es JSON versionado y legible, y el
  docstring de `guardar` dice explícitamente que la posición de inserción se
  elige para que "los diffs de los datos versionados sigan siendo legibles". Un
  UUID de 36 caracteres en cada registro pelea contra eso.
- **Prefijo `S-`**, que concuerda con `solicitudes.json` y con la transición que
  lo crea. Las pruebas existentes usan `P-01`, pero son fixtures a mano, no ids
  generados.
- **Verificación con `buscar()` antes de `guardar()`**, por si un
  `solicitudes.json` editado a mano rompe el barrido del sufijo máximo.

**Limitación documentada:** el barrido es O(n) y no es seguro con dos procesos
simultáneos — ambos calcularían el mismo id siguiente, y el chequeo con
`buscar()` también compite. Se acepta y se anota: `_escribir_atomico` ya acota
la historia de durabilidad al uso monoproceso. Es la instancia local del issue
abierto #49.

---

## 7. Orden de escritura

`aprobar` hace dos escrituras (el `Prestamo` y los `Equipo`) y `json_repo` no
tiene transacciones.

**Orden:** resolver equipos y solicitante → `validar_transicion` →
`guardar(prestamo_aprobado)` → derivar y escribir cada equipo, **pasando el
préstamo aprobado explícitamente** al helper.

Esto respeta el precedente de `registrar_devolucion`, que resuelve
`_equipos_de(prestamo)` antes de persistir nada para que un equipo inexistente
levante `RecursoNoEncontrado` con el préstamo intacto — fijado por
`test_servicio_prestamos.py:273`. Pasar el préstamo explícitamente evita que la
corrección del helper dependa de si la escritura ya aterrizó, y lo vuelve una
función pura, fácil de probar.

**Exposición residual aceptada:** si la escritura del equipo falla después de la
del préstamo, queda una solicitud `APROBADA` cuyos equipos siguen en
`DISPONIBLE`. Falla en la dirección segura: el compromiso *derivado* en
`solicitudes.json` es correcto, y es lo que realmente consultan
`equipos._exigir_sin_prestamo_activo` y `reglas.equipo_disponible`.

---

## 8. Registro de eventos (RN-18)

RN-18 nombra explícitamente estas operaciones: "crear solicitudes, aprobar,
rechazar". Se copia el helper privado `_evento` de `equipos.py:394`, incluido el
parámetro `logger` inyectable — `datos/logs/eventos.log` está versionado y una
suite que escriba ahí ensucia el diff en cada corrida.

Acciones: `solicitud_creada`, `solicitud_aprobada`, `solicitud_rechazada`, con
variantes `resultado="error"` en los caminos de rechazo, siguiendo el precedente
de `f413186` ("registrar también las operaciones sin cambio de estado").

**Fuera de alcance: #47**, que `ServicioPrestamos` no registre eventos. Es un
defecto real y ya está trazado, pero arreglarlo implica agregar el parámetro
`logger` al constructor, pasarlo por seis métodos públicos y reapuntar las
pruebas de ese servicio: churn de firmas sobre un issue cerrado que inundaría
este diff.

**No se extrae `_evento` a una base común.** Con tres sitios de llamada y #48 ya
en cola para reestructurar cómo los servicios obtienen su actor, deduplicar
antes de esa decisión sería probablemente la abstracción equivocada.

---

## 9. Pruebas

**Nombres descriptivos, sin prefijo `CP`.** `conftest.py` prescribe
`test_CPxx_RFxx_...`, pero `test_servicio_prestamos.py` —el hermano más cercano,
de un issue entregado— usa nombres descriptivos. Las pruebas unitarias de un
servicio no son casos del catálogo; las nombradas con CP viven en
`tests/funcionales/`.

### `tests/unidad/test_servicio_solicitudes.py` (nuevo)

Los cinco ítems de la DoD más el ciclo de vida de `RESERVADO`, y el par de
solapamiento:

- `EQ-01` `RESERVADO` por `S-0001` (10–14 jun); crear y aprobar `S-0002` para
  17–21 jun → **éxito**, `EQ-01` sigue `RESERVADO`.
- La misma situación con `S-0003` para 12–16 jun → rechazo con
  `regla == "RN-10"`.

La primera falla hoy por el motivo equivocado (RN-05, escalar) y debe pasar
después: es la prueba más clara de que el relajamiento aterrizó.

### `tests/unidad/test_reglas.py`

- RN-22 (aprobar la propia solicitud).
- La compuerta escalar relajada.
- **La tríada de borde:** contra una reserva del 10–14 jun → `5–9` permitida,
  `5–10` rechazada, `17–21` permitida. Ese borde inclusivo es la regla entera y
  debe fallar ruidosamente si alguien vuelve a apretar el escalar.
- Precedencia de `estado_por_compromiso`.

### `tests/unidad/test_servicio_prestamos.py`

**Corrección al inventario inicial:** las tres fixtures que siembran `RESERVADO`
a mano (`:334`, `:354`, `:443`) **no cambian**. Se verificó cada una contra el
comportamiento nuevo: en `:334` el único préstamo queda `CANCELADA` y no quedan
compromisos → `DISPONIBLE`; en `:354` la operación falla y nunca se escribe un
equipo; `:443` solo cuenta llamadas al motor. Pasan sin tocarlas — las siembras
se vuelven *retroactivamente realistas*, porque ahora la aprobación sí produce
ese estado. Solo se refrescan los comentarios.

**El hueco real:** todas las pruebas del archivo son un préstamo contra un
equipo. Nada fallaría si el helper se implementara mal. Se agregan seis:

| # | Prueba | Estado hoy |
| --- | --- | --- |
| 1 | Cancelar con una segunda reserva viva → sigue `RESERVADO` | **falla** (defecto 1) |
| 2 | Devolver con una reserva futura pendiente → `RESERVADO` | **falla** (defecto 2) |
| 3 | Custodia sobre reserva: cancelar la futura con una entregada → sigue `PRESTADO` | caracterización |
| 4 | Devolución no resucita `MANTENCION`/`BAJA` | caracterización |
| 5 | Reserva vencida deja de contar → `DISPONIBLE` | caracterización |
| 6 | Entrega de `S-0002` (10–14 jun) con `EQ-01` `RESERVADO` por `S-0001` (20–24 jun) → éxito, `PRESTADO` | pasa hoy |

1 y 2 son rojo-antes-de-verde. 3–5 son caracterización de decisiones que si no
solo existen en esta conversación. 6 encadena con 2: devolver `S-0002` el 14 de
junio con `S-0001` todavía `APROBADA` y sin vencer debe dar `RESERVADO`, así que
una sola fixture ejercita entrega-sobre-reserva y precedencia-en-devolución en
secuencia.

**`registrar_entrega` no pasa por el helper**: escribir `PRESTADO`
incondicionalmente ya es correcto bajo la regla de precedencia, y
`_validar_entrega` bloquea `MANTENCION`/`BAJA` antes de la escritura. Pasarlo
por el helper agregaría un barrido del repositorio por entrega para calcular una
respuesta que ya conocemos.

---

## 10. Documentación

- `docs/reglas-negocio.md`: columna de módulo responsable en RN-05, RN-06, RN-11
  y RN-15 (las cuatro apuntan a `solicitudes.py` cosas que viven en `reglas.py`,
  `modelos.py` y `prestamos.py`), más una fila nueva para RN-22.
- `docs/estados-transiciones.md:112`: la condición "El estado operativo del
  equipo es `disponible`" es justamente la compuerta que se relaja. Su tabla de
  estados bloqueantes (líneas 122–132) no cambia, porque ya está expresada en
  términos de estados del *préstamo* y no del equipo — evidencia adicional de
  que el modelo derivado es el que el contrato pretendía.
- `modelos.py`: docstring de `EstadoEquipo` (sección 3, costo aceptado).
- `equipos.py:328` y `test_servicio_equipos.py:8,259`: comentarios que prometen
  que #11 escribirá `RESERVADO`; ahora lo hace, pero sin que el escalar sea la
  autoridad.

**Las columnas `CP` no se tocan.** `docs/casos-de-prueba.md` define CP-01 a
CP-15, y de CP-07 en adelante son filas vacías reservadas por *tipo* (borde,
negativo, combinación, escenario) para los issues #17/#18/#19. La columna de
`reglas-negocio.md` asigna dos CP por regla de forma secuencial hasta CP-34, lo
que choca de frente con esa reserva por tipo. Renumerar exige reconciliar
#17/#18/#19, #23 y #24 en una sola pasada coherente: es trabajo de #43.

**Comentario en #43** corrigiendo su alcance: el rango colgante real es
**CP-16 a CP-34** (19 ids, RN-09 a RN-19), no los seis que enumera en RN-11,
RN-17 y RN-18.

---

## 11. Plan de commits

| # | Commit | Contenido |
| --- | --- | --- |
| 1 | `feat(reglas): derivar el estado del equipo desde los compromisos vigentes` | `estado_por_compromiso` + compuerta relajada + pruebas |
| 2 | `feat(reglas): impedir que un encargado apruebe su propia solicitud (RN-22)` | guarda RN-22 + pruebas |
| 3 | `feat(solicitudes): crear, aprobar y rechazar solicitudes de prestamo` | el servicio + `test_servicio_solicitudes.py` |
| 4 | `fix(prestamos): liberar equipos segun los compromisos restantes` | los dos sitios de llamada + las seis pruebas nuevas |
| 5 | `docs(reglas): corregir modulos responsables y documentar RN-22` | sección 10 |

El orden importa: 1 y 2 son cambios del motor de los que 3 depende, y 4 no puede
aterrizar antes de que 1 exista. Separar 1 de 2 mantiene la guarda RN-22
revisable por sí sola. Suite completa después de 1, 3 y 4, porque 1 y 4 tocan
código del que dependen dos issues cerrados.

El commit 4 es un `fix` sobre un archivo de un issue cerrado (#12). Se integra
en esta rama sin abrir un defecto previo, por decisión explícita: esta rama es
la que vuelve real a `RESERVADO`, y entregar un estado que nadie escribía junto
con dos funciones que lo manejan mal dejaría un defecto que `git blame` atribuye
a este trabajo.
