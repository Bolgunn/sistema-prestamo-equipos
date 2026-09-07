# Evidencia issue #17 - CP-06 a CP-09 borde

Ejecutado por: IsaiasACF  
Fecha: 2026-09-06  
Rama: test/casos-borde

## Comando ejecutado: `PATH=.venv/bin:$PATH pytest tests/borde/test_borde.py -v`

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- .../.venv/bin/python3
collecting ... collected 4 items

tests/borde/test_borde.py::test_CP06_RF07_limite_exacto_tres_equipos_activos_es_permitido PASSED [ 25%]
tests/borde/test_borde.py::test_CP07_RF10_devolucion_exactamente_en_fecha_termino_no_genera_atraso PASSED [ 50%]
tests/borde/test_borde.py::test_CP08_RF08_inicio_igual_a_termino_de_reserva_existente_rechaza_por_rn10 PASSED [ 75%]
tests/borde/test_borde.py::test_CP09_RF06_fecha_inicio_igual_a_fecha_termino_habil_cuenta_un_dia PASSED [100%]

============================== 4 passed in 0.30s ===============================
```

## Comando ejecutado: `PATH=.venv/bin:$PATH pytest -m borde -v`

```text
collecting ... collected 224 items / 220 deselected / 4 selected

tests/borde/test_borde.py::test_CP06_RF07_limite_exacto_tres_equipos_activos_es_permitido PASSED [ 25%]
tests/borde/test_borde.py::test_CP07_RF10_devolucion_exactamente_en_fecha_termino_no_genera_atraso PASSED [ 50%]
tests/borde/test_borde.py::test_CP08_RF08_inicio_igual_a_termino_de_reserva_existente_rechaza_por_rn10 PASSED [ 75%]
tests/borde/test_borde.py::test_CP09_RF06_fecha_inicio_igual_a_fecha_termino_habil_cuenta_un_dia PASSED [100%]

====================== 4 passed, 220 deselected in 1.03s =======================
```

## Comando ejecutado: `PATH=.venv/bin:$PATH pytest`

```text
collected 224 items

============================= 224 passed in 6.73s ==============================
```

## Comando ejecutado: `git diff --check`

```text
Sin salida; exit code 0.
```
