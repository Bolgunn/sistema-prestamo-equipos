# Estrategia de pruebas

## 1. Objetivos

## 2. Alcance (que se prueba y que no)

## 3. Responsabilidades

Pruebas cruzadas: cada integrante disena una parte de las pruebas y ejecuta o
revisa casos sobre funcionalidades desarrolladas principalmente por el otro.

| Integrante | Funcionalidades que desarrolla | Casos que disena | Casos que ejecuta (del otro) |
| --- | --- | --- | --- |

## 4. Ambiente de pruebas

## 5. Datos de prueba

## 6. Criterios de entrada y de salida

## 7. Registro de evidencias

Las evidencias se guardan en docs/evidencias/pruebas/.

## 8. Resultados

Cierre al 2026-09-06, con CP-15 terminado. Los 15 casos del minimo exigido
estan disenados, ejecutados y en verde; el detalle de cada uno vive en
docs/casos-de-prueba.md y su salida literal de pytest en las evidencias.

| Categoria | Minimo exigido | Disenados | Ejecutados | OK | Fallidos |
| --- | --- | --- | --- | --- | --- |
| Funcionales | 5 | 5 | 5 | 5 | 0 |
| Borde | 4 | 4 | 4 | 4 | 0 |
| Negativos / entradas invalidas | 3 | 3 | 3 | 3 | 0 |
| Combinacion de reglas | 2 | 2 | 2 | 2 | 0 |
| Escenario completo | 1 | 1 | 1 | 1 | 0 |
| Total | 15 | 15 | 15 | 15 | 0 |

Trazabilidad de la tabla a los archivos que la sustentan:

| Categoria | Casos | Marcador | Archivo | Evidencia |
| --- | --- | --- | --- | --- |
| Funcionales | CP-01 a CP-05 | `funcional` | tests/funcionales/test_funcionales.py | issue-16-casos-funcionales.md |
| Borde | CP-06 a CP-09 | `borde` | tests/borde/test_borde.py | issue-17-casos-borde.md |
| Negativos | CP-10 a CP-12 | `negativo` | tests/negativos/test_negativos.py | issue-18-casos-negativos.md |
| Combinacion | CP-13, CP-14 | `combinacion` | tests/integracion/test_escenario_completo.py | issue-19-casos-combinados-escenario.md |
| Escenario completo | CP-15 | `escenario` | tests/integracion/test_escenario_completo.py | issue-19-casos-combinados-escenario.md |

Los 15 casos son los que responden al minimo exigido, no el total de la suite:
`pytest` corre 269 pruebas, y las 254 restantes cubren modulos y flujos sin
etiqueta CP-XX. Esa separacion es deliberada y esta anotada en los docstrings
de esas pruebas (ver DEF-01, issue #43): usan nombres descriptivos, y la
etiqueta CP-XX queda reservada para los casos que este documento contabiliza.

La matriz de trazabilidad sigue pendiente: exige un criterio de aceptacion por
RF que no forma parte de ninguno de los issues de pruebas.
