# Backtest del agente de noticias (v1.3)

Generado: 2026-10-15 00:18 UTC · modelo claude-sonnet-5-5 · coste total de la API ≈ 4.89 USD. Simulación; no es asesoramiento financiero.

## Cómo se hizo
- 73 sesiones, de 2026-07-01 a 2026-10-13. Cada día, el mismo análisis de cierre que la web, solo con titulares publicados antes del cierre de Wall Street y precios hasta ese día.
- Hipótesis evaluadas con las reglas de la bitácora: FALLO si un cierre toca la invalidación; al vencer, se puntúa por el signo del retorno.
- Retorno neto: descontando costes simulados (0,1% ida y vuelta en acciones, 0,04% divisas, 0,2% cripto).
- **Lo que cuenta es desde el 01-08-2026.** El conocimiento fiable del modelo llega a junio de 2026; julio se muestra aparte por si supiera algo de esas semanas.

## Resultados (hipótesis cerradas)

| Grupo | n | Acierto | IC 95% | Retorno neto medio |
|---|--:|--:|--:|--:|
| Desde agosto · todas | 122 | 54% | 45–63% | -0.01% |
| Desde agosto · operadas (confianza ≥ 60) | 0 | — | — | — |
| Desde agosto · solo vigilancia (< 60) | 122 | 54% | 45–63% | -0.01% |
| Julio (posible contaminación) | 60 | 53% | 41–65% | +0.22% |

**Referencia ingenua** (mismas fechas, activos y plazos, dirección = tendencia del último mes): 53% de acierto (IC 95% 44–62%, n = 122). Si el agente no la supera, las noticias no están aportando nada.

## Calibración (desde agosto)

Si la confianza significa algo, el acierto debería subir con ella.

| Confianza | n | Acierto |
|---|--:|--:|
| 0–49 | 121 | 55% |
| 50–59 | 1 | 0% |
| 60–69 | 0 | — |
| 70–100 | 0 | — |

## Por activo (desde agosto, n ≥ 3)

| Activo | n | Acierto |
|---|--:|--:|
| SMH | 11 | 27% |
| GC=F | 10 | 50% |
| BZ=F | 10 | 60% |
| ^TNX | 9 | 56% |
| BTC-USD | 9 | 44% |
| XLE | 7 | 29% |
| ^RUT | 7 | 57% |
| ^STOXX50E | 6 | 83% |
| EURUSD=X | 6 | 33% |
| XLF | 5 | 60% |
| SAN.MC | 5 | 60% |
| ^GSPC | 4 | 25% |
| IBE.MC | 4 | 50% |
| NVDA | 4 | 75% |
| BBVA.MC | 3 | 100% |
| MSFT | 3 | 100% |
| DX-Y.NYB | 3 | 67% |
| ETH-USD | 3 | 0% |
| ^NDX | 3 | 67% |

## Notas
- Registradas 192, cerradas 182, aún abiertas 10.
- Días con decisión "no operar hoy": 73 de 73.
- Cada análisis por día y todas las hipótesis: `data/agent_bt/`.
- Fase de fiabilidad (bitácora): <30 cerradas, rodaje; 30-99, indicativa; 100-299, útil; ≥300 y dos regímenes, fiable.
- Varias hipótesis del mismo día comparten contexto: el n efectivo es menor y los IC algo optimistas.
