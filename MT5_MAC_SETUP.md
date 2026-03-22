# 🦞 เชื่อม MT5 กับ Autoresearch — Mac M1 + Exness Paper Trading

## ภาพรวม

```
MT5 (Wine/CrossOver บน Mac)
  └── AutoresearchBridge EA
        └── เขียน candles.csv + tick.csv ทุก 60 วิ
              ↓
Python (native Mac M1)
  └── mt5_file_connector.py อ่าน CSV
        └── backtest → autoresearch loop → dashboard
```

ไม่ต้องใช้ MetaTrader5 Python library เลย — ทำงานผ่านไฟล์ CSV ธรรมดา

---

## ขั้นตอนที่ 1 — ติดตั้ง EA ใน MT5

### 1.1 เปิด MT5 Data Folder
```
MT5 → File → Open Data Folder
```
จะได้โฟลเดอร์เช่น:
```
C:\users\user\AppData\Roaming\MetaQuotes\Terminal\XXXXX\
```

### 1.2 คัดลอก EA ไปที่ MT5
- ไปที่โฟลเดอร์ `MQL5\Experts\`
- คัดลอก `AutoresearchBridge.mq5` จาก project นี้ไปวาง

### 1.3 Compile EA
- เปิด MetaEditor: MT5 → Tools → MetaEditor (F4)
- เปิดไฟล์ `AutoresearchBridge.mq5`
- กด Compile (F7)
- ต้องไม่มี error (warning โอเค)

### 1.4 ตั้งค่า Symbol สำหรับ Exness
เปิด MT5 → View → Market Watch → หา BTC
Exness Paper Trading ใช้ชื่อ: **`BTCUSDm`** (มี m ต่อท้าย)

### 1.5 Attach EA ลง Chart
- เปิด chart BTCUSDm H1
- Navigator → Expert Advisors → AutoresearchBridge → ลากลง chart
- ตั้งค่า inputs:
  ```
  Symbol_     = BTCUSDm
  TF          = H1
  HistoryDays = 90
  ExportEvery = 60
  DataFolder  = autoresearch
  ```
- กด OK

### 1.6 เปิดสิทธิ์ EA
- กด Auto Trading (ปุ่มบน toolbar — ต้องเป็นสีเขียว)
- EA Properties → Common:
  - ✅ Allow DLL imports
  - ✅ Allow modification of Signal settings

หลังจากนั้น 60 วินาที EA จะสร้างไฟล์:
```
MQL5/Files/autoresearch/candles.csv
MQL5/Files/autoresearch/tick.csv
```

---

## ขั้นตอนที่ 2 — ตั้งค่า Python

### 2.1 คัดลอก config
```bash
cd trading-autoresearch
cp mt5_config.example.py mt5_config.py
```

### 2.2 แก้ mt5_config.py
```python
MT5_MODE          = "file"
MT5_SYMBOL        = "BTCUSDm"   # ตรงกับ Market Watch
MT5_TIMEFRAME     = "H1"
MT5_BACKTEST_DAYS = 90
MT5_FILES_PATH    = ""           # ปล่อยว่าง = หาอัตโนมัติ
MT5_EA_SUBFOLDER  = "autoresearch"
```

### 2.3 ติดตั้ง dependencies
```bash
pip install -r requirements.txt
```

### 2.4 ทดสอบเชื่อมต่อ
```bash
python mt5_file_connector.py
```

ถ้าสำเร็จจะเห็น:
```
🦞 MT5 File Connector — ทดสอบ

  MT5 Files: /Users/you/Library/Application Support/CrossOver/...

  [MT5 File] 2160 candles  (2025-12-12 → 2026-03-22)

                      open     high      low    close  volume
timestamp
2026-03-21 20:00  83241.00  83890.00  82100.00  83456.00    1823
...

  Tick: bid=83456.00  ask=83460.00  spread=4.0
```

---

## ขั้นตอนที่ 3 — รัน

### Paper Trading (ดูสัญญาณ real-time)
```bash
python paper_trade_mt5.py
# หรือ majority vote
python paper_trade_mt5.py --mode vote
```

output:
```
🦞 MT5 Paper Trading — Exness Demo
   Strategies : 4
   Mode       : all independent

  [14:30:00] rsi_macd          ⚪ HOLD  bid=83456  ask=83460
  [14:30:00] bollinger         🟢 BUY   bid=83456  ask=83460
  [14:30:00] ema_trend         ⚪ HOLD  bid=83456  ask=83460
  [14:30:00] supertrend        ⚪ HOLD  bid=83456  ask=83460
```

### Autoresearch (ให้ AI หา strategy ที่ดีขึ้น)
```bash
# แก้ run_experiment.py บรรทัด import ก่อน:
# from backtest import run_backtest, fetch_ohlcv
# → from backtest_mt5_file import run_backtest, fetch_ohlcv

python orchestrator.py --mode parallel --rounds 50
```

### Dashboard
```bash
python serve_dashboard.py
# เปิด http://127.0.0.1:8080
```

---

## แก้ปัญหาที่พบบ่อย

### ❌ หา MT5 Files folder ไม่เจอ
```python
# mt5_config.py — ใส่ path ตรงๆ
MT5_FILES_PATH = "/Users/ชื่อคุณ/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/XXXXX/MQL5/Files"
```
วิธีหา path: MT5 → File → Open Data Folder → ไปดูที่ MQL5/Files → copy path

### ❌ candles.csv ไม่ถูกสร้าง
1. ตรวจ EA ทำงานอยู่ไหม — Chart ต้องมีสัญลักษณ์ EA มุมขวาบน
2. กด Auto Trading ให้เป็นสีเขียว
3. ดู Toolbox → Experts tab — ต้องเห็น log จาก AutoresearchBridge

### ❌ candles.csv เก่ามาก (EA หยุด)
- EA หยุดเมื่อ MT5 ถูกปิดหรือ Wine crash
- เปิด MT5 ใหม่แล้ว Attach EA อีกครั้ง

### ❌ Symbol "BTCUSD" ไม่พบ
- Exness ใช้ `BTCUSDm` (มี m)
- เช็คใน Market Watch → Right-click → Show All → หา BTC

---

## Tips สำหรับ Exness Paper Trading

| Symbol    | ชื่อใน MT5    |
|-----------|--------------|
| Bitcoin   | BTCUSDm      |
| Ethereum  | ETHUSDm      |
| Gold      | XAUUSDm      |
| EUR/USD   | EURUSDm      |

Paper Trading บน Exness = Demo Account ราคาเหมือน live แต่ไม่ใช่เงินจริง เหมาะสำหรับทดสอบ strategy ก่อน live
