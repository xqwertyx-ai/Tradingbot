# Informe: mercados BTC 5 min de Polymarket

Generado: 2026-10-14 18:29 UTC. Simulación con datos históricos públicos; no es asesoramiento financiero.

## Datos
- Mercados resueltos: 4033 (2026-09-30 18:15 → 2026-10-14 18:15 UTC)
- Con precio de Polymarket y de BTC al inicio: 4031
- Exploración: 2823 mercados hasta 2026-10-10 13:25; prueba: 1210 mercados posteriores
- Frecuencia histórica de 'Up': 50.5%

## Supuestos de coste
- Comisión taker: 0.07 × p × (1 − p) por acción (≈ 1.75 céntimos a p = 0,50).
- Deslizamiento: 1 céntimo por acción sobre el precio de referencia.
- Cada operación: 1 acción; paga 1 USDC si acierta.

## Criterio de aprobado (fijado antes de ver los datos)
Una estrategia pasa solo si en el periodo de prueba tiene ≥ 200 operaciones y el límite inferior del IC 95% del P&L medio por operación es > 0. Se prueban 8 reglas, así que alguna puede salir bien por azar: un aprobado aislado y por poco no basta.

## Resultados — Prueba (lo que cuenta)

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 1210 | 49.3% (46.4%–52.1%) | 52.8% | -3.53 (-6.34 a -0.72) | -42.7 |
| momentum_prev5 | 1209 | 51.1% (48.3%–53.9%) | 52.5% | -1.36 (-4.17 a +1.45) | -16.4 |
| reversion_prev5 | 1209 | 48.9% (46.1%–51.7%) | 53.0% | -4.14 (-6.95 a -1.33) | -50.0 |
| continuacion_m1 | 1178 | 65.3% (62.5%–67.9%) | 54.3% | +10.97 (+8.33 a +13.62) | +129.3 |
| continuacion_m2 | 1200 | 71.3% (68.7%–73.8%) | 64.3% | +7.06 (+4.61 a +9.51) | +84.7 |
| continuacion_m3 | 1169 | 79.0% (76.5%–81.2%) | 70.2% | +8.80 (+6.55 a +11.04) | +102.8 |
| favorito_m2 | 1209 | 69.1% (66.4%–71.6%) | 72.4% | -3.33 (-5.82 a -0.83) | -40.2 |
| desfavorito_m2 | 1209 | 30.9% (28.4%–33.6%) | 32.3% | -1.39 (-3.89 a +1.10) | -16.8 |

## Resultados — Exploración

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 2821 | 51.0% (49.1%–52.8%) | 52.7% | -1.72 (-3.56 a +0.12) | -48.6 |
| momentum_prev5 | 2811 | 50.4% (48.5%–52.2%) | 52.5% | -2.17 (-4.02 a -0.32) | -61.0 |
| reversion_prev5 | 2811 | 49.6% (47.8%–51.5%) | 53.0% | -3.32 (-5.17 a -1.48) | -93.4 |
| continuacion_m1 | 2739 | 67.6% (65.8%–69.3%) | 54.2% | +13.39 (+11.68 a +15.09) | +366.7 |
| continuacion_m2 | 2784 | 73.9% (72.2%–75.5%) | 64.8% | +9.06 (+7.49 a +10.63) | +252.2 |
| continuacion_m3 | 2733 | 80.3% (78.8%–81.8%) | 70.0% | +10.29 (+8.86 a +11.72) | +281.3 |
| favorito_m2 | 2819 | 70.6% (68.9%–72.3%) | 72.1% | -1.47 (-3.09 a +0.15) | -41.5 |
| desfavorito_m2 | 2819 | 29.4% (27.7%–31.1%) | 32.6% | -3.27 (-4.89 a -1.65) | -92.3 |

## Veredicto
Pasan el criterio: continuacion_m1, continuacion_m2, continuacion_m3. Siguiente paso: confirmarlo en simulación en vivo (forward test) antes de sacar conclusiones.

## Calibración del mercado (minuto 2)
Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado y es difícil ganarle con reglas simples.

| Tramo de precio Up | n | Precio medio | Frecuencia real Up |
|---|---|---|---|
| [0.0, 0.1) | 116 | 7.0% | 5.2% |
| [0.1, 0.2) | 344 | 15.2% | 14.2% |
| [0.2, 0.3) | 475 | 24.9% | 22.7% |
| [0.3, 0.4) | 519 | 35.1% | 35.5% |
| [0.4, 0.5) | 528 | 44.9% | 46.6% |
| [0.5, 0.6) | 553 | 54.8% | 56.1% |
| [0.6, 0.7) | 529 | 65.0% | 66.0% |
| [0.7, 0.8) | 461 | 74.8% | 71.6% |
| [0.8, 0.9) | 381 | 84.8% | 87.4% |
| [0.9, 1.0) | 125 | 93.0% | 94.4% |

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
- No se modela la profundidad del libro: con importes grandes el coste sería mayor.
- Las señales usan BTC-USD de Coinbase; el mercado resuelve con Chainlink. El resultado sí es el oficial de Polymarket.
- Mercados consecutivos no son del todo independientes; los IC pueden ser algo optimistas.
