# Informe: mercados BTC 5 min de Polymarket

Generado: 2026-11-22 13:21 UTC. Simulación con datos históricos públicos; no es asesoramiento financiero.

## Datos
- Mercados resueltos: 12090 (2026-09-30 18:15 → 2026-11-22 13:10 UTC)
- Con precio de Polymarket y de BTC al inicio: 11700
- Exploración: 8463 mercados hasta 2026-11-09 22:55; prueba: 3627 mercados posteriores
- Frecuencia histórica de 'Up': 49.1%

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
| siempre_up | 3461 | 47.2% (45.5%–48.8%) | 51.8% | -4.63 (-6.24 a -3.02) | -160.2 |
| momentum_prev5 | 3458 | 52.1% (50.4%–53.7%) | 54.2% | -2.12 (-3.73 a -0.51) | -73.2 |
| reversion_prev5 | 3458 | 47.9% (46.3%–49.6%) | 51.1% | -3.17 (-4.78 a -1.56) | -109.7 |
| continuacion_m1 | 3367 | 67.6% (66.0%–69.2%) | 69.0% | -1.41 (-2.87 a +0.04) | -47.6 |
| continuacion_m2 | 3285 | 74.2% (72.7%–75.7%) | 76.0% | -1.81 (-3.15 a -0.46) | -59.3 |
| continuacion_m3 | 2642 | 76.7% (75.1%–78.3%) | 78.5% | -1.79 (-3.18 a -0.41) | -47.4 |
| favorito_m2 | 3284 | 77.7% (76.3%–79.1%) | 79.0% | -1.27 (-2.62 a +0.07) | -41.7 |
| desfavorito_m2 | 3284 | 22.3% (20.9%–23.7%) | 25.2% | -2.95 (-4.29 a -1.60) | -96.8 |

## Resultados — Exploración

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 8241 | 49.8% (48.7%–50.8%) | 52.5% | -2.73 (-3.77 a -1.68) | -224.6 |
| momentum_prev5 | 8225 | 51.6% (50.6%–52.7%) | 55.2% | -3.57 (-4.61 a -2.53) | -293.8 |
| reversion_prev5 | 8225 | 48.4% (47.3%–49.4%) | 50.1% | -1.71 (-2.75 a -0.67) | -140.5 |
| continuacion_m1 | 7874 | 66.6% (65.6%–67.6%) | 67.9% | -1.28 (-2.26 a -0.31) | -101.0 |
| continuacion_m2 | 7830 | 72.3% (71.3%–73.3%) | 74.0% | -1.74 (-2.63 a -0.85) | -136.0 |
| continuacion_m3 | 6584 | 75.5% (74.4%–76.5%) | 77.0% | -1.48 (-2.36 a -0.61) | -97.7 |
| favorito_m2 | 7906 | 76.0% (75.1%–76.9%) | 78.1% | -2.06 (-2.95 a -1.18) | -163.1 |
| desfavorito_m2 | 7907 | 24.0% (23.1%–24.9%) | 26.2% | -2.23 (-3.11 a -1.34) | -176.2 |

## Veredicto
Ninguna regla supera el criterio. Con estos costes, no hay ventaja demostrable.

## Calibración del mercado (minuto 2)
Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado y es difícil ganarle con reglas simples.

| Tramo de precio Up | n | Precio medio | Frecuencia real Up |
|---|---|---|---|
| [0.0, 0.1) | 1404 | 5.3% | 5.6% |
| [0.1, 0.2) | 1381 | 14.9% | 14.9% |
| [0.2, 0.3) | 1171 | 24.8% | 21.6% |
| [0.3, 0.4) | 1041 | 34.9% | 34.4% |
| [0.4, 0.5) | 940 | 44.9% | 45.2% |
| [0.5, 0.6) | 955 | 54.9% | 53.3% |
| [0.6, 0.7) | 1007 | 64.9% | 62.8% |
| [0.7, 0.8) | 1104 | 75.1% | 76.1% |
| [0.8, 0.9) | 1245 | 85.0% | 86.9% |
| [0.9, 1.0) | 1406 | 94.8% | 95.2% |

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
