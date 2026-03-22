"""
mt5_file_connector.py
─────────────────────
อ่านข้อมูล OHLCV จากไฟล์ CSV ที่ MT5 EA (AutoresearchBridge.mq5) เขียนออกมา
ทำงานบน Mac M1 ได้เลย — ไม่ต้องใช้ MetaTrader5 Python library

Flow:
  MT5 (Wine) → เขียน candles.csv ทุก 60 วิ → Python (native) อ่านไฟล์นี้
"""

import pandas as pd
from pathlib import Path
import time

# ── โหลด config ──────────────────────────────────────────────────────────────
try:
    import mt5_config as cfg
    MT5_FILES_PATH    = getattr(cfg, "MT5_FILES_PATH", "")
    MT5_SUBFOLDER     = getattr(cfg, "MT5_EA_SUBFOLDER", "autoresearch")
    MT5_SYMBOL        = getattr(cfg, "MT5_SYMBOL", "BTCUSDm")
    MT5_BACKTEST_DAYS = getattr(cfg, "MT5_BACKTEST_DAYS", 90)
except ImportError:
    MT5_FILES_PATH    = ""
    MT5_SUBFOLDER     = "autoresearch"
    MT5_SYMBOL        = "BTCUSDm"
    MT5_BACKTEST_DAYS = 90


def find_mt5_files_folder() -> Path:
    """หา MT5 Files folder อัตโนมัติบน Mac (Wine / CrossOver)"""
    home = Path.home()
    patterns = [
        # CrossOver
        "Library/Application Support/CrossOver/Bottles/*/drive_c/users/*/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Files",
        # Wine homebrew
        ".wine/drive_c/users/*/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Files",
        # Wine other prefix
        "Library/Application Support/Wine/prefixes/*/drive_c/users/*/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Files",
    ]
    for pat in patterns:
        found = sorted(home.glob(pat))
        if found:
            return found[0]
    raise FileNotFoundError(
        "หา MT5 Files folder ไม่เจออัตโนมัติ\n"
        "แก้ MT5_FILES_PATH ใน mt5_config.py ให้ชี้ไปที่\n"
        "  MT5 → File → Open Data Folder → MQL5/Files\n"
    )


def get_data_dir() -> Path:
    if MT5_FILES_PATH and Path(MT5_FILES_PATH).exists():
        base = Path(MT5_FILES_PATH)
    else:
        base = find_mt5_files_folder()

    data_dir = base / MT5_SUBFOLDER
    if not data_dir.exists():
        raise FileNotFoundError(
            f"ไม่พบโฟลเดอร์ '{MT5_SUBFOLDER}' ใน {base}\n"
            f"EA จะสร้างโฟลเดอร์นี้เองเมื่อทำงานครั้งแรก\n"
            f"ตรวจสอบว่า AutoresearchBridge EA Attach ลง chart แล้ว"
        )
    return data_dir


def fetch_ohlcv_file() -> pd.DataFrame:
    data_dir   = get_data_dir()
    candle_csv = data_dir / "candles.csv"

    if not candle_csv.exists():
        raise FileNotFoundError(
            f"ไม่พบ {candle_csv}\n"
            f"ตรวจสอบว่า AutoresearchBridge.mq5 EA:\n"
            f"  1. Compile แล้ว (ไม่มี error ใน Toolbox)\n"
            f"  2. Attach ลง chart {MT5_SYMBOL} H1 แล้ว\n"
            f"  3. เปิด Allow writing files ใน EA Properties"
        )

    age = time.time() - candle_csv.stat().st_mtime
    if age > 300:
        print(f"  ⚠️  candles.csv เก่า {age/60:.0f} นาที — EA ยังทำงานอยู่ไหม?")

    df = pd.read_csv(candle_csv, parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    cutoff = df.index.max() - pd.Timedelta(days=MT5_BACKTEST_DAYS)
    df = df[df.index >= cutoff].copy()

    print(f"  [MT5 File] {len(df)} candles  "
          f"({df.index[0].date()} → {df.index[-1].date()})")
    return df


def fetch_tick_file() -> dict:
    try:
        tick_csv = get_data_dir() / "tick.csv"
        if not tick_csv.exists():
            return {}
        df = pd.read_csv(tick_csv)
        if df.empty:
            return {}
        r = df.iloc[0]
        return {
            "timestamp": str(r["timestamp"]),
            "bid":    float(r["bid"]),
            "ask":    float(r["ask"]),
            "spread": float(r["spread"]),
            "mid":    (float(r["bid"]) + float(r["ask"])) / 2,
        }
    except Exception as e:
        print(f"  [tick] {e}")
        return {}


# drop-in replacement
def fetch_ohlcv() -> pd.DataFrame:
    return fetch_ohlcv_file()


if __name__ == "__main__":
    print("\n🦞 MT5 File Connector — ทดสอบ\n")
    try:
        d = get_data_dir()
        print(f"  MT5 Files: {d}\n")
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}"); exit(1)

    df = fetch_ohlcv_file()
    print(df.tail().to_string())

    tick = fetch_tick_file()
    if tick:
        print(f"\n  Tick: bid={tick['bid']}  ask={tick['ask']}  spread={tick['spread']}")
