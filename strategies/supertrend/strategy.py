"""
strategy.py — Supertrend strategy.
This file is edited by the OpenClaw agent each experiment.
"""

import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    # ATR(10)
    high, low, close = df["high"], df["low"], df["close"]
    tr  = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(10).mean()
    df["atr"] = atr

    # Supertrend bands
    mult         = 3.0
    hl2          = (high + low) / 2
    upper_band   = hl2 + mult * atr
    lower_band   = hl2 - mult * atr

    supertrend   = pd.Series(index=df.index, dtype=float)
    direction    = pd.Series(index=df.index, dtype=int)

    for i in range(1, len(df)):
        prev_upper = upper_band.iloc[i - 1]
        prev_lower = lower_band.iloc[i - 1]
        prev_close = close.iloc[i - 1]
        prev_st    = supertrend.iloc[i - 1] if i > 1 else lower_band.iloc[0]

        # Adjust bands
        curr_upper = upper_band.iloc[i]
        curr_lower = lower_band.iloc[i]
        if curr_upper > prev_upper or prev_close > prev_upper:
            curr_upper = curr_upper
        else:
            curr_upper = prev_upper

        if curr_lower < prev_lower or prev_close < prev_lower:
            curr_lower = curr_lower
        else:
            curr_lower = prev_lower

        upper_band.iloc[i] = curr_upper
        lower_band.iloc[i] = curr_lower

        if prev_st == prev_upper:
            if close.iloc[i] <= curr_upper:
                supertrend.iloc[i] = curr_upper
                direction.iloc[i]  = -1
            else:
                supertrend.iloc[i] = curr_lower
                direction.iloc[i]  = 1
        else:
            if close.iloc[i] >= curr_lower:
                supertrend.iloc[i] = curr_lower
                direction.iloc[i]  = 1
            else:
                supertrend.iloc[i] = curr_upper
                direction.iloc[i]  = -1

    df["supertrend"] = supertrend
    df["st_dir"]     = direction

    # Signals: direction flip
    df["entry"] = ((df["st_dir"] == 1)  & (df["st_dir"].shift() == -1)).astype(int)
    df["exit"]  = ((df["st_dir"] == -1) & (df["st_dir"].shift() == 1)).astype(int) * -1

    return df


STOP_LOSS_ATR_MULT = 2.0
TAKE_PROFIT_PCT    = 0.06
POSITION_SIZE_PCT  = 0.10
