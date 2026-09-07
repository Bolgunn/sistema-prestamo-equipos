# Declaración de uso de Inteligencia Artificial

Se evalúa negativamente el uso no declarado o acrítico de IA.

Este documento declara el uso de asistentes de IA en el proyecto. El criterio de
trabajo del equipo fue **asistido por IA, conducido por humanos**: las decisiones
de diseño, de proceso y de negocio se tomaron y se respondieron una por una antes
de escribir código, y la IA actuó como ejecutor y redactor.

Toda afirmación de esta declaración se apoya en commits del repositorio, que son
verificables con `git show <hash>`. Cuando se cita una sesión de trabajo se
indica su fecha y hora UTC; esos registros son locales de cada máquina y no
forman parte del repositorio (ver `cb6ed4d`).

## 1. Herramientas utilizadas y en qué actividades

Herramientas y versiones:

| Integrante | Producto | Versión | Modelo | Entorno |
| --- | --- | --- | --- | --- |
| Integrante 1 (B. Olguin) | Claude Code | 2.1.260 y 2.1.247 | claude-opus-5 | Aplicación de escritorio (`claude-desktop`) |
| Integrante 2 (Isaías) | Codex CLI | _por confirmar_ (`codex --version`) | GPT-5.5 | Terminal |

Uso por actividad. La columna **Uso de IA** distingue tres grados: `asistido`
(la IA propuso o escribió el artefacto), `redacción asistida` (la decisión fue
humana y la IA redactó el texto que la documenta) y `no usado`.

| Herramienta | Actividad | Integrante | Uso de IA | Evidencia |
| --- | --- | --- | --- | --- |
| Claude Code | Estructura inicial y plantillas de documentación | 1 | asistido | `c1962b8` |
| Claude Code | Modelos de dominio (Usuario, Equipo, Prestamo) | 1 | asistido | `70043a4` (sin trailer; ver sección 6) |
| Claude Code | Persistencia JSON con escritura atómica | 1 | asistido | `68cd52b` |
| Claude Code | Autenticación local y control de acceso por rol | 1 | asistido | `c2a2fd8`, `64fd18e` |
| Claude Code | Gestión de usuarios y equipos (RN-03, RN-04, RN-20, RN-21) | 1 | asistido | `1d7125b`, `d59e1f9`, `3a65156` |
| Claude Code | Solicitudes, aprobación y rechazo (RN-22) | 1 | asistido | `022c4c7`, `db9f161`, `620f0c0` |
| Claude Code | Documentación de reglas de negocio y estados | 1 | asistido | `8803781`, `1f700a3`, `7f25fd1` |
| Claude Code | Pruebas negativas y combinadas (CP-10 a CP-15) | 1 | asistido | `f4e747a`, `d23904d` |
| Claude Code | Documento de trabajo colaborativo y grafo de dependencias | 1 | redacción asistida | `765f4a9`, `9c0a88d`, `9b726aa` |
| Codex CLI | Motor de reglas, transiciones y guardas | 2 | asistido | `ebb887d` |
| Codex CLI | Entrega, devolución y cancelación de préstamos | 2 | asistido | `034aca9`, `46983d4` |
| Codex CLI | Consultas de préstamos por estado | 2 | asistido | `3fa43fb` |
| Codex CLI | Observabilidad, logs y Sentry | 2 | asistido | `48d44f1`, `16754cb` |
| Codex CLI | CLI, subcomandos y menú interactivo | 2 | asistido | `304621b` |
| Codex CLI | Datos demo reproducibles e `init-demo` | 2 | asistido | `393c303` |
| Codex CLI | Pruebas funcionales y de borde (CP-01 a CP-09) | 2 | asistido | `538c476`, `4573cc9` |
| Codex CLI | Formalización de `develop` y reglas de commits/PR | 2 | redacción asistida | `e9265a9`, `e99b773` |
| Ninguna | Decisiones de proceso (flujo Git, reparto del trabajo, alcance de issues) | 1 y 2 | **no usado** | ver sección 5 |
| Ninguna | Revisión cruzada de la funcionalidad del Integrante 2 (#20) | 1 | **no usado** | `c441596`, `79052c9` |
| Codex CLI | Revisión cruzada de la funcionalidad del Integrante 1 (#21) | 2 | asistido | `6593fe4` |
| Ninguna | Exclusión de contextos de IA del control de versiones | 1 | **no usado** | `cb6ed4d` |

Los commits del Integrante 1 asistidos por IA llevan el trailer
`Co-Authored-By: Claude Opus 5`. Los del Integrante 2 no llevan trailer: su uso
de Codex se declara aquí por el propio integrante, y la evidencia disponible son
los commits, no una marca automática. Esta asimetría de evidencia se discute en
la sección 6.

## 2. Dos ejemplos relevantes de prompts

Los dos prompts se transcriben literalmente desde los registros de sesión,
incluidos los errores de tipeo y la mezcla de inglés y español.

### Prompt 1

Prompt recurrente de inicio de cada issue. Se usó 8 veces entre el 2026-09-05 y
el 2026-09-07, 5 de ellas en esta forma exacta (issues #7, #10, #11, #18 y #26):

```text
/grill-me lets work on issue #10, change the branch to the corresponding one for this issue and merge the develop into it
```

`/grill-me` no es una función del modelo: es una instrucción propia del equipo,
guardada como archivo local, cuyo texto completo es:

> Interview me relentlessly about every aspect of this plan until we reach a
> shared understanding. Walk down each branch of the design tree, resolving
> dependencies between decisions one-by-one. For each question, provide your
> recommended answer. Ask the questions one at a time. If a question can be
> answered by exploring the codebase, explore the codebase instead.

El efecto es invertir el rol habitual: en vez de pedir código, se obliga a la IA
a interrogar al humano y a resolver el árbol de decisiones **antes** de escribir
nada, una pregunta a la vez y explorando el repositorio en lugar de suponer.

Por qué es relevante: es el mecanismo concreto por el que el uso fue conducido
por humanos. Las respuestas registradas en las sesiones son decisiones de diseño
tomadas por el integrante, no aprobaciones genéricas. Por ejemplo:
`"(A), and BAJA is reversible"`, `"b, tuple and the coller supplies it"`,
`"no decorator, plain methods is fine"`, `"i want both case insensitive"`,
`"B, don't migrate ServicioPrestamos in this issue"`.

Esta misma declaración (issue #26) se elaboró con este prompt.

### Prompt 2

Cadena de tres prompts del 2026-09-06 en la rama `feat/solicitudes`, sobre la
regla de un equipo en estado RESERVADO (issue #11):

```text
21:26  i want the estadoequipo.reservado to permit the lending but only until a date before the reserve
21:53  inventory looks complete, fold commit 4 in as-is. Before implementing i want to know the test we are doing to sercvicio prestamos and if there anything else we can add to it
21:55  all five, in test_servicio_prestamos.py. also do a test that something reserved can be lend if the lending date doesnt overlap with the reserve
```

Por qué es relevante: muestra los tres roles separados en una sola tarea. El
humano **fija la regla de negocio** (un equipo reservado sí puede prestarse
mientras la ventana no se solape), luego **exige el inventario de pruebas
existentes antes de permitir la implementación**, y finalmente **agrega un caso
de prueba propio** que la IA no había propuesto. La IA implementó; no decidió.
Resultado en `022c4c7` y `620f0c0`.

## 3. Resultados aceptados, modificados o descartados

| Resultado | Decisión | Justificación | Evidencia |
| --- | --- | --- | --- |
| Repositorio JSON genérico con escritura atómica | Aceptado tras revisión | La propuesta de escribir en archivo temporal y reemplazar de forma atómica resolvía el riesgo de corrupción por escritura parcial; se aceptó sin cambios de fondo. | `68cd52b` |
| Autenticación local con hash de contraseña y sal | Aceptado tras revisión, corregido después | Se aceptó el diseño, pero la revisión del PR detectó que no se validaba el largo de sal y digest al descomponer el hash. Se corrigió con criterio explícito del integrante (piso para la sal, exacto para el digest). | `c2a2fd8`, `64fd18e` |
| Comparación sensible a mayúsculas del campo `correo` | Modificado | La IA propuso tratar `id` y `correo` con criterios distintos. Al preguntar por qué `correo` era sensible a mayúsculas no hubo justificación de negocio, y se impuso que ambos fueran insensibles. | `3a65156` |
| Manejo del estado RESERVADO en el préstamo | Modificado | La propuesta bloqueaba el préstamo de todo equipo reservado. El integrante impuso la regla real: se permite mientras las ventanas de fecha no se solapen. | `022c4c7`, `620f0c0` |
| Edición de `docs/matriz-trazabilidad.md` durante el issue #11 | Descartado | La IA modificó un documento fuera del alcance del issue. Se revirtió: el cambio no correspondía a esa rama. | Sesión 2026-09-06 22:17 UTC |
| `git push --force-with-lease` sobre `feat/persistencia-json` | Descartado | La IA propuso reescribir una rama ya publicada en el remoto. Se rechazó por ser una operación destructiva sobre trabajo compartido y se resolvió sin forzar. | Sesión 2026-09-06 03:27 UTC |
| Omisión del trailer de coautoría en un commit | Descartado a posteriori | Fue una instrucción del propio integrante, no una propuesta de la IA. Se revirtió como práctica en los commits siguientes. | `70043a4` |

## 4. Cómo se verificaron las respuestas

No se verificó cada respuesta de forma individual: afirmarlo sería falso. Lo que
se sostiene es que **toda salida de IA que llegó al repositorio atravesó cuatro
controles**, y se declara además cuál de ellos detectó defectos reales.

1. **Diseño previo al código.** El prompt `/grill-me` (sección 2) obligó a
   resolver el árbol de decisiones antes de implementar. El control es
   preventivo: reduce el margen de la IA para inventar requisitos, porque las
   ambigüedades se resuelven con una respuesta humana explícita y registrada.
2. **Suite automatizada.** 303 pruebas (302 pasan, 1 `xfail` estricto) sobre
   servicios reales y repositorios JSON temporales. Se ejecutan localmente y en
   integración continua (`.github/workflows/pruebas.yml`) en cada Pull Request.
3. **Revisión por pares en Pull Request.** La integración se hace solo por PR
   (29 hasta la fecha). La revisión humana detectó defectos que la suite no vio;
   el caso más claro es la validación de largo de sal y digest, planteada como
   comentario de PR y corregida en `64fd18e`.
4. **Pruebas cruzadas.** En los issues #20 y #21 cada integrante probó la
   funcionalidad del otro escribiendo casos nuevos e independientes. El grado de
   asistencia no fue el mismo en ambos: el #20 se escribió sin IA, y el #21 se
   implementó con Codex CLI a partir de un prompt definido por el Integrante 2,
   que también generó la evidencia y actualizó la documentación.

**Hallazgo principal:** los dos defectos abiertos del proyecto salieron de
actividades realizadas **sin** IA. DEF-01 salió de la revisión
documental de reglas contra casos de prueba, y DEF-02 (las mutaciones de
préstamos no registran los eventos de auditoría que exige RN-18) salió de la
revisión cruzada del Integrante 1 sobre el código del Integrante 2, y quedó
fijado con un `xfail(strict=True)` en
`tests/cruzadas/test_integrante_1_revisa_integrante_2.py`. Ambos están
registrados en `docs/defectos.md` y como issues (#43, #47).

La lectura crítica de esto es incómoda y se declara igual: los controles
automatizados estaban en verde mientras esos defectos existían. La suite
verifica lo que se le pidió verificar, y lo que se le pidió verificar también se
escribió con asistencia de IA. El control que aportó información nueva fue el
humano.

## 5. Decisiones que NO se delegaron a IA

Se distingue entre **tomar la decisión** y **redactar el documento que la
describe**. Las decisiones siguientes fueron humanas; parte de su redacción fue
asistida, y eso está declarado como `redacción asistida` en la sección 1.

- **Flujo de trabajo Git.** Se eligió primero GitHub Flow y luego se cambió a un
  GitFlow simplificado con `develop` como rama de integración, por fricción real
  al trabajar en paralelo. El cambio lo formalizó el Integrante 2 (`e9265a9`).
- **Reparto del trabajo por rebanada vertical** en lugar de por capa, para que
  cada integrante pudiera terminar funcionalidad completa sin bloquearse.
- **Alcance de cada issue**, incluida la decisión repetida de diferir trabajo a
  un issue posterior en vez de ampliar el actual.
- **Reglas de negocio.** La ventana no solapada del estado RESERVADO, la
  reversibilidad de la baja, la insensibilidad a mayúsculas de `id` y `correo`,
  y la prohibición de que un encargado apruebe su propia solicitud (RN-22).
- **Juicios de la revisión cruzada** (#20 y #21): qué probar del módulo del
  compañero, qué considerar defecto y con qué severidad. En el #21 la
  implementación fue asistida, pero el criterio de qué revisar lo definió el
  Integrante 2 en el prompt; en el #20 no hubo asistencia.
- **Rechazo de operaciones riesgosas**, en particular el `push --force` sobre
  una rama compartida (sección 3).

## 6. Limitaciones o recomendaciones dudosas detectadas

### 6.1 Limitaciones de la herramienta

1. **Recomendó una operación destructiva sobre trabajo compartido.** El
   2026-09-06 a las 03:27 UTC la IA propuso `git push --force-with-lease` sobre
   `feat/persistencia-json`, una rama ya publicada, para resolver que el remoto
   apuntaba al scaffold inicial. El razonamiento técnico era correcto, pero la
   recomendación habría reescrito historia compartida. Se rechazó y se resolvió
   sin forzar. Es la recomendación más dudosa del proyecto: plausible en la
   forma, riesgosa en el efecto.
2. **Modificó archivos fuera del alcance del issue.** Durante el issue #11 editó
   `docs/matriz-trazabilidad.md`, que no correspondía a esa rama. Se revirtió.
   La IA no delimita sola el alcance de un cambio; hay que revisarlo.
3. **Produjo un diseño internamente incoherente.** Propuso comparar `id` sin
   distinguir mayúsculas y `correo` distinguiéndolas, sin justificación de
   negocio. Se detectó preguntando por qué, no leyendo el código.

### 6.2 Limitaciones de nuestro propio proceso de uso

Estas son fallas del equipo, no de la herramienta, y se declaran porque son
verificables y afectan a la evidencia de este mismo documento.

4. **El conteo de trailers es una cota inferior, no un censo.** 23 commits
   llevan `Co-Authored-By: Claude Opus 5`, pero el trailer se aplicó de forma
   inconsistente y el uso real de IA fue mayor: `70043a4` (`feat(modelos)`) fue
   asistido por IA y no lo lleva. La declaración autorizada del uso es la tabla
   de la sección 1, no el conteo de trailers.
5. **La higiene de contextos de IA se aplicó a una sola herramienta.**
   `.gitignore` excluye `.claude/` (`cb6ed4d`) pero no `.codex/` ni `AGENTS.md`.
   La regla protege el entorno del Integrante 1 y no el del Integrante 2. El
   efecto de esa asimetría se hizo visible al redactar este documento: una
   primera versión daba el issue #21 como realizado sin IA, y la corrección vino
   de la declaración del propio Integrante 2 en la revisión del Pull Request, no
   del repositorio, donde ese uso no dejaba ninguna marca. La
   evidencia de uso de IA quedó por eso asimétrica: automática y verificable de
   un lado, declarada por el integrante del otro.
6. **La integración continua no cubre la rama de integración.**
   `.github/workflows/pruebas.yml` ejecuta `pytest` en cada Pull Request y en
   push a `main`, pero no en push a `develop`. Como `develop` es justamente donde
   se integra el trabajo de ambos, un push directo a esa rama no queda cubierto
   por el control automatizado descrito en la sección 4.
