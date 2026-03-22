"""
backtest_mt5_file.py — drop-in แทน backtest.py สำหรับ Mac M1 + Wine + MT5

แก้ run_experiment.py บรรทัดเดียว:
  จาก: from backtest          import run_backtest, fetch_ohlcv
  เป็น: from backtest_mt5_file import run_backtest, fetch_ohlcv
"""

import importlib.util
import pandas as pd
from mt5_file_connector import fetch_ohlcv_file
from config import INITIAL_CAPITAL


def fetch_ohlcv() -> pd.DataFrame:
    return fetch_ohlcv_file()


def load_strategy_module(path: str):
    spec = importlib.util.spec_from_file_location("strategy", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_backtest(strategy_py_path: str, df: pd.DataFrame = None) -> dict:
    if df is None:
        df = fetch_ohlcv_file()

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

        if position == 0 and sig == 1:
            alloc     = capital * position_size
            position  = alloc / row["close"]
            entry_px  = row["close"]
            entry_atr = float(row.get("atr", row["close"] * 0.01))
            capital  -= alloc

        elif position > 0:
            pnl_pct = (row["close"] - entry_px) / entry_px

            if stop_atr_mult and "atr" in row:
                sl_hit = pnl_pct <= -(stop_atr_mult * entry_atr / entry_px)
            elif stop_loss_pct:
                sl_hit = pnl_pct <= -stop_loss_pct
            else:
                sl_hit = pnl_pct <= -0.02

            tp_hit   = pnl_pct >= take_profit_pct
            sig_exit = int(row.get("exit", row.get("signal", 0))) == -1

            if sl_hit or tp_hit or sig_exit:
                capital += position * row["close"]
                trades.append({
                    "entry":   entry_px,
                    "exit":    row["close"],
                    "pnl_pct": round(pnl_pct, 6),
                    "win":     pnl_pct > 0,
                    "exit_ts": str(ts),
                    "reason":  "sl" if sl_hit else ("tp" if tp_hit else "signal"),
                })
                position = 0.0

        equity.append(capital + (position * row["close"] if position > 0 else 0))

    return {
        "trades":        trades,
        "final_capital": round(capital, 2),
        "equity_curve":  [round(e, 2) for e in equity[::max(1, len(equity)//200)]],
    }
