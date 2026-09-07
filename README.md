# Sistema de Prestamo de Equipos de Laboratorio

Aplicacion de linea de comandos para gestionar el prestamo de equipos tecnologicos
de un laboratorio universitario.

> Tarea 1 - Verificacion y Validacion.
> Enunciado: https://github.com/Pruebas-de-Software/VerificacionVsValidacion/blob/main/ejercicios/ej_s22026.md

## Estado

Entrega final. Siguiendo UNICAMENTE las instrucciones de este README el revisor
puede instalar, ejecutar la aplicacion y correr la suite de pruebas.

Verificado en limpio el 2026-09-06 sobre Windows 11 + Python 3.14.5: clon nuevo
del repositorio, entorno virtual nuevo, y los comandos de las secciones
siguientes ejecutados en orden (302 pruebas pasando, 1 xfail).

## Tecnologias

- Python 3.11+ (desarrollado y verificado sobre 3.14)
- pytest (pruebas)
- sentry-sdk (monitoreo de errores)
- Persistencia en archivos JSON (sin base de datos)

## Instalacion

```bash
git clone https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos.git
cd sistema-prestamo-equipos
python -m venv .venv
```

Activar el entorno virtual:

```bash
# Windows (PowerShell / CMD)
.venv\Scripts\activate
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Instalar dependencias y el paquete:

```bash
pip install -r requirements.txt
pip install -e .          # necesario para poder ejecutar `python -m prestamos`
cp .env.example .env      # completar SENTRY_DSN solo si se desea monitoreo
```

El paso `pip install -e .` es obligatorio: el codigo vive en `src/` y sin esa
instalacion `python -m prestamos` falla con `No module named prestamos`.
La aplicacion funciona sin `SENTRY_DSN`; en ese caso el monitoreo queda inactivo.

Comprobacion rapida de que la instalacion quedo bien:

```bash
python -m prestamos --help
```

## Ejecucion

Los datos de demostracion ya vienen versionados en `datos/demo/`, asi que se
puede ejecutar la aplicacion de inmediato. `init-demo` solo hace falta si se
quieren regenerar.

```bash
# Regenerar los datos de demostracion en datos/demo/
python -m prestamos init-demo --force

# Menu interactivo usando los datos demo
python -m prestamos --datos-dir datos/demo

# Subcomandos disponibles
python -m prestamos --help
```

En el menu interactivo se elige `1. Iniciar sesion`, se ingresa un usuario de la
tabla de credenciales y luego la contrasena (que no se muestra en pantalla).
`0. Salir` termina la aplicacion.

Para subcomandos autenticados puedes omitir `--contrasena`; la CLI la pedira
sin eco en pantalla:

```bash
python -m prestamos --datos-dir datos/demo --usuario enc-demo equipos listar
python -m prestamos --datos-dir datos/demo --usuario enc-demo prestamos atrasados --fecha 2026-09-10
```

Salida esperada del primer comando:

```
EQ-DEMO-01 | DISPONIBLE | Notebook Dell Latitude
EQ-DEMO-02 | RESERVADO | Proyector Epson
EQ-DEMO-03 | PRESTADO | Kit Arduino
EQ-DEMO-04 | PRESTADO | Camara Sony
EQ-DEMO-05 | DISPONIBLE | Multimetro Fluke
```

Salida esperada del segundo:

```
S-0004 | ATRASADA | sol-demo-2 | EQ-DEMO-04 | 2026-08-25 -> 2026-08-27
```

## Datos de demostracion

Ver `datos/demo/`. El dataset representa el estado del laboratorio al
`2026-09-10`: contiene usuarios, equipos y solicitudes/prestamos en estados
`SOLICITADA`, `APROBADA`, `ENTREGADA`, `ATRASADA` y `DEVUELTA`.

Credenciales ficticias de demostracion (solo para el dataset demo):

| Usuario | Contrasena | Rol | Para que sirve |
| --- | --- | --- | --- |
| `enc-demo` | `DemoEncargado2026!` | Encargado | Aprueba/rechaza solicitudes, registra entregas y devoluciones, consulta atrasados |
| `sol-demo` | `DemoSolicitante2026!` | Solicitante | Crea solicitudes y consulta sus propios prestamos |
| `sol-demo-2` | `DemoSolicitante2026!` | Solicitante | Segundo solicitante; es el dueno del prestamo atrasado `S-0004` |

## Documentacion

| Documento | Contenido |
| --- | --- |
| [docs/documento-principal.md](docs/documento-principal.md) | Documento integrador de la entrega |
| [docs/analisis-requerimiento.md](docs/analisis-requerimiento.md) | Ambiguedades, preguntas, requerimiento mejorado |
| [docs/reglas-negocio.md](docs/reglas-negocio.md) | Reglas, alcance y exclusiones |
| [docs/estados-transiciones.md](docs/estados-transiciones.md) | Maquina de estados del prestamo |
| [docs/verificacion-validacion.md](docs/verificacion-validacion.md) | 5 actividades de V + 5 de V |
| [docs/matriz-trazabilidad.md](docs/matriz-trazabilidad.md) | Trazabilidad requerimiento -> codigo -> prueba |
| [docs/estrategia-pruebas.md](docs/estrategia-pruebas.md) | Estrategia y resultados de pruebas |
| [docs/casos-de-prueba.md](docs/casos-de-prueba.md) | Los 15+ casos ejecutados |
| [docs/defectos.md](docs/defectos.md) | Defectos, correcciones y reejecuciones |
| [docs/trabajo-colaborativo.md](docs/trabajo-colaborativo.md) | Flujo Git, ramas, PRs, reparto |
| [docs/uso-ia.md](docs/uso-ia.md) | Declaracion de uso de IA |
| [docs/reflexiones/](docs/reflexiones/) | Reflexiones individuales |
| [docs/evidencias/](docs/evidencias/) | Evidencias de ejecucion de pruebas, V y V |

## Pruebas

```bash
pytest
```

Resultado esperado: `302 passed, 1 xfailed`.

La evidencia de la ejecucion esta guardada en
[docs/evidencias/pruebas/issue-24-pytest-v.txt](docs/evidencias/pruebas/issue-24-pytest-v.txt).
Para regenerarla:

```bash
pytest -v > docs/evidencias/pruebas/issue-24-pytest-v.txt
```

## Autores

- Benjamin Olguin - [@nonmeeeeeeeeeeeeeee](https://github.com/nonmeeeeeeeeeeeeeee)
- Isaias Carte - [@IsaiasACF](https://github.com/IsaiasACF)

## Licencia

MIT. Ver [LICENSE](LICENSE).
