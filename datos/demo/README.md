# Datos de demostracion

Archivos JSON semilla que carga `python -m prestamos init-demo`.

El dataset representa el estado del laboratorio al `2026-09-10`. Incluye:

- usuarios demo con contrasenas ficticias documentadas en el README principal;
- cinco equipos de laboratorio;
- solicitudes/prestamos en estados `SOLICITADA`, `APROBADA`, `ENTREGADA`,
  `ATRASADA` y `DEVUELTA`.

No guardar contrasenas en texto plano dentro de `usuarios.json`; el archivo
solo debe contener el hash normal de autenticacion.
