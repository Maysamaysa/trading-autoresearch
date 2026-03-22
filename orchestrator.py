"""
orchestrator.py — Multi-strategy competition orchestrator.

Modes (pick per run):
  parallel          Each strategy researches independently in its own thread.
                    Agents don't know about each other. Best of N wins overall.

  capital_allocation One agent allocates capital across strategies based on
                    their current win_rate scores. Better strategies get more
                    capital weight. Re-balances every round.

  majority_vote     All strategies generate signals on the same candle.
                    Only trade when a majority (2/3+) agree on direction.
                    Logged as a virtual "ensemble" strategy.

Usage:
    python orchestrator.py --mode parallel
    python orchestrator.py --mode capital_allocation
    python orchestrator.py --mode majority_vote
    python orchestrator.py --mode parallel --rounds 50
"""

import argparse, json, shutil, threading, time, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from backtest import fetch_ohlcv, run_backtest, load_strategy_module
from metrics  import compute_metrics, is_improvement
from config   import STRATEGIES_DIR, INITIAL_CAPITAL


STRATEGY_DIRS = sorted(Path(STRATEGIES_DIR).glob("*/strategy.py"))


# ── helpers ──────────────────────────────────────────────────────────────────

def load_best_score(strat_dir: Path) -> dict:
    p = strat_dir / "best_score.json"
    return json.loads(p.read_text()) if p.exists() else {"win_rate": 0.0, "sharpe": 0.0}


def append_log(strat_dir: Path, entry: dict):
    with open(strat_dir / "experiment_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def exp_count(strat_dir: Path) -> int:
    p = strat_dir / "experiment_log.jsonl"
    return sum(1 for _ in open(p)) if p.exists() else 0


# ── MODE 1: parallel ─────────────────────────────────────────────────────────

def run_parallel(rounds: int):
    """Each strategy runs independently in its own thread."""
    print(f"\n[PARALLEL MODE] {len(STRATEGY_DIRS)} strategies · {rounds} rounds each\n")

    def worker(strategy_py: Path):
        import subprocess
        for _ in range(rounds):
            subprocess.run(
                [sys.executable, "run_experiment.py", str(strategy_py.parent)],
                cwd=ROOT,
            )

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in STRATEGY_DIRS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("\n[PARALLEL] All rounds complete. Leaderboard:")
    _print_leaderboard()


# ── MODE 2: capital_allocation ───────────────────────────────────────────────

def run_capital_allocation(rounds: int):
    """
    Allocate capital proportionally to each strategy's win_rate.
    After each round, re-balance weights. Log a combined equity curve.
    """
    print(f"\n[CAPITAL ALLOCATION MODE] {rounds} rounds\n")
    df = fetch_ohlcv()  # shared data for all strategies

    combined_log = ROOT / "ensemble_capital_log.jsonl"

    for r in range(1, rounds + 1):
        scores = {}
        results = {}

        for s in STRATEGY_DIRS:
            strat_dir = s.parent
            try:
                result  = run_backtest(str(s), df=df.copy())
                metrics = compute_metrics(result)
                scores[strat_dir.name]  = metrics
                results[strat_dir.name] = result

                best = load_best_score(strat_dir)
                improved = is_improvement(metrics, best)
                if improved:
                    shutil.copy(s, strat_dir / "best_strategy.py")
                    (strat_dir / "best_score.json").write_text(json.dumps(metrics, indent=2))

                append_log(strat_dir, {
                    "exp":      exp_count(strat_dir) + 1,
                    "ts":       datetime.now(timezone.utc).isoformat(),
                    "strategy": strat_dir.name,
                    "improved": improved,
                    "metrics":  metrics,
                    "mode":     "capital_allocation",
                    "round":    r,
                })
            except Exception as e:
                print(f"  [{strat_dir.name}] ERROR: {e}")
                scores[strat_dir.name] = {"win_rate": 0.0, "sharpe": 0.0, "valid": False}

        # Compute capital weights
        total_wr = sum(max(v["win_rate"], 0.01) for v in scores.values() if v.get("valid", True))
        weights  = {
            k: max(v["win_rate"], 0.01) / total_wr
            for k, v in scores.items()
        }

        combined_profit = sum(
            weights.get(k, 0) * results[k]["final_capital"]
            for k in results
        ) if results else INITIAL_CAPITAL

        entry = {
            "round":    r,
            "ts":       datetime.now(timezone.utc).isoformat(),
            "weights":  weights,
            "scores":   {k: v for k, v in scores.items()},
            "combined_capital": round(combined_profit, 2),
        }
        with open(combined_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"\n  Round {r}/{rounds} · Combined capital ${combined_profit:,.0f}")
        for k, w in sorted(weights.items(), key=lambda x: -x[1]):
            wr = scores[k].get("win_rate", 0)
            print(f"    {k:<20} weight={w:.1%}  win_rate={wr:.1%}")

    print("\n[CAPITAL ALLOCATION] Done.")
    _print_leaderboard()


# ── MODE 3: majority_vote ────────────────────────────────────────────────────

def run_majority_vote(rounds: int):
    """
    All strategies vote on each candle. Trade only on 2/3+ agreement.
    Logs a virtual 'ensemble' strategy result.
    """
    print(f"\n[MAJORITY VOTE MODE] {rounds} rounds\n")

    import pandas as pd
    df = fetch_ohlcv()

    ensemble_log = ROOT / "ensemble_vote_log.jsonl"
    best_ensemble_score = {"win_rate": 0.0, "sharpe": 0.0}

    for r in range(1, rounds + 1):
        signal_frames = []
        for s in STRATEGY_DIRS:
            try:
                strat = load_strategy_module(str(s))
                sdf   = strat.generate_signals(df.copy())
                col   = sdf.get("entry", sdf.get("signal", pd.Series(0, index=sdf.index)))
                signal_frames.append(col.rename(s.parent.name))
            except Exception as e:
                print(f"  [{s.parent.name}] signal error: {e}")

        if not signal_frames:
            continue

        votes     = pd.concat(signal_frames, axis=1).fillna(0)
        threshold = len(signal_frames) / 2  # majority = > half
        df_vote   = df.copy()
        df_vote["entry"]  = (votes.sum(axis=1) > threshold).astype(int)
        df_vote["exit"]   = (votes.sum(axis=1) < -threshold).astype(int) * -1
        df_vote["signal"] = df_vote["entry"]  # compat

        # Simulate on ensemble signals
        from backtest import run_backtest
        # Write temp strategy
        tmp = ROOT / "_tmp_vote_strategy.py"
        tmp.write_text(
            "import pandas as pd\n"
            "def generate_signals(df):\n"
            "    return df\n"
            "STOP_LOSS_PCT    = 0.02\n"
            "TAKE_PROFIT_PCT  = 0.04\n"
            "POSITION_SIZE_PCT = 0.10\n"
        )
        # Inject pre-computed signals
        from backtest import load_strategy_module as lsm
        strat_mod = lsm(str(tmp))
        strat_mod.generate_signals = lambda d: df_vote  # monkey-patch

        capital  = float(INITIAL_CAPITAL)
        position = 0.0
        entry_px = 0.0
        trades   = []
        equity   = [capital]

        for ts, row in df_vote.iterrows():
            sig = int(row.get("entry", 0))
            if position == 0 and sig == 1:
                alloc    = capital * 0.10
                position = alloc / row["close"]
                entry_px = row["close"]
                capital -= alloc
            elif position > 0:
                pnl_pct = (row["close"] - entry_px) / entry_px
                if pnl_pct <= -0.02 or pnl_pct >= 0.04 or int(row.get("exit", 0)) == -1:
                    capital += position * row["close"]
                    trades.append({"pnl_pct": pnl_pct, "win": pnl_pct > 0})
                    position = 0.0
            equity.append(capital + (position * row["close"] if position > 0 else 0))

        result  = {"trades": trades, "final_capital": capital, "equity_curve": equity[::max(1,len(equity)//200)]}
        metrics = compute_metrics(result)

        improved = is_improvement(metrics, best_ensemble_score)
        if improved:
            best_ensemble_score = metrics

        entry = {
            "round":    r,
            "ts":       datetime.now(timezone.utc).isoformat(),
            "metrics":  metrics,
            "improved": improved,
            "n_voters": len(signal_frames),
        }
        with open(ensemble_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        tmp.unlink(missing_ok=True)

        print(f"  Round {r}/{rounds} · ensemble win_rate={metrics['win_rate']:.1%} "
              f"sharpe={metrics['sharpe']:.2f}  {'✓ NEW BEST' if improved else ''}")

    print("\n[MAJORITY VOTE] Done. Best ensemble:", best_ensemble_score)


# ── leaderboard ──────────────────────────────────────────────────────────────

def _print_leaderboard():
    print("\n  ── Leaderboard ──────────────────────────")
    rows = []
    for s in STRATEGY_DIRS:
        sc = load_best_score(s.parent)
        rows.append((s.parent.name, sc))
    for name, sc in sorted(rows, key=lambda x: -x[1].get("win_rate", 0)):
        print(f"  {name:<22} wr={sc.get('win_rate',0):.1%}  "
              f"sharpe={sc.get('sharpe',0):.2f}  "
              f"dd={sc.get('max_drawdown',0):.1%}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-strategy orchestrator")
    parser.add_argument("--mode",   choices=["parallel","capital_allocation","majority_vote"],
                        default="parallel")
    parser.add_argument("--rounds", type=int, default=20,
                        help="Experiments per strategy (parallel) or total rounds")
    args = parser.parse_args()

    if args.mode == "parallel":
        run_parallel(args.rounds)
    elif args.mode == "capital_allocation":
        run_capital_allocation(args.rounds)
    elif args.mode == "majority_vote":
        run_majority_vote(args.rounds)
