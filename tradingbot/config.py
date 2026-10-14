"""Parámetros del backtest. Cambiar aquí, no en el código.

Fuentes verificadas el 2026-10-14:
- Comisión taker Polymarket (categoría Crypto): fee = acciones * 0.07 * p * (1 - p)
  (https://docs.polymarket.com/trading/fees). Makers no pagan.
- Mercados "Bitcoin Up or Down" de 5 min: slug btc-updown-5m-<unix inicio ventana>,
  resuelven con el TWAP 60 s de Chainlink BTC/USD; "Up" si el final >= inicio.
"""

WINDOW_SECONDS = 300

# Comisión taker (por acción): FEE_RATE * p * (1 - p)
FEE_RATE = 0.07

# Deslizamiento simulado por acción comprada (en USDC). El histórico de Polymarket
# da un precio de referencia, no el ask real; esto lo compensa de forma conservadora.
SLIPPAGE = 0.01

# Se ejecuta al primer precio de Polymarket igual o posterior a la señal; si no hay
# ninguno en este margen, no se opera. Nunca usar un precio anterior a la señal.
MAX_EXEC_DELAY_SECONDS = 60

# Fracción cronológica de datos usada para "explorar"; el resto es la prueba final.
TRAIN_FRACTION = 0.7

# Criterio de aprobado, fijado ANTES de ver los datos:
# la estrategia pasa solo si el límite inferior del IC 95% del P&L medio por
# operación en el periodo de prueba es > 0 (tras comisión y deslizamiento).
MIN_TRADES_TEST = 200

GAMMA_URL = "https://gamma-api.polymarket.com/events"
CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

DATA_DIR = "data"
REPORT_PATH = "reports/informe.md"
