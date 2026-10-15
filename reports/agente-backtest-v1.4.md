# Backtest del agente de noticias (v1.4)

Generado: 2026-10-15 08:04 UTC · modelo claude-sonnet-5-5 · coste total de la API ≈ 5.16 USD. Simulación; no es asesoramiento financiero.

## Cómo se hizo
- 73 sesiones, de 2026-07-01 a 2026-10-13. Cada día, el mismo análisis de cierre que la web, solo con titulares publicados antes del cierre de Wall Street y precios hasta ese día.
- Cada hipótesis es un plan: objetivo, stop y plazo, todo con precios de cierre. ACIERTO si toca el objetivo antes que el stop; FALLO si toca el stop; al vencer, EXPIRADA puntuada por el signo.
- Se opera (en simulación) si el valor esperado neto ≥ 1% y la probabilidad ≥ 55. El resto se registra para medir la calibración.
- Retorno neto: menos el coste de ida y vuelta (0,10% acciones/índices, 0,06% futuros, 0,04% divisas, 0,20% cripto). Factor de beneficio = ganancias netas / pérdidas netas.
- **Lo que cuenta es desde el 01-08-2026.** El conocimiento fiable del modelo llega a junio de 2026; julio se muestra aparte por si supiera algo de esas semanas.

## Resultado frente al objetivo (≥ 1% neto por operación)

Ninguna hipótesis pasó el filtro para operarse desde agosto.

## Resultados (hipótesis cerradas)

| Grupo | n | Acierto (IC 95%) | Retorno neto medio (±IC 95%) | Factor de beneficio | Objetivo tocado |
|---|--:|--:|--:|--:|--:|
| Desde agosto · operadas | 0 | — | — | — | — |
| Desde agosto · todas | 124 | 44% (35–52%) | -0.05% (±0.60) | 0.96 | 23% |
| Desde agosto · no operadas | 124 | 44% (35–52%) | -0.05% (±0.60) | 0.96 | 23% |
| Julio (posible contaminación) · todas | 55 | 53% (40–65%) | +0.26% (±1.01) | 1.18 | 27% |

**Referencia ingenua** (mismas fechas, activos, objetivos, stops y plazos; dirección = tendencia del último mes). Si el agente no la supera, las noticias no aportan nada.

| Grupo | n | Acierto (IC 95%) | Retorno neto medio (±IC 95%) | Factor de beneficio | Objetivo tocado |
|---|--:|--:|--:|--:|--:|
| Referencia · mismas que las operadas | 0 | — | — | — | — |
| Referencia · todas | 123 | 49% (40–58%) | -0.17% (±0.57) | 0.87 | 22% |

## Calibración (desde agosto)

La probabilidad declarada debería parecerse a la frecuencia real con la que se toca el objetivo.

| Probabilidad declarada | n | Media declarada | Objetivo tocado | Acierto (incl. expiradas) |
|---|--:|--:|--:|--:|
| 0–44 | 108 | 40% | 23% | 44% |
| 45–54 | 16 | 46% | 19% | 44% |
| 55–64 | 0 | — | — | — |
| 65–100 | 0 | — | — | — |

Objetivo medio 3.5% · stop medio 2.2% · EV previsto medio de las operadas nan%.

## Por activo (desde agosto, n ≥ 3)

| Activo | n | Acierto | Neto medio |
|---|--:|--:|--:|
| GC=F | 11 | 55% | +0.90% |
| BZ=F | 10 | 60% | +2.10% |
| XLE | 10 | 40% | -0.10% |
| SMH | 10 | 30% | -0.13% |
| ^RUT | 9 | 56% | +0.32% |
| BTC-USD | 9 | 44% | -0.58% |
| IBE.MC | 7 | 43% | -0.64% |
| NVDA | 7 | 43% | +0.55% |
| XLF | 6 | 33% | -0.68% |
| SAN.MC | 5 | 80% | +0.92% |
| EURUSD=X | 5 | 20% | -0.20% |
| ITX.MC | 4 | 50% | -0.47% |
| BBVA.MC | 4 | 0% | -2.14% |
| ASML | 3 | 33% | -1.26% |
| MSFT | 3 | 33% | -0.66% |
| SOL-USD | 3 | 33% | -1.53% |
| ^GSPC | 3 | 67% | +0.61% |
| ^NDX | 3 | 0% | -1.68% |
| ^STOXX50E | 3 | 67% | +0.05% |

## Notas
- Registradas 187, cerradas 179, aún abiertas 8.
- Días con decisión "operar": 0 de 72 analizados.
- Cada análisis por día y todas las hipótesis: `data/agent_bt/`.
- Fase de fiabilidad (bitácora): <30 cerradas, rodaje; 30-99, indicativa; 100-299, útil; ≥300 y dos regímenes, fiable.
- Varias hipótesis del mismo día comparten contexto: el n efectivo es menor y los IC algo optimistas.
- Este periodo ya se usó para evaluar versiones anteriores: una mejora aquí es una pista, no una prueba. La prueba es el test en vivo.
