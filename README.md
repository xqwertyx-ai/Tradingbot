# Tradingbot — investigación

Proyecto de I+D. Todo es **simulación con datos históricos públicos**; nada de esto es asesoramiento financiero ni opera con dinero real.

## Experimento 1: mercados "Bitcoin Up or Down" de 5 minutos (Polymarket)

**Pregunta:** ¿alguna regla simple acierta lo bastante como para cubrir el precio, la comisión y el deslizamiento?

**Cómo:**
1. Descarga los mercados resueltos de BTC 5 min (`btc-updown-5m-<inicio>`), su resultado oficial y el histórico de precio de "Up" (~1 punto por minuto).
2. Descarga velas de 1 min de BTC-USD (Coinbase) para calcular señales.
3. Simula 8 reglas fijadas de antemano (ver `tradingbot/backtest.py`), comprando 1 acción por mercado.
4. Divide los datos en el tiempo: 70% exploración, 30% prueba. **Solo cuenta la prueba.**
5. Escribe el informe en [`reports/informe.md`](reports/informe.md).

**Criterio de aprobado (fijado antes de ver datos):** ≥ 200 operaciones en prueba y límite inferior del IC 95% del P&L medio > 0.

**Costes simulados** (en `tradingbot/config.py`):
- Comisión taker de Polymarket en cripto: `0,07 × p × (1 − p)` por acción (1,75 ¢ a p = 0,50), según la [documentación oficial](https://docs.polymarket.com/trading/fees).
- Deslizamiento: 1 ¢ por acción.

## Cómo ejecutarlo desde el móvil

1. Pestaña **Actions** → **Backtest BTC 5 min** → **Run workflow**.
2. Elige los días de histórico (por defecto 14) y lánzalo.
3. Cuando termine, abre `reports/informe.md`.

También se ejecuta solo cada mañana y añade los mercados nuevos. La descarga es incremental: ampliar los días solo baja lo que falta.

## En local

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/descargar.py --dias 14
python scripts/backtest.py
```

## Aviso legal

En mayo de 2026 la DGOJ ordenó el bloqueo cautelar de Polymarket en España. Este repositorio solo lee datos públicos para investigar; no incluye código para operar.
