# Reflexion individual - IsaiasACF


## 1. Que ambiguedad influyo mas en el diseño y como la resolvi?

La ambiguedad que mas me hizo frenar fue la relacion entre `Equipo.estado` y la disponibilidad real para una fecha. Al principio parecia natural pensar que si un equipo estaba `RESERVADO` o `PRESTADO`, entonces no podia usarse nunca para otra solicitud. Pero al avanzar con #12 y #13 quedo claro que eso era demasiado simple: una reserva es un rango de fechas, mientras que `Equipo.estado` es solo un valor puntual.

Lo resolvi apoyandome en `docs/estados-transiciones.md` y en el motor de reglas de #9: la disponibilidad se valida con fechas y prestamos existentes, y las consultas de #13 solo clasifican, sin modificar ni persistir estados. Esa separacion se ve en los tests de `tests/unidad/test_servicio_prestamos.py` y en CP-05, donde las consultas devuelven futuros, vigentes y atrasados sin mutar los JSON. Me quedo como aprendizaje que un estado visible en una entidad no siempre es la fuente completa de verdad; a veces es apenas una fotografia, y la regla real vive en la relacion entre varias entidades.

Evidencia: #12, #13, CP-05 en [docs/casos-de-prueba.md](../casos-de-prueba.md), [issue-16-casos-funcionales.md](../evidencias/pruebas/issue-16-casos-funcionales.md) y `tests/unidad/test_servicio_prestamos.py`.

## 2. Cual fue la prueba mas util y que riesgo permitio reducir?

La prueba mas util para mi fue CP-07 de #17, la devolucion exactamente en `fecha_termino`. Es un caso chico, pero toca una frontera peligrosa: si el plazo termina el 12, devolver el mismo 12 debe cerrar el prestamo como `DEVUELTA`, liberar el equipo y no marcarlo como `ATRASADA`. Ese tipo de comparacion parece obvia hasta que alguien cambia un `>` por un `>=` y convierte el ultimo dia valido en atraso.

Por eso reforcé CP-07 para que no solo mirara el estado final, sino tambien el camino: la prueba espia los eventos enviados al motor y comprueba que se use `EventoTransicion.REGISTRAR_DEVOLUCION` y que no se ejecute `MARCAR_ATRASO`. Hice la mutacion manual de la condicion `fecha_devolucion > fecha_termino` a `fecha_devolucion >= fecha_termino`; CP-07 fallo con esa mutacion y volvio a pasar al restaurar la condicion correcta. Ese ejercicio redujo el riesgo de aceptar una devolucion limite como atraso por un error de operador relacional.

Evidencia: CP-07 en [docs/casos-de-prueba.md](../casos-de-prueba.md), [issue-17-casos-borde.md](../evidencias/pruebas/issue-17-casos-borde.md), `tests/borde/test_borde.py::test_CP07_RF10_devolucion_exactamente_en_fecha_termino_no_genera_atraso` y la asercion `EventoTransicion.MARCAR_ATRASO not in eventos` en `tests/borde/test_borde.py`.

## 3. Que fallo o comportamiento inesperado detecte y como se corrigio?

El comportamiento inesperado mas claro en mi parte aparecio con #15: `init-demo --force` no era reproducible byte a byte. Yo habia dejado datos demo funcionales, pero los hashes de contrasena cambiaban por las sales aleatorias normales del sistema. Para usuarios reales eso esta bien; para un dataset versionado de demostracion era un problema, porque regenerar los JSON producia diffs aunque los datos fueran los mismos.

La correccion fue acotar el cambio solo a `demo.py`: usar hashes demo fijos/precalculados para credenciales ficticias, sin tocar `auth.py` ni debilitar el hashing normal. Tambien agregue una prueba que genera los datos, fuerza la sobrescritura y compara los tres JSON byte a byte contra los versionados. Me gusto ese arreglo porque no peleo contra la seguridad del sistema: separa lo que es demo reproducible de lo que es autenticacion real.

Evidencia: PR #57, commit [`a734f26`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/a734f26), `src/prestamos/demo.py`, `tests/funcionales/test_init_demo.py` y `datos/demo/usuarios.json`.

## 4. Que aporte de mi companero mejoro mi trabajo?

El aporte mas concreto de Benjamin fueron sus revisiones a mis PRs #55 y #57. En #55 me hizo mirar la CLI con ojos menos felices: no bastaba con que los subcomandos existieran, tambien habia que cuidar que la contrasena no quedara como argumento obligatorio del proceso, que Sentry no capturara variables locales y que el menu distinguiera bien EOF, `KeyboardInterrupt` y `OSError`. Eso termino en el commit [`7fc57ab`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/7fc57ab).

En #57 detecto el problema de reproducibilidad de `init-demo --force`, que yo no habia tratado como requisito fuerte hasta verlo en revision. Esa observacion termino en el commit [`a734f26`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/a734f26). Tambien sus pruebas cruzadas de #20 fueron utiles porque validaron mis issues #12 a #15 desde otro angulo y dejaron un defecto abierto real, DEF-02/#47, sobre logs de auditoria en operaciones de prestamos. No fue comodo ver un `xfail`, pero fue mejor que cerrar los ojos y decir que todo estaba listo.

Evidencia: PR #55, PR #57, [issue-20-pruebas-cruzadas-integrante-1.md](../evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md), [docs/defectos.md](../defectos.md), commits [`7fc57ab`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/7fc57ab) y [`a734f26`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/a734f26).

## 5. Que parte del sistema podria fallar todavia?

La parte que todavia me deja mas inquieto es la observabilidad de las operaciones de prestamos. En #8 se habia trabajado la base de errores, logs y Sentry; despues, con #12, entrega/devolucion/cancelacion empezaron a modificar inventario fisico. Las pruebas cruzadas de #20 dejaron marcado DEF-02/#47: registrar entrega deberia quedar en log de auditoria por RN-18, pero esa prueba esta `XFAIL`.

Tambien hay un riesgo menor en consultas: CP-15 documento una observacion sobre una solicitud `APROBADA` que inicia exactamente el dia de consulta. No se marco como defecto confirmado, porque puede ser una decision de dominio, pero muestra que RF-12 podria necesitar mas precision si el usuario espera ver esas reservas en alguna lista.

Evidencia: [issue-20-pruebas-cruzadas-integrante-1.md](../evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md), [docs/defectos.md](../defectos.md), CP-15 y observaciones en [issue-19-casos-combinados-escenario.md](../evidencias/pruebas/issue-19-casos-combinados-escenario.md).

## 6. Que aprendi sobre la diferencia entre verificar y validar?

Para mi, verificar fue comprobar que el sistema estaba construido segun lo que prometian los documentos y los issues: que #12 usara el motor de reglas, que #13 no mutara estados al consultar, que #14 no mostrara tracebacks ni pidiera contrasenas de forma insegura, que #15 fuera idempotente y reproducible, y que las correcciones de revision quedaran cubiertas con tests.

Validar fue otra cosa: preguntarme si esos comportamientos realmente servian para trabajar con prestamos de laboratorio. Ahi entran CP-01 a CP-05, CP-06 a CP-09, CP-15 y las pruebas cruzadas #20/#21. Esas pruebas no solo dicen "el codigo cumple una regla"; dicen "este flujo tiene sentido para alguien que presta, devuelve, consulta o revisa equipos". La diferencia se me hizo bastante concreta: verificar me protege de construir mal; validar me protege de construir algo correcto en papel pero torpe o incompleto para el uso real.

Evidencia: #16, #17, #21, [docs/verificacion-validacion.md](../verificacion-validacion.md), [docs/casos-de-prueba.md](../casos-de-prueba.md), [issue-16-casos-funcionales.md](../evidencias/pruebas/issue-16-casos-funcionales.md), [issue-17-casos-borde.md](../evidencias/pruebas/issue-17-casos-borde.md) y [issue-21-pruebas-cruzadas-benjamin.md](../evidencias/pruebas/issue-21-pruebas-cruzadas-benjamin.md).
