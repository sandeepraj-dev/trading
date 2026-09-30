import time
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data import fetch_data, normalize_symbol
from indicators import add_indicators, signal_columns
from strategies import current_analysis, backtest, STRATEGIES

st.set_page_config(page_title="Intraday Analyzer Pro", page_icon="📈", layout="wide")
st.title("📈 Intraday Analyzer Pro")
st.caption("Historical accuracy + entry/exit/stop-loss analysis. Educational use only.")

with st.sidebar:
    st.header("Market")
    symbol = st.text_input("NSE symbol", "RELIANCE.NS")
    interval = st.selectbox("Candle interval", ["5m", "15m", "30m", "1h"])
    live_period = st.selectbox("Current chart history", ["1d", "5d", "1mo"])

    st.header("Backtest")
    strategy = st.selectbox("Strategy", list(STRATEGIES.keys()))
    bt_period = st.selectbox("Backtest period", ["5d", "1mo", "3mo", "6mo", "1y", "2y"], index=3)
    risk = st.number_input("Risk budget per trade (₹)", 100, 100000, 1000, 100)
    costs = st.number_input("Brokerage + costs / trade (₹)", 0.0, 1000.0, 20.0, 1.0)
    slippage = st.number_input("Slippage (%)", 0.0, 2.0, 0.05, 0.01)
    atr_stop = st.slider("Stop loss: ATR ×", 0.5, 3.0, 1.2, 0.1)
    rr = st.slider("Target risk/reward", 0.5, 4.0, 1.5, 0.1)
    max_hold = st.slider("Maximum holding candles", 2, 100, 20)

    auto = st.checkbox("Auto refresh", False)
    seconds = st.slider("Refresh seconds", 15, 300, 60)

ticker = normalize_symbol(symbol)

try:
    live = signal_columns(add_indicators(fetch_data(ticker, interval, live_period)))
    a = current_analysis(live)
except Exception as e:
    st.error(str(e))
    st.stop()

st.subheader(f"{ticker} — Current setup")
c = st.columns(5)
c[0].metric("Price", f"₹{a['price']:,.2f}")
c[1].metric("Setup", a["overall"])
c[2].metric("Score", f"{a['score']:+d} / {a['max_score']}")
c[3].metric("ATR", f"₹{a['atr']:,.2f}")
c[4].metric("Direction", a["direction"])

if a["direction"] != "WAIT":
    e = st.columns(4)
    e[0].metric("Entry", f"₹{a['price']:,.2f}")
    e[1].metric("Stop loss", f"₹{a['stop']:,.2f}")
    e[2].metric("Target 1", f"₹{a['target1']:,.2f}")
    e[3].metric("Target 2", f"₹{a['target2']:,.2f}")
else:
    st.info("No strong combined setup right now. WAIT.")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=live.index, open=live.open, high=live.high, low=live.low,
    close=live.close, name="Price"
))
for col, name in [("ema9", "EMA 9"), ("ema20", "EMA 20"),
                  ("ema50", "EMA 50"), ("vwap", "VWAP")]:
    fig.add_trace(go.Scatter(x=live.index, y=live[col], mode="lines", name=name))
fig.update_layout(xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

l, r = st.columns(2)
with l:
    labels = {1: "BUY", -1: "SELL", 0: "NEUTRAL"}
    rows = [{"Strategy": k, "Signal": labels[v]} for k, v in a["signals"].items()]
    st.subheader("Strategy agreement")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
with r:
    row = live.iloc[-1]
    vals = {
        "Price": row.close, "VWAP": row.vwap, "EMA 9": row.ema9,
        "EMA 20": row.ema20, "EMA 50": row.ema50, "RSI": row.rsi,
        "MACD": row.macd, "ADX": row.adx, "Volume ratio": row.volume_ratio
    }
    st.subheader("Indicators")
    st.dataframe(pd.DataFrame({"Value": vals}), use_container_width=True)

st.divider()
st.header("🧪 Historical accuracy / backtest")
st.warning(
    "Win rate is historical backtest performance. It is not the probability "
    "that the next trade will win."
)

try:
    bt = signal_columns(add_indicators(fetch_data(ticker, interval, bt_period)))
    result = backtest(
        bt, strategy, risk_per_trade=risk,
        brokerage_per_trade=costs, slippage_pct=slippage,
        atr_stop=atr_stop, rr1=rr, max_hold_bars=max_hold
    )
except Exception as e:
    st.error(f"Backtest error: {e}")
    st.stop()

if result["total"] == 0:
    st.info("No completed trades. Try another strategy, timeframe or longer period.")
else:
    b = st.columns(4)
    b[0].metric("Trades", result["total"])
    b[1].metric("Historical win rate", f"{result['win_rate']:.1f}%")
    pf = result["profit_factor"]
    b[2].metric("Profit factor", "∞" if pf == float("inf") else f"{pf:.2f}")
    b[3].metric("Net P&L", f"₹{result['net_pnl']:,.2f}")

    b = st.columns(3)
    b[0].metric("Wins / losses", f"{result['wins']} / {result['losses']}")
    b[1].metric("Expectancy / trade", f"₹{result['expectancy']:,.2f}")
    b[2].metric("Max drawdown", f"₹{result['max_drawdown']:,.2f}")

    st.caption(
        "Signal is generated from a completed candle; entry is the next candle open. "
        "Stop/target are ATR-based. If both are touched in one candle, stop is assumed first."
    )

    eq = result["trades"][["Exit time", "PnL"]].copy()
    eq["Equity"] = eq.PnL.cumsum()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=eq["Exit time"], y=eq.Equity, mode="lines", name="Equity"))
    fig2.update_layout(height=350, yaxis_title="₹", title="Backtest equity curve")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Trade log")
    st.dataframe(
        result["trades"].sort_values("Entry time", ascending=False),
        hide_index=True, use_container_width=True
    )

st.subheader("How accuracy is calculated")
st.markdown(
    "**Win rate = winning completed trades / total completed trades × 100.** "
    "Profit factor, expectancy and maximum drawdown are also shown because win rate "
    "alone can be misleading. Current entry, stop-loss and targets are reference "
    "levels calculated from the rules; they are not guaranteed prices."
)

if auto:
    time.sleep(seconds)
    st.rerun()
