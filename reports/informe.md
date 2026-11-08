# Informe: mercados BTC 5 min de Polymarket

Generado: 2026-11-08 11:58 UTC. Simulación con datos históricos públicos; no es asesoramiento financiero.

## Datos
- Mercados resueltos: 8041 (2026-09-30 18:15 → 2026-11-08 11:45 UTC)
- Con precio de Polymarket y de BTC al inicio: 7825
- Exploración: 5629 mercados hasta 2026-10-31 00:40; prueba: 2412 mercados posteriores
- Frecuencia histórica de 'Up': 49.8%

## Supuestos de coste
- Comisión taker: 0.07 × p × (1 − p) por acción (≈ 1.75 céntimos a p = 0,50).
- Deslizamiento: 1 céntimo por acción sobre el precio de referencia.
- Cada operación: 1 acción; paga 1 USDC si acierta.
- Ejecución: primer precio de Polymarket igual o posterior a la señal (retraso medio: 21 s). Nunca se usa un precio anterior a la señal.

## Criterio de aprobado (fijado antes de ver los datos)
Una estrategia pasa solo si en el periodo de prueba tiene ≥ 200 operaciones y el límite inferior del IC 95% del P&L medio por operación es > 0. Se prueban 8 reglas, así que alguna puede salir bien por azar: un aprobado aislado y por poco no basta.

## Resultados — Prueba (lo que cuenta)

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 2322 | 49.4% (47.4%–51.5%) | 52.4% | -3.00 (-4.94 a -1.05) | -69.5 |
| momentum_prev5 | 2319 | 52.7% (50.6%–54.7%) | 55.4% | -2.74 (-4.69 a -0.79) | -63.6 |
| reversion_prev5 | 2319 | 47.3% (45.3%–49.4%) | 49.9% | -2.53 (-4.48 a -0.59) | -58.8 |
| continuacion_m1 | 2172 | 66.4% (64.4%–68.3%) | 67.6% | -1.22 (-3.08 a +0.64) | -26.5 |
| continuacion_m2 | 2169 | 73.0% (71.1%–74.8%) | 73.3% | -0.32 (-1.99 a +1.34) | -7.0 |
| continuacion_m3 | 1822 | 74.4% (72.4%–76.4%) | 76.4% | -1.98 (-3.63 a -0.33) | -36.1 |
| favorito_m2 | 2202 | 77.2% (75.4%–78.9%) | 77.6% | -0.42 (-2.07 a +1.24) | -9.2 |
| desfavorito_m2 | 2203 | 22.8% (21.1%–24.6%) | 26.8% | -3.92 (-5.57 a -2.27) | -86.3 |

## Resultados — Exploración

Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.

| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |
|---|---|---|---|---|---|
| siempre_up | 5503 | 49.8% (48.5%–51.1%) | 52.5% | -2.67 (-3.95 a -1.40) | -147.1 |
| momentum_prev5 | 5490 | 51.0% (49.6%–52.3%) | 55.2% | -4.21 (-5.49 a -2.93) | -231.0 |
| reversion_prev5 | 5490 | 49.0% (47.7%–50.4%) | 50.1% | -1.07 (-2.35 a +0.21) | -58.9 |
| continuacion_m1 | 5295 | 66.9% (65.7%–68.2%) | 68.0% | -1.07 (-2.26 a +0.11) | -56.8 |
| continuacion_m2 | 5263 | 72.2% (71.0%–73.4%) | 74.4% | -2.15 (-3.23 a -1.06) | -112.9 |
| continuacion_m3 | 4427 | 75.7% (74.4%–77.0%) | 77.1% | -1.34 (-2.42 a -0.27) | -59.4 |
| favorito_m2 | 5305 | 75.6% (74.5%–76.8%) | 78.3% | -2.66 (-3.74 a -1.57) | -140.9 |
| desfavorito_m2 | 5305 | 24.4% (23.2%–25.5%) | 26.0% | -1.61 (-2.70 a -0.53) | -85.6 |

## Veredicto
Ninguna regla supera el criterio. Con estos costes, no hay ventaja demostrable.

## Calibración del mercado (minuto 2)
Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado y es difícil ganarle con reglas simples.

| Tramo de precio Up | n | Precio medio | Frecuencia real Up |
|---|---|---|---|
| [0.0, 0.1) | 894 | 5.3% | 5.9% |
| [0.1, 0.2) | 903 | 14.8% | 14.6% |
| [0.2, 0.3) | 767 | 24.8% | 21.1% |
| [0.3, 0.4) | 715 | 35.0% | 35.8% |
| [0.4, 0.5) | 631 | 45.0% | 46.0% |
| [0.5, 0.6) | 669 | 55.0% | 53.2% |
| [0.6, 0.7) | 684 | 64.8% | 62.1% |
| [0.7, 0.8) | 779 | 75.2% | 76.5% |
| [0.8, 0.9) | 846 | 85.0% | 87.2% |
| [0.9, 1.0) | 903 | 94.7% | 95.0% |

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
