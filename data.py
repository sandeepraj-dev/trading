import pandas as pd
import yfinance as yf

def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        raise ValueError("Enter a symbol.")
    if "." not in s and not s.startswith("^"):
        s += ".NS"
    return s

def fetch_data(symbol: str, interval: str = "5m", period: str = "5d") -> pd.DataFrame:
    ticker = normalize_symbol(symbol)
    df = yf.download(
        ticker, period=period, interval=interval,
        auto_adjust=False, progress=False, threads=False
    )
    if df is None or df.empty:
        raise ValueError(
            f"No data returned for {ticker}. Check symbol, market hours and data availability."
        )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).lower() for c in df.columns]
    wanted = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in wanted if c in df.columns]].dropna(subset=["close"])
    if "volume" not in df.columns:
        df["volume"] = 0
    return df
