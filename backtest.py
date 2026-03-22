"""
backtest.py — Fixed backtesting engine. NEVER modified by agents.
Fetches OHLCV from broker API, runs strategy signals, simulates trades.
"""

import importlib.util
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import ccxt
except ImportError:
    raise SystemExit("Run: pip install -r requirements.txt")

from config import (
    BROKER_ID, BROKER_API_KEY, BROKER_API_SECRET,
    SYMBOL, TIMEFRAME, BACKTEST_DAYS, INITIAL_CAPITAL,
)


def fetch_ohlcv() -> pd.DataFrame:
    """Fetch historical candles from broker via ccxt."""
    exchange_class = getattr(ccxt, BROKER_ID)
    exchange = exchange_class({
        "apiKey": BROKER_API_KEY,
        "secret": BROKER_API_SECRET,
        "enableRateLimit": True,
    })
    since = exchange.parse8601(
        (datetime.utcnow() - timedelta(days=BACKTEST_DAYS))
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    raw = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=5000)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df.set_index("timestamp").sort_index()


def load_strategy_module(strategy_py_path: str):
    """Dynamically load a strategy.py from a given path."""
    spec = importlib.util.spec_from_file_location("strategy", strategy_py_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_backtest(strategy_py_path: str, df: pd.DataFrame = None) -> dict:
    """
    Run a full backtest for the strategy file at strategy_py_path.
    Returns dict with trades list and final capital.
    Optionally pass pre-fetched df to avoid repeated API calls.
    """
    if df is None:
        df = fetch_ohlcv()

    strat = load_strategy_module(strategy_py_path)
    df    = strat.generate_signals(df.copy())

    stop_loss_pct   = getattr(strat, "STOP_LOSS_PCT",      None)
    stop_atr_mult   = getattr(strat, "STOP_LOSS_ATR_MULT", None)
    take_profit_pct = getattr(strat, "TAKE_PROFIT_PCT",    0.04)
    position_size   = getattr(strat, "POSITION_SIZE_PCT",  0.10)

    capital   = float(INITIAL_CAPITAL)
    position  = 0.0
    entry_px  = 0.0
    entry_atr = 0.0
    trades    = []
    equity    = [capital]

    for ts, row in df.iterrows():
        sig = int(row.get("entry", row.get("signal", 0)))

        # ── ENTRY ──────────────────────────────────────────
        if position == 0 and sig == 1:
            alloc     = capital * position_size
            position  = alloc / row["close"]
            entry_px  = row["close"]
            entry_atr = float(row.get("atr", row["close"] * 0.01))
            capital  -= alloc

        # ── EXIT ────────────────────────────────────────────
        elif position > 0:
            pnl_pct = (row["close"] - entry_px) / entry_px

            # Determine stop loss
            if stop_atr_mult and "atr" in row:
                sl_hit = pnl_pct <= -(stop_atr_mult * entry_atr / entry_px)
            elif stop_loss_pct:
                sl_hit = pnl_pct <= -stop_loss_pct
            else:
                sl_hit = pnl_pct <= -0.02

            tp_hit   = pnl_pct >= take_profit_pct
            sig_exit = int(row.get("exit", row.get("signal", 0))) == -1

            if sl_hit or tp_hit or sig_exit:
                exit_value = position * row["close"]
                capital   += exit_value
                trades.append({
                    "entry":    entry_px,
                    "exit":     row["close"],
                    "pnl_pct":  round(pnl_pct, 6),
                    "win":      pnl_pct > 0,
                    "exit_ts":  str(ts),
                    "reason":   "sl" if sl_hit else ("tp" if tp_hit else "signal"),
                })
                position = 0.0

        equity.append(capital + (position * row["close"] if position > 0 else 0))

    return {
        "trades":        trades,
        "final_capital": round(capital, 2),
        "equity_curve":  [round(e, 2) for e in equity[::max(1, len(equity)//200)]],  # downsample to 200pts
    }
