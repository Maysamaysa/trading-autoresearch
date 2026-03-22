# 🦞 วิธีเชื่อม MT5 กับ Trading Autoresearch

## เลือกวิธีที่เหมาะกับคุณ

---

## วิธีที่ 1 — Windows VPS + Bridge (แนะนำสำหรับ Mac M1)

```
Mac M1 (autoresearch) ──HTTP──► Windows VPS (MT5 + bridge server)
```

### ขั้นตอน

**บน Windows VPS:**
```bash
# ติดตั้ง Python dependencies
pip install flask MetaTrader5 pandas

# แก้ login ใน mt5_bridge_server.py บรรทัด 28-30
MT5_LOGIN    = 123456789        # หมายเลขบัญชี MT5 จริง
MT5_PASSWORD = "your_password"
MT5_SERVER   = "ICMarkets-Demo" # ชื่อ server โบรกเกอร์

# รัน bridge server
python mt5_bridge_server.py
# จะเห็น: Running on http://0.0.0.0:5000
```

**เปิด Windows Firewall port 5000:**
```
Windows Defender Firewall → Inbound Rules → New Rule
→ Port → TCP 5000 → Allow
```

**บน Mac:**
```bash
# คัดลอก config template
cp mt5_config.example.py mt5_config.py

# แก้ mt5_config.py
MT5_MODE      = "bridge"
MT5_SYMBOL    = "BTCUSD"      # ตรงกับ Market Watch ใน MT5
MT5_TIMEFRAME = "H1"
MT5_BRIDGE_URL = "http://YOUR_VPS_IP:5000"  # ← ใส่ IP จริง

# ทดสอบเชื่อมต่อ
python -c "from mt5_connector import fetch_ohlcv_mt5; df = fetch_ohlcv_mt5(); print(df.tail())"
```

**เปลี่ยน backtest engine เป็น MT5:**
```bash
# แก้ run_experiment.py บรรทัด import (บรรทัดประมาณ 15)
# จาก:
from backtest import run_backtest, fetch_ohlcv
# เป็น:
from backtest_mt5 import run_backtest, fetch_ohlcv
```

**รัน autoresearch ปกติ:**
```bash
python orchestrator.py --mode parallel --rounds 50
```

---

## วิธีที่ 2 — Windows เครื่องเดียวกับ MT5 (Direct)

ถ้ามี Windows PC แยก หรือรัน Python บน Windows โดยตรง

```bash
# ติดตั้ง
pip install MetaTrader5 pandas numpy

# แก้ mt5_config.py
MT5_MODE     = "direct"
MT5_LOGIN    = 123456789
MT5_PASSWORD = "your_password"
MT5_SERVER   = "ICMarkets-Demo"
MT5_SYMBOL   = "BTCUSD"

# ทดสอบ
python -c "from mt5_connector import fetch_ohlcv_mt5; print(fetch_ohlcv_mt5().tail())"
```

---

## วิธีที่ 3 — Mac + Wine/CrossOver (ขั้นสูง ไม่แนะนำ)

MetaTrader5 Python library ไม่รองรับ Mac โดยตรง
ถ้าจะลองใช้ Wine ต้องติดตั้ง CrossOver ($50) หรือ Wine HQ ฟรี
แล้วรัน MT5 Windows app บน Mac จากนั้นใช้ MT5_MODE = "direct"
**แต่มักมีปัญหา** — แนะนำ VPS แทน

---

## ชื่อ Symbol ที่ถูกต้องสำหรับ Crypto บน MT5

ชื่อ symbol แตกต่างกันตามโบรกเกอร์ ดูใน **Market Watch** ของ MT5 ตัวเอง:

| โบรกเกอร์ | Bitcoin | Ethereum |
|---|---|---|
| ICMarkets | BTCUSD | ETHUSD |
| Exness | BTCUSD | ETHUSD |
| XM | BTCUSD | ETHUSD |
| FBS | BTCUSD. (มีจุด) | ETHUSD. |
| Pepperstone | BTCUSD | ETHUSD |

ถ้าไม่แน่ใจ: เปิด MT5 → View → Market Watch → ดูชื่อที่ตรงกับที่ต้องการ

---

## ทดสอบ Bridge Server

```bash
# ดู health ของ bridge
curl http://YOUR_VPS_IP:5000/health

# ดูราคาปัจจุบัน
curl "http://YOUR_VPS_IP:5000/tick?symbol=BTCUSD"

# ดึง OHLCV 90 วัน
curl "http://YOUR_VPS_IP:5000/ohlcv?symbol=BTCUSD&timeframe=H1&days=90"
```

---

## VPS แนะนำราคาถูก

| Provider | Spec | ราคา/เดือน |
|---|---|---|
| **Contabo** | 4 vCPU, 4GB RAM, Windows | ~$14 |
| **Vultr** | 1 vCPU, 2GB RAM, Windows | ~$16 |
| **DigitalOcean** | 1 vCPU, 2GB RAM | ~$12 + Windows license |
| **AWS Lightsail** | 2 vCPU, 4GB RAM, Windows | ~$20 |

MT5 ใช้ RAM น้อยมาก 4GB เกินพอสำหรับ MT5 + bridge server
