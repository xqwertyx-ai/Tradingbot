"""Activos que sigue la portada. Editar aquí para añadir o quitar valores.

yahoo: símbolo en Yahoo Finance (fuente principal).
stooq: símbolo en Stooq (respaldo); None si no hay.
coinbase: par en Coinbase (respaldo para cripto).
key: True = aparece en las fichas y en el panel de gráficas de la portada.
"""

ASSETS = [
    # Índices
    dict(yahoo="^GSPC", stooq="^spx", name="S&P 500", group="Índices", key=True),
    dict(yahoo="^NDX", stooq="^ndx", name="Nasdaq 100", group="Índices", key=True),
    dict(yahoo="^IBEX", stooq=None, name="IBEX 35", group="Índices", key=True),
    dict(yahoo="^STOXX50E", stooq=None, name="Euro Stoxx 50", group="Índices", key=False),
    dict(yahoo="^RUT", stooq=None, name="Russell 2000", group="Índices", key=False),
    # Tipos, divisas y materias primas
    dict(yahoo="^TNX", stooq=None, name="Bono EE. UU. 10a (%)", group="Macro", key=True, level=True),
    dict(yahoo="EURUSD=X", stooq="eurusd", name="EUR/USD", group="Macro", key=True),
    dict(yahoo="DX-Y.NYB", stooq=None, name="Índice dólar", group="Macro", key=False),
    dict(yahoo="BZ=F", stooq=None, name="Brent", group="Macro", key=True),
    dict(yahoo="GC=F", stooq=None, name="Oro", group="Macro", key=True),
    # Cripto
    dict(yahoo="BTC-USD", stooq=None, coinbase="BTC-USD", name="Bitcoin", group="Cripto", key=True),
    dict(yahoo="ETH-USD", stooq=None, coinbase="ETH-USD", name="Ethereum", group="Cripto", key=False),
    dict(yahoo="SOL-USD", stooq=None, coinbase="SOL-USD", name="Solana", group="Cripto", key=False),
    # Sectores EE. UU. (ETF)
    dict(yahoo="SMH", stooq="smh.us", name="Semiconductores (SMH)", group="Sectores", key=False),
    dict(yahoo="XLF", stooq="xlf.us", name="Financieras (XLF)", group="Sectores", key=False),
    dict(yahoo="XLE", stooq="xle.us", name="Energía (XLE)", group="Sectores", key=False),
    dict(yahoo="XLK", stooq="xlk.us", name="Tecnología (XLK)", group="Sectores", key=False),
    # Acciones EE. UU. y Europa
    dict(yahoo="NVDA", stooq="nvda.us", name="NVIDIA", group="Acciones", key=False),
    dict(yahoo="AAPL", stooq="aapl.us", name="Apple", group="Acciones", key=False),
    dict(yahoo="MSFT", stooq="msft.us", name="Microsoft", group="Acciones", key=False),
    dict(yahoo="ASML", stooq="asml.us", name="ASML", group="Acciones", key=False),
    dict(yahoo="SAN.MC", stooq=None, name="Banco Santander", group="Acciones", key=False),
    dict(yahoo="BBVA.MC", stooq=None, name="BBVA", group="Acciones", key=False),
    dict(yahoo="ITX.MC", stooq=None, name="Inditex", group="Acciones", key=False),
    dict(yahoo="IBE.MC", stooq=None, name="Iberdrola", group="Acciones", key=False),
]

BY_TICKER = {a["yahoo"]: a for a in ASSETS}
