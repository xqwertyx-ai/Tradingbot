# Informe: mercados BTC 5 min de Polymarket

Generado: 2026-10-14 18:31 UTC. Simulación con datos históricos públicos; no es asesoramiento financiero.

## Datos
- Mercados resueltos: 4033 (2026-09-30 18:15 → 2026-10-14 18:15 UTC)
- Con precio de Polymarket y de BTC al inicio: 4027
- Exploración: 2823 mercados hasta 2026-10-10 13:25; prueba: 1210 mercados posteriores
- Frecuencia histórica de 'Up': 50.5%

## Supuestos de coste
- Comisión taker: 0.07 × p × (1 − p) por acción (≈ 1.75 céntimos a p = 0,50).
- Deslizamiento: 1 céntimo por acción sobre el precio de referencia.
- Cada operación: 1 acción; paga 1 USDC si acierta.
- Ejecución: primer precio de Polymarket igual o posterior a la señal (retraso medio: 20 s). Nunca se usa un precio anterior a la señal.

## Criterio de aprobado (fijado antes de ver los datos)
Una estrategia pasa solo si en el periodo de prueba tiene ≥ 200 operaciones y el límite inferior del IC 95% del P&L medio por operación es > 0. Se prueban 8 reglas, así que alguna puede salir bien por azar: un aprobado aislado y por poco no basta.

## Resultados — Prueba (lo que cuenta)

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 1208 | 49.2% (46.4%–52.0%) | 52.5% | -3.30 (-6.02 a -0.57) | -39.8 |
| momentum_prev5 | 1207 | 51.1% (48.3%–53.9%) | 55.6% | -4.49 (-7.21 a -1.77) | -54.2 |
| reversion_prev5 | 1207 | 48.9% (46.1%–51.7%) | 49.7% | -0.78 (-3.50 a +1.95) | -9.4 |
| continuacion_m1 | 1175 | 65.3% (62.5%–67.9%) | 68.3% | -3.03 (-5.56 a -0.51) | -35.6 |
| continuacion_m2 | 1161 | 70.5% (67.8%–73.0%) | 73.4% | -2.95 (-5.29 a -0.60) | -34.2 |
| continuacion_m3 | 950 | 74.3% (71.4%–77.0%) | 76.1% | -1.74 (-4.04 a +0.57) | -16.5 |
| favorito_m2 | 1170 | 75.0% (72.4%–77.4%) | 77.9% | -2.96 (-5.30 a -0.63) | -34.7 |
| desfavorito_m2 | 1170 | 25.0% (22.6%–27.6%) | 26.4% | -1.34 (-3.67 a +1.00) | -15.6 |

## Resultados — Exploración

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 2819 | 50.9% (49.1%–52.7%) | 52.7% | -1.80 (-3.58 a -0.01) | -50.7 |
| momentum_prev5 | 2809 | 50.3% (48.5%–52.2%) | 55.1% | -4.79 (-6.58 a -3.01) | -134.7 |
| reversion_prev5 | 2809 | 49.7% (47.8%–51.5%) | 50.2% | -0.49 (-2.28 a +1.29) | -13.9 |
| continuacion_m1 | 2738 | 67.6% (65.8%–69.3%) | 67.7% | -0.09 (-1.72 a +1.55) | -2.3 |
| continuacion_m2 | 2713 | 73.2% (71.5%–74.8%) | 74.7% | -1.52 (-3.03 a -0.02) | -41.4 |
| continuacion_m3 | 2318 | 76.8% (75.1%–78.5%) | 77.6% | -0.75 (-2.23 a +0.73) | -17.4 |
| favorito_m2 | 2749 | 76.0% (74.4%–77.6%) | 78.6% | -2.64 (-4.15 a -1.14) | -72.7 |
| desfavorito_m2 | 2749 | 24.0% (22.4%–25.6%) | 25.6% | -1.60 (-3.10 a -0.10) | -44.0 |

## Veredicto
Ninguna regla supera el criterio. Con estos costes, no hay ventaja demostrable.

## Calibración del mercado (minuto 2)
Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado y es difícil ganarle con reglas simples.

| Tramo de precio Up | n | Precio medio | Frecuencia real Up |
|---|---|---|---|
| [0.0, 0.1) | 452 | 5.5% | 6.9% |
| [0.1, 0.2) | 463 | 14.8% | 14.0% |
| [0.2, 0.3) | 390 | 24.7% | 23.6% |
| [0.3, 0.4) | 374 | 34.8% | 39.6% |
| [0.4, 0.5) | 317 | 45.1% | 44.2% |
| [0.5, 0.6) | 333 | 55.0% | 56.2% |
| [0.6, 0.7) | 367 | 64.8% | 60.2% |
| [0.7, 0.8) | 386 | 75.2% | 73.8% |
| [0.8, 0.9) | 434 | 85.1% | 86.4% |
| [0.9, 1.0) | 513 | 94.6% | 95.1% |

## Estrategias
- `siempre_up` (entrada minuto 0): Control: comprar siempre Up al inicio
- `momentum_prev5` (entrada minuto 0): Lado del movimiento de BTC en los 5 min previos
- `reversion_prev5` (entrada minuto 0): Lado contrario al movimiento de BTC en los 5 min previos
- `continuacion_m1` (entrada minuto 1): Lado del movimiento de BTC en el 1er minuto de la ventana
- `continuacion_m2` (entrada minuto 2): Lado del movimiento de BTC en los 2 primeros minutos
- `continuacion_m3` (entrada minuto 3): Lado del movimiento de BTC en los 3 primeros minutos
- `favorito_m2` (entrada minuto 2): Lado que el mercado da como favorito en el minuto 2
- `desfavorito_m2` (entrada minuto 2): Lado que el mercado da como no favorito en el minuto 2

## Limitaciones
- El precio histórico de Polymarket es un precio de referencia, no el precio al que realmente se habría ejecutado; el deslizamiento lo aproxima.
- El histórico tiene ~1 precio por minuto, así que la ejecución simulada llega ~20 s después de la señal. Un bot más rápido vería otros precios; esa ventaja de velocidad es justo la que tienen los bots de alta frecuencia.
- No se modela la profundidad del libro: con importes grandes el coste sería mayor.
- Las señales usan BTC-USD de Coinbase; el mercado resuelve con Chainlink. El resultado sí es el oficial de Polymarket.
- Mercados consecutivos no son del todo independientes; los IC pueden ser algo optimistas.
