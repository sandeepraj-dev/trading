# Intraday Analyzer Pro

Educational intraday dashboard with current technical analysis and historical backtesting.

Features:
- Entry, stop-loss and target reference levels
- Historical win rate ("accuracy")
- Profit factor, expectancy and maximum drawdown
- Trade log and equity curve
- VWAP, EMA, momentum, breakout, pullback, Bollinger and ADX strategies
- Brokerage and slippage assumptions

Run:
    pip install -r requirements.txt
    streamlit run app/main.py

Important:
Win rate is historical backtest performance for the selected symbol, timeframe,
period and strategy. It is NOT the probability that the next trade will win.

Free market data can be delayed, incomplete, or rate-limited. Use a broker's
official API for live trading and validate with paper trading first.
