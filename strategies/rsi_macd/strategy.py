"""
strategy.py — RSI + MACD strategy.
This file is edited by the OpenClaw agent each experiment.
Only this file should be changed — not backtest.py or metrics.py.
"""

import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input:  OHLCV DataFrame indexed by timestamp
    Output: same DataFrame with columns 'entry' (1=buy) and 'exit' (-1=sell)
    """
    # RSI(14)
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

    # MACD(12,26,9)
    ema12       = df["close"].ewm(span=12, adjust=False).mean()
    ema26       = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]  = ema12 - ema26
    df["msig"]  = df["macd"].ewm(span=9, adjust=False).mean()

    # Signals
    df["entry"] = ((df["rsi"] < 30) & (df["macd"] > df["msig"])).astype(int)
    df["exit"]  = (df["rsi"] > 70).astype(int) * -1

    return df


# Risk parameters — agent may tune these
STOP_LOSS_PCT    = 0.02   # 2% stop loss
TAKE_PROFIT_PCT  = 0.04   # 4% take profit
POSITION_SIZE_PCT = 0.10  # 10% of capital per trade
