# Evidencia issue #19 - CP-13 a CP-15 combinacion y escenario completo

Ejecutado por: nonmeeeeeeeeeeeeeee (B. Olguin)  
Fecha: 2026-09-06  
Rama: test/casos-combinados-escenario (apilada sobre test/casos-negativos)

## Comando ejecutado: `.venv/Scripts/pytest.exe tests/integracion/test_escenario_completo.py -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Dev\sistema-prestamo-equipos\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Dev\sistema-prestamo-equipos
configfile: pyproject.toml
collecting ... collected 3 items

tests/integracion/test_escenario_completo.py::test_CP13_RF07_el_atraso_retiene_el_cupo_de_equipos_activos_rn16_y_rn07 PASSED [ 33%]
tests/integracion/test_escenario_completo.py::test_CP14_RF07_la_cancelacion_libera_solo_el_cupo_cancelado_rn15_y_rn07 PASSED [ 66%]
tests/integracion/test_escenario_completo.py::test_CP15_RF01_a_RF12_ciclo_completo_sobre_persistencia_real PASSED [100%]

============================== 3 passed in 0.12s ==============================
```

## Comando ejecutado: `.venv/Scripts/pytest.exe -m "combinacion or escenario" -v`

```text
testpaths: tests
collecting ... collected 269 items / 266 deselected / 3 selected

tests/integracion/test_escenario_completo.py::test_CP13_RF07_el_atraso_retiene_el_cupo_de_equipos_activos_rn16_y_rn07 PASSED [ 33%]
tests/integracion/test_escenario_completo.py::test_CP14_RF07_la_cancelacion_libera_solo_el_cupo_cancelado_rn15_y_rn07 PASSED [ 66%]
tests/integracion/test_escenario_completo.py::test_CP15_RF01_a_RF12_ciclo_completo_sobre_persistencia_real PASSED [100%]

====================== 3 passed, 266 deselected in 0.19s ======================
```

## Comando ejecutado: `.venv/Scripts/pytest.exe`

```text
collected 269 items

============================= 269 passed in 5.31s =============================
```

## Comando ejecutado: `git diff --check`

```text
Sin salida; exit code 0.
```

## Decisiones de diseno de los casos

### La interaccion elegida: RN-07 no es una regla independiente

El limite de tres equipos activos no se guarda en ninguna parte: se **calcula**
recorriendo la maquina de estados (`reglas._validar_limite_equipos_activos`):

```python
if existente.estado in ESTADOS_DISPONIBILIDAD_BLOQUEADA:  # {APROBADA, ENTREGADA, ATRASADA}
    activos += len(existente.equipos)
```

`ATRASADA` esta dentro del conjunto y `CANCELADA` no. Esa es una interaccion
real -el resultado de una regla cambia el veredicto de otra- y RN-07 aparecia
en solo dos lugares de toda la suite antes de esta rama.

Se descartaron dos alternativas:

- **RN-08 x RN-09** (duracion maxima y ventana de anticipacion en sus limites
  simultaneos): cumple la letra del DoD pero no su espiritu. Las dos guardas son
  independientes; en ese caso simplemente pasan las dos a la vez, sin que
  ninguna condicione a la otra.
- **RN-05 x RN-10** (la disjuncion entre el escalar `Equipo.estado` y el
  solapamiento de fechas): es la interaccion mejor documentada del codigo, pero
  `tests/unidad/test_servicio_solicitudes.py` declara en su propio docstring que
  el solapamiento es su tema principal y ya cubre que un equipo `RESERVADO`
  sigue siendo solicitable fuera de la ventana.

Tambien se descarto la devolucion con otra reserva viva: ya la cubre
`test_devolver_deja_el_equipo_reservado_si_hay_una_reserva_pendiente`, uno de
los seis tests que trajo el fix `620f0c0`.

### El cupo se reparte 2 + 1 en CP-14, y no 3

Cancelando una reserva de tres equipos el contador cae a 0 y cualquier solicitud
posterior pasa: el caso no distinguiria un contador correcto de uno que se
reinicia. Repartiendo 2 + 1 y cancelando la de un equipo, el limite queda en 2 y
la asercion se vuelve exigente: **una solicitud de dos equipos sigue rechazada y
una de uno pasa**. Eso es lo que fija el contador como por-equipo y no
por-solicitud.

### La aritmetica se afirma leyendo `detalles`

En ambos casos combinados la asercion decisiva no es que se levante
`ErrorValidacion`, sino el contenido de `detalles`: `equipos_activos` igual a 3
con el prestamo atrasado y a 2 despues de la cancelacion. Ese numero es lo unico
que distingue "el contador funciono" de "el contador coincidio". Si `ATRASADA`
saliera de `ESTADOS_DISPONIBILIDAD_BLOQUEADA`, CP-13 fallaria mostrando 0 en vez
de 3, senalando exactamente que se rompio.

### CP-15 corre por los servicios, no por la CLI

El DoD enumera operaciones de dominio, no comandos, y su condicion explicita
-"sobre persistencia real en tmp_path, no con mocks"- habla de los repositorios.
Ir por la CLI habria obligado a apilar esta rama tambien sobre el PR #55
(`feat/cli-menu`), sin mergear, por una ganancia que el issue no pide; ademas la
capa CLI ya tiene su propia cobertura en `tests/funcionales/`.

Lo que CP-15 aporta y ningun otro test tiene es que **los cinco servicios
comparten estado a traves de los archivos JSON**. Por eso se montan sobre las
mismas instancias de `RepositorioJson` y cada asercion **relee del repositorio**
en vez de encadenar el objeto devuelto por la llamada anterior: encadenarlo
probaria que los servicios devuelven lo que prometen, no que lo persisten.

El atraso se marca **explicitamente** con `marcar_atraso` en vez de dejar que
`registrar_devolucion` lo deduzca, porque el DoD lo lista como paso propio y asi
la devolucion transita T-09 y no T-08.

La reserva futura B existe para que la consulta final discrimine. Con un solo
prestamo el cierre devolveria tres listas vacias, que no distinguiria un
clasificador correcto de uno que no devuelve nada.

## Observaciones para el registro de defectos

### OBS-01: un prestamo aprobado que empieza hoy no aparece en ninguna consulta

Detectado al escribir CP-15: la primera version fijaba el inicio de la reserva
futura el mismo dia de la consulta final y el caso fallo con
`assert [] == ['S-0002']`.

Los tres clasificadores de `ServicioPrestamos` son:

| Consulta | Condicion |
| --- | --- |
| `prestamos_futuros` | `estado is APROBADA and fecha_inicio > hoy` |
| `prestamos_vigentes` | `estado is ENTREGADA and fecha_devolucion is None and inicio <= hoy <= termino` |
| `prestamos_atrasados` | derivada de `ENTREGADA`/`ATRASADA` vencidas |

Una solicitud `APROBADA` cuya `fecha_inicio` es exactamente hoy y que todavia no
se entrega **no cae en ninguna de las tres**: no es futura porque la comparacion
es estricta, y no es vigente porque eso exige `ENTREGADA`. Es justo el dia en que
el solicitante deberia ir a retirar el equipo, es decir el dia en que la reserva
mas necesita ser visible para el encargado.

Puede ser deliberado -no hay custodia fisica, asi que no es "vigente"- pero
RF-12 dice que el sistema clasifica futuros, vigentes y atrasados, y aqui hay un
prestamo activo invisible a las tres. Queda como observacion, no como defecto
confirmado; corresponde decidirlo con el contrato de RF-12 a la vista.

CP-15 esquiva el caso poniendo la reserva B del 15 al 17 y consultando el 14.

### OBS-02: sin cobertura previa de RN-07 fuera del motor

Antes de esta rama, RN-07 aparecia en la suite solo en `test_reglas.py:266` y en
un docstring de `test_servicio_solicitudes.py`. Ninguna prueba verificaba que su
contador reaccionara a las transiciones de estado, que es precisamente de donde
saca su valor.
