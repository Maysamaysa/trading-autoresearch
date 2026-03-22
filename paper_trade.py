"""
paper_trade.py — Live paper trading mode.
Fetches real-time candles every N minutes, runs all strategy signals,
logs alerts WITHOUT placing real orders. Safe to run 24/7.

Usage:
    python paper_trade.py
    python paper_trade.py --strategy strategies/rsi_macd
    python paper_trade.py --mode vote   # majority vote across all strategies
"""

import argparse, json, time, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from backtest import fetch_ohlcv, load_strategy_module
from config   import SYMBOL, TIMEFRAME, STRATEGIES_DIR, INITIAL_CAPITAL

ALERT_LOG = ROOT / "paper_trade_log.jsonl"
POLL_SECONDS = 60  # check every 60s (adjust to your timeframe)


def get_latest_candle():
    """Fetch the most recent closed candle."""
    df = fetch_ohlcv()
    return df.iloc[-2]  # use second-to-last (last candle may be unclosed)


def run_strategy_signal(strategy_py: Path, candle) -> int:
    """Return 1 (buy), -1 (sell), 0 (hold) for the latest candle."""
    import pandas as pd
    df = fetch_ohlcv()
    strat = load_strategy_module(str(strategy_py))
    df    = strat.generate_signals(df.copy())
    row   = df.iloc[-2]
    entry = int(row.get("entry", row.get("signal", 0)))
    exit_ = int(row.get("exit",  0))
    if entry == 1:  return  1
    if exit_  == -1: return -1
    return 0


def log_alert(alert: dict):
    with open(ALERT_LOG, "a") as f:
        f.write(json.dumps(alert) + "\n")
    ts   = alert["ts"].split("T")[1][:8]
    sig  = {1: "🟢 BUY", -1: "🔴 SELL", 0: "⚪ HOLD"}[alert["signal"]]
    print(f"  [{ts}] {alert['strategy']:<20} {sig}  {SYMBOL} @ {alert['price']:.2f}")


def mode_single(strategy_dir: str):
    strat_py = Path(strategy_dir) / "strategy.py"
    name     = Path(strategy_dir).name
    print(f"\n🦞 Paper trading: {name}  ({SYMBOL} {TIMEFRAME})")
    print(f"   Log → {ALERT_LOG}\n")

    while True:
        try:
            candle = get_latest_candle()
            sig    = run_strategy_signal(strat_py, candle)
            alert  = {
                "ts":       datetime.now(timezone.utc).isoformat(),
                "strategy": name,
                "signal":   sig,
                "price":    float(candle["close"]),
                "symbol":   SYMBOL,
            }
            log_alert(alert)
        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(POLL_SECONDS)


def mode_all():
    strat_dirs = sorted(Path(STRATEGIES_DIR).glob("*/strategy.py"))
    names      = [s.parent.name for s in strat_dirs]
    print(f"\n🦞 Paper trading ALL strategies  ({SYMBOL} {TIMEFRAME})")
    print(f"   Strategies: {', '.join(names)}")
    print(f"   Log → {ALERT_LOG}\n")

    while True:
        try:
            for sp in strat_dirs:
                candle = get_latest_candle()
                sig    = run_strategy_signal(sp, candle)
                alert  = {
                    "ts":       datetime.now(timezone.utc).isoformat(),
                    "strategy": sp.parent.name,
                    "signal":   sig,
                    "price":    float(candle["close"]),
                    "symbol":   SYMBOL,
                }
                log_alert(alert)
        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(POLL_SECONDS)


def mode_vote():
    strat_dirs = sorted(Path(STRATEGIES_DIR).glob("*/strategy.py"))
    print(f"\n🦞 Paper trading MAJORITY VOTE  ({SYMBOL} {TIMEFRAME})")
    print(f"   {len(strat_dirs)} strategies voting\n")

    while True:
        try:
            votes = []
            price = None
            for sp in strat_dirs:
                candle = get_latest_candle()
                price  = float(candle["close"])
                votes.append(run_strategy_signal(sp, candle))

            buy_votes  = votes.count(1)
            sell_votes = votes.count(-1)
            threshold  = len(votes) / 2

            if buy_votes > threshold:
                sig = 1
            elif sell_votes > threshold:
                sig = -1
            else:
                sig = 0

            alert = {
                "ts":         datetime.now(timezone.utc).isoformat(),
                "strategy":   "majority_vote",
                "signal":     sig,
                "price":      price,
                "symbol":     SYMBOL,
                "votes":      votes,
                "buy_votes":  buy_votes,
                "sell_votes": sell_votes,
            }
            log_alert(alert)

        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper trading monitor")
    parser.add_argument("--strategy", default=None,
                        help="Path to a strategy folder (e.g. strategies/rsi_macd). "
                             "Omit to run all strategies.")
    parser.add_argument("--mode", choices=["all", "vote"], default=None,
                        help="'all' = run each strategy independently. "
                             "'vote' = majority vote signal.")
    args = parser.parse_args()

    try:
        if args.strategy:
            mode_single(args.strategy)
        elif args.mode == "vote":
            mode_vote()
        else:
            mode_all()
    except KeyboardInterrupt:
        print("\n\nPaper trading stopped.")
