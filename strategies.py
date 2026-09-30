import numpy as np
import pandas as pd

STRATEGIES = {
    "Combined": "combined_signal",
    "VWAP": "sig_vwap",
    "EMA Trend": "sig_ema",
    "Momentum": "sig_momentum",
    "Breakout": "sig_breakout",
    "Pullback": "sig_pullback",
    "Bollinger": "sig_bollinger",
    "ADX Trend": "sig_adx",
}

def current_analysis(df):
    d = df.dropna(subset=["close"])
    r = d.iloc[-1]
    score = int(r.combined_score)
    overall = "BUY SETUP" if score >= 5 else "SELL SETUP" if score <= -5 else "NEUTRAL"
    signals = {
        "VWAP": int(r.sig_vwap),
        "EMA Trend": int(r.sig_ema),
        "Momentum": int(r.sig_momentum),
        "Breakout": int(r.sig_breakout),
        "Pullback": int(r.sig_pullback),
        "Bollinger": int(r.sig_bollinger),
        "ADX Trend": int(r.sig_adx),
    }
    price = float(r.close)
    atr = float(r.atr) if pd.notna(r.atr) and r.atr > 0 else price * 0.005

    if overall == "BUY SETUP":
        stop = price - 1.2 * atr
        risk = price - stop
        target1 = price + 1.5 * risk
        target2 = price + 2.5 * risk
        direction = "LONG"
    elif overall == "SELL SETUP":
        stop = price + 1.2 * atr
        risk = stop - price
        target1 = price - 1.5 * risk
        target2 = price - 2.5 * risk
        direction = "SHORT"
    else:
        stop = target1 = target2 = np.nan
        direction = "WAIT"

    return {
        "overall": overall, "direction": direction, "score": score,
        "max_score": 11, "signals": signals, "price": price,
        "atr": atr, "stop": stop, "target1": target1, "target2": target2
    }

def backtest(df, strategy_name, risk_per_trade=1000.0,
             brokerage_per_trade=0.0, slippage_pct=0.0,
             atr_stop=1.2, rr1=1.5, max_hold_bars=20):
    d = df.copy().reset_index()
    if "Datetime" not in d.columns:
        d.rename(columns={d.columns[0]: "Datetime"}, inplace=True)

    sig_col = STRATEGIES[strategy_name]
    trades = []
    i = 30

    while i < len(d) - 2:
        signal = d.loc[i, sig_col]
        if signal not in (-1, 1):
            i += 1
            continue

        entry_i = i + 1
        entry = float(d.loc[entry_i, "open"])
        atr = d.loc[i, "atr"]
        if not np.isfinite(atr) or atr <= 0:
            i += 1
            continue

        if signal == 1:
            stop = entry - atr_stop * float(atr)
            risk = entry - stop
            target = entry + rr1 * risk
        else:
            stop = entry + atr_stop * float(atr)
            risk = stop - entry
            target = entry - rr1 * risk

        end_i = min(len(d) - 1, entry_i + max_hold_bars)
        exit_i = end_i
        exit_price = float(d.loc[end_i, "close"])
        exit_reason = "TIME EXIT"

        for j in range(entry_i, end_i + 1):
            high, low = float(d.loc[j, "high"]), float(d.loc[j, "low"])
            if signal == 1:
                if low <= stop:
                    exit_i, exit_price, exit_reason = j, stop, "STOP LOSS"
                    break
                if high >= target:
                    exit_i, exit_price, exit_reason = j, target, "TARGET"
                    break
            else:
                if high >= stop:
                    exit_i, exit_price, exit_reason = j, stop, "STOP LOSS"
                    break
                if low <= target:
                    exit_i, exit_price, exit_reason = j, target, "TARGET"
                    break

        raw_move = (exit_price-entry) if signal == 1 else (entry-exit_price)
        slippage = abs(entry) * slippage_pct / 100.0
        net_points = raw_move - slippage
        pnl = (net_points / risk) * risk_per_trade - brokerage_per_trade

        trades.append({
            "Entry time": d.loc[entry_i, "Datetime"],
            "Exit time": d.loc[exit_i, "Datetime"],
            "Side": "BUY" if signal == 1 else "SELL",
            "Entry": entry, "Stop Loss": stop, "Target": target,
            "Exit": exit_price, "Exit reason": exit_reason,
            "Return %": (raw_move / entry) * 100,
            "PnL": pnl, "R multiple": net_points / risk
        })
        i = exit_i + 1

    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return {"trades": trades_df, "total": 0, "wins": 0, "losses": 0,
                "win_rate": np.nan, "net_pnl": 0.0, "profit_factor": np.nan,
                "expectancy": np.nan, "max_drawdown": 0.0}

    wins = int((trades_df.PnL > 0).sum())
    losses = int((trades_df.PnL <= 0).sum())
    win_rate = wins / len(trades_df) * 100
    gross_profit = trades_df.loc[trades_df.PnL > 0, "PnL"].sum()
    gross_loss = -trades_df.loc[trades_df.PnL < 0, "PnL"].sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    equity = trades_df.PnL.cumsum()
    max_drawdown = float(abs((equity - equity.cummax()).min()))

    return {
        "trades": trades_df, "total": len(trades_df),
        "wins": wins, "losses": losses, "win_rate": win_rate,
        "net_pnl": float(trades_df.PnL.sum()),
        "profit_factor": float(profit_factor),
        "expectancy": float(trades_df.PnL.mean()),
        "max_drawdown": max_drawdown
    }
