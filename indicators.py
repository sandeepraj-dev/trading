import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, SMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = [str(c).lower() for c in d.columns]

    d["ema9"] = EMAIndicator(d["close"], window=9).ema_indicator()
    d["ema20"] = EMAIndicator(d["close"], window=20).ema_indicator()
    d["ema50"] = EMAIndicator(d["close"], window=50).ema_indicator()
    d["sma200"] = SMAIndicator(d["close"], window=200).sma_indicator()

    d["rsi"] = RSIIndicator(d["close"], window=14).rsi()

    macd = MACD(d["close"], window_slow=26, window_fast=12, window_sign=9)
    d["macd"] = macd.macd()
    d["macd_signal"] = macd.macd_signal()
    d["macd_hist"] = macd.macd_diff()

    bb = BollingerBands(d["close"], window=20, window_dev=2)
    d["bb_high"] = bb.bollinger_hband()
    d["bb_mid"] = bb.bollinger_mavg()
    d["bb_low"] = bb.bollinger_lband()

    d["atr"] = AverageTrueRange(
        d["high"], d["low"], d["close"], window=14
    ).average_true_range()

    d["adx"] = ADXIndicator(
        d["high"], d["low"], d["close"], window=14
    ).adx()

    typical = (d["high"] + d["low"] + d["close"]) / 3
    dates = pd.Series(d.index.date, index=d.index)
    pv = typical * d["volume"]
    d["vwap"] = pv.groupby(dates).cumsum() / d["volume"].groupby(dates).cumsum()

    d["volume_ma20"] = d["volume"].rolling(20).mean()
    d["volume_ratio"] = d["volume"] / d["volume_ma20"]
    d["prev_high_20"] = d["high"].rolling(20).max().shift(1)
    d["prev_low_20"] = d["low"].rolling(20).min().shift(1)

    return d.replace([np.inf, -np.inf], np.nan)

def signal_columns(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()

    d["sig_vwap"] = 0
    d.loc[(d.close > d.vwap) & (d.close > d.open), "sig_vwap"] = 1
    d.loc[(d.close < d.vwap) & (d.close < d.open), "sig_vwap"] = -1

    d["sig_ema"] = 0
    d.loc[(d.ema9 > d.ema20) & (d.close > d.ema20), "sig_ema"] = 1
    d.loc[(d.ema9 < d.ema20) & (d.close < d.ema20), "sig_ema"] = -1

    d["sig_momentum"] = 0
    d.loc[(d.rsi >= 55) & (d.macd > d.macd_signal), "sig_momentum"] = 1
    d.loc[(d.rsi <= 45) & (d.macd < d.macd_signal), "sig_momentum"] = -1

    d["sig_breakout"] = 0
    d.loc[(d.close > d.prev_high_20) & (d.volume_ratio >= 1.2), "sig_breakout"] = 1
    d.loc[(d.close < d.prev_low_20) & (d.volume_ratio >= 1.2), "sig_breakout"] = -1

    d["sig_pullback"] = 0
    d.loc[(d.close > d.ema20) & d.rsi.between(45, 65), "sig_pullback"] = 1
    d.loc[(d.close < d.ema20) & d.rsi.between(35, 55), "sig_pullback"] = -1

    d["sig_bollinger"] = 0
    d.loc[d.close > d.bb_high, "sig_bollinger"] = 1
    d.loc[d.close < d.bb_low, "sig_bollinger"] = -1

    d["sig_adx"] = 0
    d.loc[(d.adx >= 20) & (d.close > d.ema20), "sig_adx"] = 1
    d.loc[(d.adx >= 20) & (d.close < d.ema20), "sig_adx"] = -1

    d["combined_score"] = (
        2*d.sig_vwap + 2*d.sig_ema + 2*d.sig_momentum +
        2*d.sig_breakout + d.sig_pullback + d.sig_bollinger + d.sig_adx
    )
    d["combined_signal"] = 0
    d.loc[d.combined_score >= 5, "combined_signal"] = 1
    d.loc[d.combined_score <= -5, "combined_signal"] = -1
    return d
