"""
run_experiment.py — Run one experiment iteration for a given strategy folder.

Usage:
    python run_experiment.py strategies/rsi_macd
    python run_experiment.py strategies/bollinger

The agent calls this after editing strategy.py. It:
  1. Runs the backtest
  2. Computes metrics
  3. Compares to best
  4. Keeps or reverts
  5. Appends to experiment_log.jsonl
"""

import sys, os, json, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from backtest import run_backtest, fetch_ohlcv
from metrics  import compute_metrics, is_improvement


def run(strategy_dir: str):
    strat_path = Path(strategy_dir)
    if not strat_path.exists():
        print(f"[ERROR] Strategy folder not found: {strategy_dir}")
        sys.exit(1)

    strategy_py  = strat_path / "strategy.py"
    best_py      = strat_path / "best_strategy.py"
    best_json    = strat_path / "best_score.json"
    log_file     = strat_path / "experiment_log.jsonl"

    # Load current best score
    if best_json.exists():
        best = json.loads(best_json.read_text())
    else:
        best = {"win_rate": 0.0, "sharpe": 0.0, "max_drawdown": 1.0}

    exp_num = sum(1 for _ in open(log_file)) + 1 if log_file.exists() else 1

    print(f"\n{'═'*52}")
    print(f"  {strat_path.name.upper()} · Experiment #{exp_num}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'═'*52}")

    # Run backtest
    try:
        result  = run_backtest(str(strategy_py))
        metrics = compute_metrics(result)
    except Exception as e:
        print(f"  [FAIL] Backtest error: {e}")
        entry = {
            "exp":       exp_num,
            "ts":        datetime.now(timezone.utc).isoformat(),
            "strategy":  strat_path.name,
            "improved":  False,
            "error":     str(e),
            "metrics":   {},
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return

    # Print results
    valid_label = "✓" if metrics["valid"] else "✗"
    print(f"  Trades     : {metrics['n_trades']}")
    print(f"  Win rate   : {metrics['win_rate']:.1%}")
    print(f"  Sharpe     : {metrics['sharpe']:.3f}")
    print(f"  Max DD     : {metrics['max_drawdown']:.1%}  {valid_label}")
    print(f"  Capital    : ${metrics['final_capital']:>10,.2f}")
    print(f"  Profit     : {metrics['profit_pct']:+.1%}")

    improved = is_improvement(metrics, best)

    if improved:
        shutil.copy(strategy_py, best_py)
        best_json.write_text(json.dumps(metrics, indent=2))
        print(f"\n  ✓ NEW BEST! win_rate {metrics['win_rate']:.1%}  "
              f"(was {best['win_rate']:.1%})")
    else:
        reason = metrics.get("reason") or f"no improvement over best {best['win_rate']:.1%}"
        print(f"\n  ✗ Discarded — {reason}")
        if best_py.exists():
            shutil.copy(best_py, strategy_py)
            print("  → Reverted to best_strategy.py")

    # Append to log
    entry = {
        "exp":      exp_num,
        "ts":       datetime.now(timezone.utc).isoformat(),
        "strategy": strat_path.name,
        "improved": improved,
        "metrics":  metrics,
        "equity":   result.get("equity_curve", []),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"  Log        : {log_file}  (entry #{exp_num})\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_experiment.py strategies/<name>")
        sys.exit(1)
    run(sys.argv[1])
