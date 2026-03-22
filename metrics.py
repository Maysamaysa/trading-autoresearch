"""
metrics.py — Compute performance metrics from backtest results.
"""

import numpy as np
from config import INITIAL_CAPITAL, MAX_DRAWDOWN_LIMIT, MIN_TRADES


def compute_metrics(result: dict) -> dict:
    trades = result["trades"]

    if len(trades) < MIN_TRADES:
        return {
            "win_rate":     0.0,
            "sharpe":       0.0,
            "max_drawdown": 1.0,
            "n_trades":     len(trades),
            "final_capital": result["final_capital"],
            "valid":        False,
            "reason":       f"too few trades ({len(trades)} < {MIN_TRADES})",
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [t for t in trades if t["win"]]

    win_rate = len(wins) / len(trades)
    mean_pnl = np.mean(pnls)
    std_pnl  = np.std(pnls) + 1e-9
    sharpe   = mean_pnl / std_pnl * np.sqrt(252)

    # Max drawdown from equity curve
    equity = result.get("equity_curve", [INITIAL_CAPITAL, result["final_capital"]])
    peak   = equity[0]
    max_dd = 0.0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    valid  = max_dd <= MAX_DRAWDOWN_LIMIT
    reason = "" if valid else f"drawdown {max_dd:.1%} > limit {MAX_DRAWDOWN_LIMIT:.0%}"

    return {
        "win_rate":      round(win_rate, 4),
        "sharpe":        round(sharpe, 4),
        "max_drawdown":  round(max_dd, 4),
        "n_trades":      len(trades),
        "final_capital": result["final_capital"],
        "profit_pct":    round((result["final_capital"] - INITIAL_CAPITAL) / INITIAL_CAPITAL, 4),
        "valid":         valid,
        "reason":        reason,
    }


def is_improvement(new: dict, best: dict) -> bool:
    """Return True if new metrics are better than best."""
    if not new["valid"]:
        return False
    if new["n_trades"] < MIN_TRADES:
        return False
    # Primary: win rate (must improve by >0.3%). Tiebreak: Sharpe.
    if new["win_rate"] > best.get("win_rate", 0) + 0.003:
        return True
    if abs(new["win_rate"] - best.get("win_rate", 0)) <= 0.003:
        if new["sharpe"] > best.get("sharpe", 0):
            return True
    return False
