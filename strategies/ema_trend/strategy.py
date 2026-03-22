"""
strategy.py — EMA Trend Following strategy.
This file is edited by the OpenClaw agent each experiment.
"""

import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    # EMA crossover
    df["ema_fast"] = df["close"].ewm(span=9,  adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=21, adjust=False).mean()

    # ADX for trend strength
    high, low, close = df["high"], df["low"], df["close"]
    tr   = pd.concat([high - low,
                      (high - close.shift()).abs(),
                      (low  - close.shift()).abs()], axis=1).max(axis=1)
    dm_p = ((high - high.shift()) > (low.shift() - low)).astype(float) * (high - high.shift()).clip(lower=0)
    dm_n = ((low.shift() - low) > (high - high.shift())).astype(float) * (low.shift() - low).clip(lower=0)

    tr14   = tr.rolling(14).sum()
    df["adx"] = (
        ((dm_p.rolling(14).sum() - dm_n.rolling(14).sum()).abs() / (tr14 + 1e-9)) * 100
    ).rolling(14).mean()

    # Signals
    cross_up   = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift() <= df["ema_slow"].shift())
    cross_down = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift() >= df["ema_slow"].shift())

    df["entry"] = (cross_up  & (df["adx"] > 20)).astype(int)
    df["exit"]  = cross_down.astype(int) * -1

    return df


STOP_LOSS_PCT     = 0.03
TAKE_PROFIT_PCT   = 0.06
POSITION_SIZE_PCT = 0.10
