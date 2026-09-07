# Sistema de Prestamo de Equipos de Laboratorio

Aplicacion de linea de comandos para gestionar el prestamo de equipos tecnologicos
de un laboratorio universitario.

> Tarea 1 - Verificacion y Validacion.
> Enunciado: https://github.com/Pruebas-de-Software/VerificacionVsValidacion/blob/main/ejercicios/ej_s22026.md

## Estado

En construccion. Este README debe quedar completo: siguiendo UNICAMENTE estas
instrucciones el revisor tiene que poder instalar y ejecutar la aplicacion.

## Tecnologias

- Python 3.11+ (desarrollado sobre 3.14)
- pytest (pruebas)
- sentry-sdk (monitoreo de errores)
- Persistencia en archivos JSON (sin base de datos)

## Instalacion

```bash
git clone https://github.com/<usuario>/sistema-prestamo-equipos.git
cd sistema-prestamo-equipos
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar SENTRY_DSN si se desea monitoreo
```

## Ejecucion

```bash
# Crear datos de demostracion en datos/demo/
python -m prestamos init-demo

# Si ya existen y quieres regenerarlos explicitamente
python -m prestamos init-demo --force

# Menu interactivo usando los datos demo
python -m prestamos --datos-dir datos/demo

# Subcomandos disponibles
python -m prestamos --help
```

Para subcomandos autenticados puedes omitir `--contrasena`; la CLI la pedira
sin eco en pantalla:

```bash
python -m prestamos --datos-dir datos/demo --usuario enc-demo equipos listar
python -m prestamos --datos-dir datos/demo --usuario enc-demo prestamos atrasados --fecha 2026-09-10
```

## Datos de demostracion

Ver `datos/demo/`. El dataset representa el estado del laboratorio al
`2026-09-10`: contiene usuarios, equipos y solicitudes/prestamos en estados
`SOLICITADA`, `APROBADA`, `ENTREGADA`, `ATRASADA` y `DEVUELTA`.

Credenciales ficticias de demostracion:

| Usuario | Contrasena | Rol |
| --- | --- | --- |
| `enc-demo` | `DemoEncargado2026!` | Encargado |
| `sol-demo` | `DemoSolicitante2026!` | Solicitante |
| `sol-demo-2` | `DemoSolicitante2026!` | Solicitante |

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

## Pruebas

```bash
pytest -v
# Con evidencia en archivo:
pytest -v | tee docs/evidencias/pruebas/ejecucion-pytest.txt
```

## Autores

- Benjamin Olguin- @nonmeeeeeeeeeeeeeee
- Isaias Carte @IsaiasACF

## Licencia

MIT. Ver [LICENSE](LICENSE).
