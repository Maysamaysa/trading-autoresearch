"""
mt5_connector.py — MT5 data connector for trading-autoresearch.

รองรับ 2 โหมด (เลือกใน config.py):

  MT5_MODE = "bridge"   ← แนะนำสำหรับ Mac M1
                           MT5 รันบน Windows VPS/PC
                           Mac เรียกข้อมูลผ่าน HTTP REST
                           ติดตั้ง mt5_bridge_server.py บน Windows ด้วย

  MT5_MODE = "direct"  ← ถ้ารัน Python บน Windows เครื่องเดียวกับ MT5
                           ใช้ MetaTrader5 library โดยตรง
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ── โหลด config ──────────────────────────────────────────────────────────────
try:
    from mt5_config import (
        MT5_MODE,
        MT5_SYMBOL, MT5_TIMEFRAME, MT5_BACKTEST_DAYS,
        MT5_BRIDGE_URL,
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER,
    )
except ImportError:
    raise SystemExit(
        "[ERROR] ไม่พบ mt5_config.py\n"
        "        คัดลอก mt5_config.example.py → mt5_config.py แล้วกรอกข้อมูล"
    )

# ── timeframe map ────────────────────────────────────────────────────────────
# MT5 timeframe constants (ใช้ทั้ง direct และ bridge)
TF_MAP = {
    "M1":  1,    "M5":  5,    "M15": 15,   "M30": 30,
    "H1":  16385, "H4": 16388, "D1":  16408,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  MODE: bridge  (Mac → HTTP → Windows VPS running mt5_bridge_server.py)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_bridge() -> pd.DataFrame:
    """ดึง OHLCV จาก MT5 bridge server ที่รันบน Windows"""
    try:
        import requests
    except ImportError:
        raise SystemExit("ติดตั้ง requests ก่อน: pip install requests")

    url    = f"{MT5_BRIDGE_URL.rstrip('/')}/ohlcv"
    params = {
        "symbol":   MT5_SYMBOL,
        "timeframe": MT5_TIMEFRAME,
        "days":     MT5_BACKTEST_DAYS,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        raise ConnectionError(
            f"[MT5 Bridge] เชื่อมต่อไม่ได้: {e}\n"
            f"  URL: {url}\n"
            f"  ตรวจสอบว่า mt5_bridge_server.py รันอยู่บน Windows VPS หรือยัง"
        )

    data = resp.json()
    df   = pd.DataFrame(data["candles"],
                        columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp").sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  MODE: direct  (Windows เครื่องเดียวกับ MT5)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_direct() -> pd.DataFrame:
    """ดึง OHLCV โดยตรงจาก MT5 terminal บน Windows"""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        raise SystemExit(
            "ติดตั้ง MetaTrader5 library ก่อน: pip install MetaTrader5\n"
            "(รองรับ Windows เท่านั้น — บน Mac ให้ใช้ MT5_MODE = 'bridge')"
        )

    # เชื่อมต่อ MT5
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        raise ConnectionError(f"[MT5 Direct] initialize() ล้มเหลว: {mt5.last_error()}")

    tf_const  = TF_MAP.get(MT5_TIMEFRAME, TF_MAP["H1"])
    date_from = datetime.utcnow() - timedelta(days=MT5_BACKTEST_DAYS)
    date_to   = datetime.utcnow()

    rates = mt5.copy_rates_range(MT5_SYMBOL, tf_const, date_from, date_to)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise ValueError(
            f"[MT5 Direct] ไม่มีข้อมูล rates สำหรับ {MT5_SYMBOL}\n"
            f"  ตรวจสอบชื่อ symbol ใน Market Watch ของ MT5"
        )

    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={"tick_volume": "volume"})[
        ["timestamp","open","high","low","close","volume"]
    ]
    return df.set_index("timestamp").sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API  (backtest.py เรียก fetch_ohlcv_mt5 แทน fetch_ohlcv)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_ohlcv_mt5() -> pd.DataFrame:
    """
    ฟังก์ชันหลัก — ดึงข้อมูล OHLCV จาก MT5
    เลือก mode อัตโนมัติจาก MT5_MODE ใน mt5_config.py
    """
    print(f"  [MT5] fetching {MT5_SYMBOL} {MT5_TIMEFRAME} ({MT5_BACKTEST_DAYS}d) "
          f"via {MT5_MODE.upper()}...")

    if MT5_MODE == "bridge":
        df = _fetch_bridge()
    elif MT5_MODE == "direct":
        df = _fetch_direct()
    else:
        raise ValueError(f"MT5_MODE ไม่รู้จัก: '{MT5_MODE}' (ต้องเป็น 'bridge' หรือ 'direct')")

    # Validate
    required = {"open","high","low","close","volume"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"[MT5] ข้อมูลไม่ครบ columns: {missing}")

    print(f"  [MT5] ได้ {len(df)} candles  "
          f"({df.index[0].date()} → {df.index[-1].date()})")
    return df
