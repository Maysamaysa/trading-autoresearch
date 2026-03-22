"""
strategy.py — Bollinger Band strategy.
This file is edited by the OpenClaw agent each experiment.
"""

import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    # Bollinger Bands (20, 2)
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

    # EMA trend filter
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # Entry: price touches lower band + in uptrend
    df["entry"] = (
        (df["close"] <= df["bb_lower"]) &
        (df["close"] > df["ema50"])
    ).astype(int)

    # Exit: price touches upper band
    df["exit"] = (df["close"] >= df["bb_upper"]).astype(int) * -1

    return df


STOP_LOSS_PCT     = 0.025
TAKE_PROFIT_PCT   = 0.05
POSITION_SIZE_PCT = 0.10
