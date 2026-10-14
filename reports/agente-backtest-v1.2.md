# Backtest del agente de noticias

Generado: 2026-10-14 23:08 UTC · modelo claude-sonnet-5-5 · coste total de la API ≈ 3.04 USD. Simulación; no es asesoramiento financiero.

## Cómo se hizo
- 73 sesiones, de 2026-07-01 a 2026-10-13. Cada día, el mismo análisis de cierre que la web, solo con titulares publicados antes del cierre de Wall Street y precios hasta ese día.
- Hipótesis evaluadas con las reglas de la bitácora: FALLO si un cierre toca la invalidación; al vencer, se puntúa por el signo del retorno.
- Retorno neto: descontando costes simulados (0,1% ida y vuelta en acciones, 0,04% divisas, 0,2% cripto).
- **Lo que cuenta es desde el 01-08-2026.** El conocimiento fiable del modelo llega a junio de 2026; julio se muestra aparte por si supiera algo de esas semanas.

## Resultados (hipótesis cerradas)

| Grupo | n | Acierto | IC 95% | Retorno neto medio |
|---|--:|--:|--:|--:|
| Desde agosto · todas | 6 | 50% | 19–81% | -1.90% |
| Desde agosto · operadas (confianza ≥ 60) | 0 | — | — | — |
| Desde agosto · solo vigilancia (< 60) | 6 | 50% | 19–81% | -1.90% |
| Julio (posible contaminación) | 1 | 100% | 21–100% | +0.12% |

**Referencia ingenua** (mismas fechas, activos y plazos, dirección = tendencia del último mes): 67% de acierto (IC 95% 30–90%, n = 6). Si el agente no la supera, las noticias no están aportando nada.

## Calibración (desde agosto)

Si la confianza significa algo, el acierto debería subir con ella.

| Confianza | n | Acierto |
|---|--:|--:|
| 0–49 | 6 | 50% |
| 50–59 | 0 | — |
| 60–69 | 0 | — |
| 70–100 | 0 | — |

## Por activo (desde agosto, n ≥ 3)

| Activo | n | Acierto |
|---|--:|--:|
| XLE | 4 | 50% |

## Notas
- Registradas 7, cerradas 7, aún abiertas 0.
- Días con decisión "no operar hoy": 64 de 73.
- Cada análisis por día y todas las hipótesis: `data/agent_bt/`.
- Fase de fiabilidad (bitácora): <30 cerradas, rodaje; 30-99, indicativa; 100-299, útil; ≥300 y dos regímenes, fiable.
- Varias hipótesis del mismo día comparten contexto: el n efectivo es menor y los IC algo optimistas.
