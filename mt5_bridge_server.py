"""
mt5_bridge_server.py — รันไฟล์นี้บน Windows (VPS หรือ PC) ที่ติดตั้ง MT5

Python บน Mac จะเรียกมาที่ http://VPS_IP:5000/ohlcv
แล้ว bridge นี้จะดึงข้อมูลจาก MT5 terminal ให้

ติดตั้งบน Windows:
    pip install flask MetaTrader5

รัน:
    python mt5_bridge_server.py

เปิด port 5000 บน Windows Firewall ด้วย (ถ้าใช้ VPS)
"""

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import MetaTrader5 as mt5

app = Flask(__name__)

# ── MT5 login ─────────────────────────────────────────────────
# แก้ค่าเหล่านี้ตามบัญชีโบรกเกอร์
MT5_LOGIN    = 123456789
MT5_PASSWORD = "your_password"
MT5_SERVER   = "YourBroker-Server"

TF_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}


def connect():
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        raise RuntimeError(f"MT5 initialize() ล้มเหลว: {mt5.last_error()}")


# ── GET /ohlcv ────────────────────────────────────────────────
@app.route("/ohlcv")
def get_ohlcv():
    symbol    = request.args.get("symbol",    "BTCUSD")
    timeframe = request.args.get("timeframe", "H1")
    days      = int(request.args.get("days",  90))

    try:
        connect()
        tf_const  = TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)
        date_from = datetime.utcnow() - timedelta(days=days)
        date_to   = datetime.utcnow()

        rates = mt5.copy_rates_range(symbol, tf_const, date_from, date_to)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            return jsonify({"error": f"ไม่มีข้อมูล: {symbol}"}), 404

        import pandas as pd
        df = pd.DataFrame(rates)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s").astype(str)
        df = df.rename(columns={"tick_volume": "volume"})

        candles = df[["timestamp","open","high","low","close","volume"]].values.tolist()
        return jsonify({
            "symbol":    symbol,
            "timeframe": timeframe,
            "days":      days,
            "count":     len(candles),
            "candles":   candles,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GET /health ───────────────────────────────────────────────
@app.route("/health")
def health():
    try:
        connect()
        info = mt5.terminal_info()
        mt5.shutdown()
        return jsonify({
            "status":    "ok",
            "terminal":  info.name if info else "unknown",
            "connected": True,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── GET /tick ─────────────────────────────────────────────────
@app.route("/tick")
def get_tick():
    """ราคาปัจจุบัน (ใช้สำหรับ paper trading)"""
    symbol = request.args.get("symbol", "BTCUSD")
    try:
        connect()
        tick = mt5.symbol_info_tick(symbol)
        mt5.shutdown()
        if tick is None:
            return jsonify({"error": f"ไม่พบ symbol: {symbol}"}), 404
        return jsonify({
            "symbol": symbol,
            "bid":    tick.bid,
            "ask":    tick.ask,
            "time":   str(datetime.utcfromtimestamp(tick.time)),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n🦞 MT5 Bridge Server")
    print("   รันบน Windows เครื่องนี้")
    print("   Mac เรียกได้ที่ http://THIS_PC_IP:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
