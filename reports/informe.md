# Informe: mercados BTC 5 min de Polymarket

Generado: 2026-11-15 12:44 UTC. Simulación con datos históricos públicos; no es asesoramiento financiero.

## Datos
- Mercados resueltos: 10066 (2026-09-30 18:15 → 2026-11-15 12:30 UTC)
- Con precio de Polymarket y de BTC al inicio: 9768
- Exploración: 7046 mercados hasta 2026-11-05 00:50; prueba: 3020 mercados posteriores
- Frecuencia histórica de 'Up': 49.3%

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
| siempre_up | 2890 | 46.9% (45.1%–48.7%) | 52.3% | -5.45 (-7.20 a -3.70) | -157.5 |
| momentum_prev5 | 2888 | 52.9% (51.1%–54.7%) | 54.5% | -1.64 (-3.40 a +0.11) | -47.4 |
| reversion_prev5 | 2888 | 47.1% (45.3%–48.9%) | 50.7% | -3.65 (-5.41 a -1.90) | -105.5 |
| continuacion_m1 | 2725 | 66.9% (65.1%–68.6%) | 67.9% | -1.03 (-2.67 a +0.61) | -28.1 |
| continuacion_m2 | 2716 | 73.2% (71.5%–74.8%) | 74.8% | -1.57 (-3.05 a -0.10) | -42.8 |
| continuacion_m3 | 2268 | 77.6% (75.8%–79.2%) | 78.2% | -0.64 (-2.11 a +0.83) | -14.5 |
| favorito_m2 | 2734 | 77.9% (76.3%–79.4%) | 78.4% | -0.55 (-2.02 a +0.92) | -15.1 |
| desfavorito_m2 | 2735 | 22.1% (20.6%–23.7%) | 25.8% | -3.71 (-5.18 a -2.24) | -101.5 |

## Resultados — Exploración

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 6878 | 50.1% (49.0%–51.3%) | 52.4% | -2.30 (-3.44 a -1.16) | -158.4 |
| momentum_prev5 | 6864 | 51.5% (50.3%–52.7%) | 55.3% | -3.79 (-4.94 a -2.65) | -260.4 |
| reversion_prev5 | 6864 | 48.5% (47.3%–49.7%) | 50.0% | -1.49 (-2.63 a -0.35) | -102.1 |
| continuacion_m1 | 6605 | 66.7% (65.5%–67.8%) | 67.9% | -1.27 (-2.34 a -0.21) | -84.1 |
| continuacion_m2 | 6562 | 72.4% (71.3%–73.4%) | 74.2% | -1.89 (-2.87 a -0.92) | -124.2 |
| continuacion_m3 | 5499 | 75.3% (74.2%–76.5%) | 76.9% | -1.56 (-2.52 a -0.59) | -85.6 |
| favorito_m2 | 6620 | 75.9% (74.8%–76.9%) | 78.2% | -2.29 (-3.26 a -1.32) | -151.9 |
| desfavorito_m2 | 6620 | 24.1% (23.1%–25.2%) | 26.1% | -1.99 (-2.96 a -1.02) | -131.8 |

## Veredicto
Ninguna regla supera el criterio. Con estos costes, no hay ventaja demostrable.

## Calibración del mercado (minuto 2)
Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado y es difícil ganarle con reglas simples.

| Tramo de precio Up | n | Precio medio | Frecuencia real Up |
|---|---|---|---|
| [0.0, 0.1) | 1140 | 5.3% | 5.6% |
| [0.1, 0.2) | 1125 | 14.9% | 14.9% |
| [0.2, 0.3) | 980 | 24.8% | 21.6% |
| [0.3, 0.4) | 884 | 34.9% | 34.0% |
| [0.4, 0.5) | 794 | 44.9% | 45.0% |
| [0.5, 0.6) | 796 | 55.0% | 53.4% |
| [0.6, 0.7) | 858 | 64.9% | 62.7% |
| [0.7, 0.8) | 945 | 75.2% | 76.7% |
| [0.8, 0.9) | 1040 | 85.0% | 86.5% |
| [0.9, 1.0) | 1145 | 94.7% | 95.1% |

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
