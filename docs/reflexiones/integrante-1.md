# Reflexión individual - Benjamín Olguín

## 1. Que ambigüedad influyó más en el diseño y cómo la resolví?

La ambigüedad que más me costó no venía del enunciado del cliente sino de dos supuestos que el propio equipo había escrito y que no eran compatibles entre sí. SUP-04 dice que un equipo `RESERVADO` no está disponible, tratando el estado como un escalar que bloquea al equipo completo. SUP-08 y RN-09 permiten reservar hasta 20 días laborales hacia el futuro. Juntos significan que reservar un equipo para dentro de tres semanas lo deja muerto durante tres semanas por un compromiso de dos días.

El problema me tocaba a mí porque #11 es lo primero que escribe `RESERVADO` en el catálogo: mientras nadie lo escribiera, la contradicción no se notaba. Lo resolví dejando de tratar `Equipo.estado` como la autoridad y convirtiéndolo en una proyección: `reglas.estado_por_compromiso` deriva el escalar a partir de los compromisos vigentes con sus fechas, y la verdad sobre disponibilidad vive en la relación entre préstamos y fechas, no en el campo.

Vale la pena distinguir esto de la reflexión de mi compañero, que trabajó la misma frontera desde el otro lado. Él consumió el contrato: sus consultas de #13 clasifican sin mutar estados. Yo estuve del lado del productor y tuve que decidir cuál es la fuente de verdad, escribir la función que la calcula y corregir los caminos de escritura que ya estaban decidiendo a ciegas.

Evidencia: SUP-04 y SUP-08 en [docs/reglas-negocio.md](../reglas-negocio.md), RN-09 y RN-10, las decisiones registradas en [PLAN.md](../../PLAN.md), y los commits [`7a15d7f`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/7a15d7f) y [`620f0c0`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/620f0c0).

## 2. Cuál fue la prueba más útil y qué riesgo permitió reducir?

Las más útiles fueron las seis pruebas que agregué en [`620f0c0`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/620f0c0) sobre `tests/unidad/test_servicio_prestamos.py`, con dos préstamos sobre el mismo equipo. Cinco de esas seis fallaron contra el código que ya estaba integrado en `develop`.

Lo interesante es que la prueba útil no fue una aserción nueva, fue cambiar la forma del escenario. Todas las pruebas existentes del archivo eran un préstamo contra un equipo, y con esa forma decidir el estado a ciegas y calcularlo a partir de los compromisos dan exactamente el mismo resultado: son indistinguibles, así que ninguna prueba podía separarlas. Recién con dos compromisos sobre el mismo equipo aparecieron los tres errores reales: cancelar escribía `RESERVADO -> DISPONIBLE` aunque otra reserva siguiera viva, devolver escribía `DISPONIBLE` y borraba un `RESERVADO` que otra solicitud aprobada todavía justificaba, y ninguna de las dos respetaba `MANTENCION` ni `BAJA`, de modo que una devolución podía reponer al catálogo un equipo retirado.

El riesgo que redujo es el más caro del sistema: el descuadre entre lo que dice el JSON y los equipos que están físicamente en el laboratorio. Un equipo retirado que reaparece como disponible termina siendo prometido a alguien que no lo va a poder retirar.

Evidencia: commit [`620f0c0`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/620f0c0), `src/prestamos/servicios/prestamos.py`, `src/prestamos/reglas.py::estado_por_compromiso` y `tests/unidad/test_servicio_prestamos.py`.

## 3. Qué fallo o comportamiento inesperado detecté y cómo se corrigió?

Detecté dos, y lo que aprendí de ellos no fue tanto el hallazgo como el criterio para decidir qué hacer con cada uno.

El primero fue DEF-02 / #47, encontrado con PC20-04 en las pruebas cruzadas de #20. RN-18 exige que las operaciones queden auditadas, y las entregas modifican inventario físico, pero no dejan evento de auditoría. Como contradice una regla escrita, lo registré como defecto con su issue, y la prueba quedó en el repositorio como `XFAIL`: documenta la expectativa y avisa el día que alguien la cumpla, en vez de desaparecer hasta que alguien se acuerde.

El segundo fue OBS-01, que apareció al escribir CP-15 en #19: mi primera versión del caso falló con `assert [] == ['S-0002']`. Un préstamo `APROBADA` cuya `fecha_inicio` es exactamente hoy y que todavía no se entrega no cae en ninguna de las tres consultas: no es futuro porque la comparación es estricta, y no es vigente porque eso exige `ENTREGADA`. Es justo el día en que el solicitante debe ir a retirar el equipo, o sea el día en que la reserva más necesita ser visible. No lo registré como defecto: puede ser una decisión deliberada de dominio, porque sin custodia física no hay nada "vigente". Quedó como observación, con la decisión devuelta al contrato de RF-12, y CP-15 esquiva el caso poniendo la reserva del 15 al 17 y consultando el 14.

La diferencia que me quedó clara es esa: cuando el sistema contradice una regla escrita, es defecto y lleva issue; cuando contradice una expectativa mía pero no una regla, lo honesto es documentarlo y pedir la decisión, no inventar el requerimiento que me conviene.

Evidencia: OBS-01 en [issue-19-casos-combinados-escenario.md](../evidencias/pruebas/issue-19-casos-combinados-escenario.md), DEF-02 en [docs/defectos.md](../defectos.md) e [issue-20-pruebas-cruzadas-integrante-1.md](../evidencias/pruebas/issue-20-pruebas-cruzadas-integrante-1.md), y `tests/cruzadas/test_integrante_1_revisa_integrante_2.py`.

## 4. Qué aporte de mi compañero mejoró mi trabajo?

El aporte más útil de Isaías fue su revisión del PR #45, sobre autenticación. Mi función `_descomponer` verificaba que la sal y el digest no estuvieran vacíos, y a mí me parecía suficiente. Él observó que una credencial truncada, con una sal o un digest de un solo byte, pasaba esa validación y recién fallaba después en `hmac.compare_digest`, produciendo el mensaje "Credenciales invalidas". Es decir, un `usuarios.json` corrupto se veía exactamente igual que un typo del usuario.

Lo que me hizo cambiar no fue una línea, fue el criterio: yo estaba validando que los campos existieran, y él estaba mirando si la validación alcanzaba para distinguir dos causas de falla completamente distintas, que es justamente lo que ese módulo promete hacer. La corrección quedó en el commit [`64fd18e`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/64fd18e): el digest se compara exacto contra `hashlib.sha256().digest_size` derivándolo del algoritmo en vez de escribir 32 a mano, y la sal se compara contra un mínimo y no contra `BYTES_DE_SAL`, porque esa constante gobierna la generación y exigir igualdad invalidaría todas las credenciales existentes al subirla. Se agregaron tres pruebas: sal truncada, digest truncado y digest demasiado largo.

Evidencia: PR #45, commit [`64fd18e`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/64fd18e) y `src/prestamos/auth.py`.

## 5. Qué parte del sistema podría fallar todavía?

Lo que más me inquieta es la fragilidad de la solución que yo mismo elegí en la pregunta 1. Convertir `Equipo.estado` en una proyección derivada de los compromisos funciona solo mientras todos los caminos de escritura pasen por `reglas.estado_por_compromiso`. Nada en el diseño lo obliga: es una convención, no una restricción estructural.

Y no es una preocupación teórica, porque ya falló dos veces. `cancelar` y `devolver` escribían el estado por su cuenta y se equivocaban en cuanto un equipo tenía más de un compromiso; los corregí en [`620f0c0`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/620f0c0). Si mañana alguien agrega una operación nueva que toque el catálogo, puede volver a escribir el escalar a mano, y el error va a ser invisible mientras cada equipo tenga un solo préstamo. Un diseño más robusto tendría que impedirlo, por ejemplo dejando de persistir el escalar y calculándolo siempre al leer.

Evidencia: `src/prestamos/reglas.py::estado_por_compromiso`, `src/prestamos/servicios/prestamos.py` y el commit [`620f0c0`](https://github.com/nonmeeeeeeeeeeeeeee/sistema-prestamo-equipos/commit/620f0c0).

## 6. Qué aprendí sobre la diferencia entre verificar y validar?

Lo entendí al escribir el README de #28. La idea era que seguir las instrucciones sin conocer ese módulo por dentro demostrara que alcanzan para un revisor externo, y esa ejecución quedó registrada como actividad de validación en #22.

Ahí vi la diferencia. Verificar lo puedo hacer conociendo el sistema, comparándolo contra los documentos. Validar a veces exige lo contrario: ignorancia deliberada, porque quien ya sabe cómo funciona el módulo por dentro rellena mentalmente los pasos que faltan y deja de ser capaz de juzgar si las instrucciones bastan.

Evidencia: #28, #22, [docs/verificacion-validacion.md](../verificacion-validacion.md) y el reparto documentado en [docs/trabajo-colaborativo.md](../trabajo-colaborativo.md).
