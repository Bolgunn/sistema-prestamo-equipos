# Declaracion de uso de Inteligencia Artificial

Se evalua negativamente el uso no declarado o acritico de IA.

Este documento declara el uso de asistentes de IA en el proyecto. El criterio de
trabajo del equipo fue **asistido por IA, conducido por humanos**: las decisiones
de diseno, de proceso y de negocio se tomaron y se respondieron una por una antes
de escribir codigo, y la IA actuo como ejecutor y redactor.

Toda afirmacion de esta declaracion se apoya en commits del repositorio, que son
verificables con `git show <hash>`. Cuando se cita una sesion de trabajo se
indica su fecha y hora UTC; esos registros son locales de cada maquina y no
forman parte del repositorio (ver `cb6ed4d`).

## 1. Herramientas utilizadas y en que actividades

Herramientas y versiones:

| Integrante | Producto | Version | Modelo | Entorno |
| --- | --- | --- | --- | --- |
| Integrante 1 (B. Olguin) | Claude Code | 2.1.260 y 2.1.247 | claude-opus-5 | Aplicacion de escritorio (`claude-desktop`) |
| Integrante 2 (Isaias) | Codex CLI | _por confirmar_ (`codex --version`) | GPT-5.5 | Terminal |

Uso por actividad. La columna **Uso de IA** distingue tres grados: `asistido`
(la IA propuso o escribio el artefacto), `redaccion asistida` (la decision fue
humana y la IA redacto el texto que la documenta) y `no usado`.

| Herramienta | Actividad | Integrante | Uso de IA | Evidencia |
| --- | --- | --- | --- | --- |
| Claude Code | Estructura inicial y plantillas de documentacion | 1 | asistido | `c1962b8` |
| Claude Code | Modelos de dominio (Usuario, Equipo, Prestamo) | 1 | asistido | `70043a4` (sin trailer; ver seccion 6) |
| Claude Code | Persistencia JSON con escritura atomica | 1 | asistido | `68cd52b` |
| Claude Code | Autenticacion local y control de acceso por rol | 1 | asistido | `c2a2fd8`, `64fd18e` |
| Claude Code | Gestion de usuarios y equipos (RN-03, RN-04, RN-20, RN-21) | 1 | asistido | `1d7125b`, `d59e1f9`, `3a65156` |
| Claude Code | Solicitudes, aprobacion y rechazo (RN-22) | 1 | asistido | `022c4c7`, `db9f161`, `620f0c0` |
| Claude Code | Documentacion de reglas de negocio y estados | 1 | asistido | `8803781`, `1f700a3`, `7f25fd1` |
| Claude Code | Pruebas negativas y combinadas (CP-10 a CP-15) | 1 | asistido | `f4e747a`, `d23904d` |
| Claude Code | Documento de trabajo colaborativo y grafo de dependencias | 1 | redaccion asistida | `765f4a9`, `9c0a88d`, `9b726aa` |
| Codex CLI | Motor de reglas, transiciones y guardas | 2 | asistido | `ebb887d` |
| Codex CLI | Entrega, devolucion y cancelacion de prestamos | 2 | asistido | `034aca9`, `46983d4` |
| Codex CLI | Consultas de prestamos por estado | 2 | asistido | `3fa43fb` |
| Codex CLI | Observabilidad, logs y Sentry | 2 | asistido | `48d44f1`, `16754cb` |
| Codex CLI | CLI, subcomandos y menu interactivo | 2 | asistido | `304621b` |
| Codex CLI | Datos demo reproducibles e `init-demo` | 2 | asistido | `393c303` |
| Codex CLI | Pruebas funcionales y de borde (CP-01 a CP-09) | 2 | asistido | `538c476`, `4573cc9` |
| Codex CLI | Formalizacion de `develop` y reglas de commits/PR | 2 | redaccion asistida | `e9265a9`, `e99b773` |
| Ninguna | Decisiones de proceso (flujo Git, reparto del trabajo, alcance de issues) | 1 y 2 | **no usado** | ver seccion 5 |
| Ninguna | Revision cruzada de la funcionalidad del companero (#20, #21) | 1 y 2 | **no usado** | `c441596`, `79052c9`, `6593fe4` |
| Ninguna | Exclusion de contextos de IA del control de versiones | 1 | **no usado** | `cb6ed4d` |

Los commits del Integrante 1 asistidos por IA llevan el trailer
`Co-Authored-By: Claude Opus 5`. Los del Integrante 2 no llevan trailer: su uso
de Codex se declara aqui por el propio integrante, y la evidencia disponible son
los commits, no una marca automatica. Esta asimetria de evidencia se discute en
la seccion 6.

## 2. Dos ejemplos relevantes de prompts

Los dos prompts se transcriben literalmente desde los registros de sesion,
incluidos los errores de tipeo y la mezcla de ingles y espanol.

### Prompt 1

Prompt recurrente de inicio de cada issue. Se uso 8 veces entre el 2026-09-05 y
el 2026-09-07, 5 de ellas en esta forma exacta (issues #7, #10, #11, #18 y #26):

```text
/grill-me lets work on issue #10, change the branch to the corresponding one for this issue and merge the develop into it
```

`/grill-me` no es una funcion del modelo: es una instruccion propia del equipo,
guardada como archivo local, cuyo texto completo es:

> Interview me relentlessly about every aspect of this plan until we reach a
> shared understanding. Walk down each branch of the design tree, resolving
> dependencies between decisions one-by-one. For each question, provide your
> recommended answer. Ask the questions one at a time. If a question can be
> answered by exploring the codebase, explore the codebase instead.

El efecto es invertir el rol habitual: en vez de pedir codigo, se obliga a la IA
a interrogar al humano y a resolver el arbol de decisiones **antes** de escribir
nada, una pregunta a la vez y explorando el repositorio en lugar de suponer.

Por que es relevante: es el mecanismo concreto por el que el uso fue conducido
por humanos. Las respuestas registradas en las sesiones son decisiones de diseno
tomadas por el integrante, no aprobaciones genericas. Por ejemplo:
`"(A), and BAJA is reversible"`, `"b, tuple and the coller supplies it"`,
`"no decorator, plain methods is fine"`, `"i want both case insensitive"`,
`"B, don't migrate ServicioPrestamos in this issue"`.

Esta misma declaracion (issue #26) se elaboro con este prompt.

### Prompt 2

Cadena de tres prompts del 2026-09-06 en la rama `feat/solicitudes`, sobre la
regla de un equipo en estado RESERVADO (issue #11):

```text
21:26  i want the estadoequipo.reservado to permit the lending but only until a date before the reserve
21:53  inventory looks complete, fold commit 4 in as-is. Before implementing i want to know the test we are doing to sercvicio prestamos and if there anything else we can add to it
21:55  all five, in test_servicio_prestamos.py. also do a test that something reserved can be lend if the lending date doesnt overlap with the reserve
```

Por que es relevante: muestra los tres roles separados en una sola tarea. El
humano **fija la regla de negocio** (un equipo reservado si puede prestarse
mientras la ventana no se solape), luego **exige el inventario de pruebas
existentes antes de permitir la implementacion**, y finalmente **agrega un caso
de prueba propio** que la IA no habia propuesto. La IA implemento; no decidio.
Resultado en `022c4c7` y `620f0c0`.

## 3. Resultados aceptados, modificados o descartados

| Resultado | Decision | Justificacion | Evidencia |
| --- | --- | --- | --- |
| Repositorio JSON generico con escritura atomica | Aceptado tras revision | La propuesta de escribir en archivo temporal y reemplazar de forma atomica resolvia el riesgo de corrupcion por escritura parcial; se acepto sin cambios de fondo. | `68cd52b` |
| Autenticacion local con hash de contrasena y sal | Aceptado tras revision, corregido despues | Se acepto el diseno, pero la revision del PR detecto que no se validaba el largo de sal y digest al descomponer el hash. Se corrigio con criterio explicito del integrante (piso para la sal, exacto para el digest). | `c2a2fd8`, `64fd18e` |
| Comparacion sensible a mayusculas del campo `correo` | Modificado | La IA propuso tratar `id` y `correo` con criterios distintos. Al preguntar por que `correo` era sensible a mayusculas no hubo justificacion de negocio, y se impuso que ambos fueran insensibles. | `3a65156` |
| Manejo del estado RESERVADO en el prestamo | Modificado | La propuesta bloqueaba el prestamo de todo equipo reservado. El integrante impuso la regla real: se permite mientras las ventanas de fecha no se solapen. | `022c4c7`, `620f0c0` |
| Edicion de `docs/matriz-trazabilidad.md` durante el issue #11 | Descartado | La IA modifico un documento fuera del alcance del issue. Se revirtio: el cambio no correspondia a esa rama. | Sesion 2026-09-06 22:17 UTC |
| `git push --force-with-lease` sobre `feat/persistencia-json` | Descartado | La IA propuso reescribir una rama ya publicada en el remoto. Se rechazo por ser una operacion destructiva sobre trabajo compartido y se resolvio sin forzar. | Sesion 2026-09-06 03:27 UTC |
| Omision del trailer de coautoria en un commit | Descartado a posteriori | Fue una instruccion del propio integrante, no una propuesta de la IA. Se revirtio como practica y se declara en la seccion 6. | `70043a4` |

## 4. Como se verificaron las respuestas

No se verifico cada respuesta de forma individual: afirmarlo seria falso. Lo que
se sostiene es que **toda salida de IA que llego al repositorio atraveso cuatro
controles**, y se declara ademas cual de ellos detecto defectos reales.

1. **Diseno previo al codigo.** El prompt `/grill-me` (seccion 2) obligo a
   resolver el arbol de decisiones antes de implementar. El control es
   preventivo: reduce el margen de la IA para inventar requisitos, porque las
   ambiguedades se resuelven con una respuesta humana explicita y registrada.
2. **Suite automatizada.** 303 pruebas (302 pasan, 1 `xfail` estricto) sobre
   servicios reales y repositorios JSON temporales. Se ejecutan localmente y en
   integracion continua (`.github/workflows/pruebas.yml`) en cada Pull Request.
3. **Revision por pares en Pull Request.** La integracion se hace solo por PR
   (29 hasta la fecha). La revision humana detecto defectos que la suite no vio;
   el caso mas claro es la validacion de largo de sal y digest, planteada como
   comentario de PR y corregida en `64fd18e`.
4. **Pruebas cruzadas sin IA.** En los issues #20 y #21 cada integrante probo la
   funcionalidad del otro escribiendo casos nuevos e independientes, sin
   asistencia de IA.

**Hallazgo principal:** las dos actividades realizadas **sin** IA son las que
encontraron los defectos abiertos del proyecto. DEF-01 salio de la revision
documental de reglas contra casos de prueba, y DEF-02 (las mutaciones de
prestamos no registran los eventos de auditoria que exige RN-18) salio de la
revision cruzada del Integrante 1 sobre el codigo del Integrante 2, y quedo
fijado con un `xfail(strict=True)` en
`tests/cruzadas/test_integrante_1_revisa_integrante_2.py`. Ambos estan
registrados en `docs/defectos.md` y como issues (#43, #47).

La lectura critica de esto es incomoda y se declara igual: los controles
automatizados estaban en verde mientras esos defectos existian. La suite
verifica lo que se le pidio verificar, y lo que se le pidio verificar tambien se
escribio con asistencia de IA. El control que aporto informacion nueva fue el
humano.

## 5. Decisiones que NO se delegaron a IA

Se distingue entre **tomar la decision** y **redactar el documento que la
describe**. Las decisiones siguientes fueron humanas; parte de su redaccion fue
asistida, y eso esta declarado como `redaccion asistida` en la seccion 1.

- **Flujo de trabajo Git.** Se eligio primero GitHub Flow y luego se cambio a un
  GitFlow simplificado con `develop` como rama de integracion, por friccion real
  al trabajar en paralelo. El cambio lo formalizo el Integrante 2 (`e9265a9`).
- **Reparto del trabajo por rebanada vertical** en lugar de por capa, para que
  cada integrante pudiera terminar funcionalidad completa sin bloquearse.
- **Alcance de cada issue**, incluida la decision repetida de diferir trabajo a
  un issue posterior en vez de ampliar el actual.
- **Reglas de negocio.** La ventana no solapada del estado RESERVADO, la
  reversibilidad de la baja, la insensibilidad a mayusculas de `id` y `correo`,
  y la prohibicion de que un encargado apruebe su propia solicitud (RN-22).
- **Juicios de la revision cruzada** (#20 y #21): que probar del modulo del
  companero, que considerar defecto y con que severidad.
- **Rechazo de operaciones riesgosas**, en particular el `push --force` sobre
  una rama compartida (seccion 3).

## 6. Limitaciones o recomendaciones dudosas detectadas

### 6.1 Limitaciones de la herramienta

1. **Recomendo una operacion destructiva sobre trabajo compartido.** El
   2026-09-06 a las 03:27 UTC la IA propuso `git push --force-with-lease` sobre
   `feat/persistencia-json`, una rama ya publicada, para resolver que el remoto
   apuntaba al scaffold inicial. El razonamiento tecnico era correcto, pero la
   recomendacion habria reescrito historia compartida. Se rechazo y se resolvio
   sin forzar. Es la recomendacion mas dudosa del proyecto: plausible en la
   forma, riesgosa en el efecto.
2. **Modifico archivos fuera del alcance del issue.** Durante el issue #11 edito
   `docs/matriz-trazabilidad.md`, que no correspondia a esa rama. Se revirtio.
   La IA no delimita sola el alcance de un cambio; hay que revisarlo.
3. **Produjo un diseno internamente incoherente.** Propuso comparar `id` sin
   distinguir mayusculas y `correo` distinguiendolas, sin justificacion de
   negocio. Se detecto preguntando por que, no leyendo el codigo.

### 6.2 Limitaciones de nuestro propio proceso de uso

Estas son fallas del equipo, no de la herramienta, y se declaran porque son
verificables y afectan a la evidencia de este mismo documento.

4. **Se suprimio deliberadamente la declaracion de coautoria en un commit.** El
   2026-09-06 a las 01:35 UTC el Integrante 1 instruyo explicitamente
   `"commit and open the PR (dont credit claude on the messages or comments)"`.
   El commit resultante es `70043a4` (`feat(modelos)`), que fue asistido por IA y
   no lleva trailer. Fue un caso unico, se corrigio de inmediato en los commits
   siguientes, y se declara aqui porque el enunciado penaliza el uso **no
   declarado**: la deteccion se hizo auditando nuestro propio historial al
   redactar este documento.
5. **El conteo de trailers es una cota inferior, no un censo.** 23 commits
   llevan `Co-Authored-By: Claude Opus 5`, pero por el punto anterior el uso real
   de IA fue mayor. La declaracion autorizada del uso es la tabla de la seccion
   1, no el conteo de trailers.
6. **La higiene de contextos de IA se aplico a una sola herramienta.**
   `.gitignore` excluye `.claude/` (`cb6ed4d`) pero no `.codex/` ni `AGENTS.md`.
   La regla protege el entorno del Integrante 1 y no el del Integrante 2. La
   evidencia de uso de IA quedo por eso asimetrica: automatica y verificable de
   un lado, declarada por el integrante del otro.
7. **La integracion continua no cubre la rama de integracion.**
   `.github/workflows/pruebas.yml` ejecuta `pytest` en cada Pull Request y en
   push a `main`, pero no en push a `develop`. Como `develop` es justamente donde
   se integra el trabajo de ambos, un push directo a esa rama no queda cubierto
   por el control automatizado descrito en la seccion 4.
