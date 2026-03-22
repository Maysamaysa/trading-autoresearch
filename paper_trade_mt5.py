"""
paper_trade_mt5.py — Live paper trading ผ่าน MT5 (Wine/CrossOver บน Mac)

EA เขียน candle ใหม่ → Python อ่าน → รัน strategy → ส่ง signal กลับ EA
EA รับ signal → เปิด/ปิด position บน Paper Trading account จริง

Usage:
    python paper_trade_mt5.py
    python paper_trade_mt5.py --strategy strategies/rsi_macd
    python paper_trade_mt5.py --mode vote
"""

import argparse, time, json
from pathlib import Path
from datetime import datetime, timezone

from mt5_file_connector import (
    fetch_ohlcv, send_signal, read_status, check_connection
)

ROOT         = Path(__file__).parent
STRATEGIES   = sorted(Path("strategies").glob("*/best_strategy.py"))
TRADE_LOG    = ROOT / "paper_trade_mt5_log.jsonl"


def load_strategy(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("strategy", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_signal_from_strategy(strat_path: Path, df) -> int:
    """รัน strategy บน candle ล่าสุด → return 1/0/-1"""
    try:
        strat = load_strategy(strat_path)
        out   = strat.generate_signals(df.copy())
        row   = out.iloc[-2]  # candle ก่อนสุดท้าย (ปิดแล้ว)
        entry = int(row.get("entry", row.get("signal", 0)))
        exit_ = int(row.get("exit",  0))
        if entry == 1:  return  1
        if exit_ == -1: return -1
        return 0
    except Exception as e:
        print(f"  [WARN] {strat_path.parent.name}: {e}")
        return 0


def log_trade(entry: dict):
    with open(TRADE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run(strat_paths: list, mode: str = "single", poll: int = 60):
    print(f"\n🦞 MT5 Paper Trading (Wine/CrossOver)")
    print(f"   Mode     : {mode}")
    print(f"   Strategies: {[p.parent.name for p in strat_paths]}")
    print(f"   Poll     : ทุก {poll} วินาที")
    print(f"   Log      : {TRADE_LOG}")
    print(f"   Status   : {read_status()}")
    print()

    # ตรวจ connection ก่อน
    if not check_connection():
        print("⚠️  ยังไม่พบข้อมูลจาก EA — รอ EA เริ่มส่งข้อมูล...")

    prev_candle_time = None

    while True:
        try:
            # ── อ่านข้อมูลใหม่ ──────────────────────────────────
            df = fetch_ohlcv(timeout_seconds=30)

            current_candle = df.index[-1]
            if current_candle == prev_candle_time:
                # ยังไม่มี candle ใหม่
                time.sleep(poll)
                continue

            prev_candle_time = current_candle
            price = float(df["close"].iloc[-2])  # candle ปิดล่าสุด
            ts    = datetime.now(timezone.utc).isoformat()

            print(f"\n[{ts[:19]}] candle ใหม่ — price={price:.5f}")

            # ── คำนวณ signal ─────────────────────────────────────
            if mode == "vote":
                # majority vote
                votes = [get_signal_from_strategy(p, df) for p in strat_paths]
                buy_v  = votes.count(1)
                sell_v = votes.count(-1)
                thresh = len(votes) / 2
                sig    = 1 if buy_v > thresh else (-1 if sell_v > thresh else 0)
                sig_name = {1:"BUY", 0:"HOLD", -1:"SELL"}[sig]
                print(f"  Votes: BUY={buy_v} SELL={sell_v} HOLD={votes.count(0)} → {sig_name}")

            elif mode == "best":
                # ใช้ strategy อันดับ 1 (best_score.json สูงสุด)
                sig = get_signal_from_strategy(strat_paths[0], df)
                sig_name = {1:"BUY", 0:"HOLD", -1:"SELL"}[sig]
                print(f"  [{strat_paths[0].parent.name}] → {sig_name}")

            else:
                # single strategy
                sig = get_signal_from_strategy(strat_paths[0], df)
                sig_name = {1:"BUY", 0:"HOLD", -1:"SELL"}[sig]
                print(f"  [{strat_paths[0].parent.name}] → {sig_name}")

            # ── ส่ง signal ให้ EA ────────────────────────────────
            mt5_signal = {1: "BUY", 0: "HOLD", -1: "SELL"}[sig]
            send_signal(mt5_signal)

            # ── บันทึก log ───────────────────────────────────────
            log_trade({
                "ts":     ts,
                "price":  price,
                "signal": mt5_signal,
                "mode":   mode,
            })

        except KeyboardInterrupt:
            print("\n\n⛔ Paper trading หยุดแล้ว")
            send_signal("CLOSE")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(poll)


# ── หา best strategies โดยเรียงจาก best_score.json ──────────────
def get_sorted_strategies() -> list:
    import json
    ranked = []
    for p in Path("strategies").glob("*/best_strategy.py"):
        score_file = p.parent / "best_score.json"
        wr = 0.0
        if score_file.exists():
            try:
                wr = json.loads(score_file.read_text()).get("win_rate", 0)
            except Exception:
                pass
        ranked.append((wr, p))
    ranked.sort(reverse=True)
    return [p for _, p in ranked] if ranked else list(Path("strategies").glob("*/strategy.py"))


# ── CLI ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default=None,
                        help="path ของ strategy folder เช่น strategies/rsi_macd")
    parser.add_argument("--mode", choices=["single","vote","best"], default="best",
                        help="single=1 strategy, vote=majority, best=อันดับ1 อัตโนมัติ")
    parser.add_argument("--poll", type=int, default=60,
                        help="เช็คทุกกี่วินาที (default 60)")
    args = parser.parse_args()

    if args.strategy:
        strat_py = Path(args.strategy) / "best_strategy.py"
        if not strat_py.exists():
            strat_py = Path(args.strategy) / "strategy.py"
        strats = [strat_py]
        mode   = "single"
    else:
        strats = get_sorted_strategies()
        mode   = args.mode

    run(strats, mode=mode, poll=args.poll)
