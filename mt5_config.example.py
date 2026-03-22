# mt5_config.py
# ─────────────────────────────────────────────────────────────────────
#  คัดลอกไฟล์นี้เป็น mt5_config.py แล้วแก้ค่า
#  Setup: Mac M1 + Wine/CrossOver + Exness Paper Trading
# ─────────────────────────────────────────────────────────────────────

MT5_MODE          = "file"       # file = อ่าน CSV ที่ EA เขียน (Mac+Wine)
MT5_SYMBOL        = "BTCUSDm"    # Exness Crypto มี m ต่อท้าย
MT5_TIMEFRAME     = "H1"
MT5_BACKTEST_DAYS = 90

# ปล่อยว่าง = หาอัตโนมัติ
# ถ้าหาไม่เจอ: MT5 → File → Open Data Folder → copy path ของ MQL5/Files
MT5_FILES_PATH    = ""
MT5_EA_SUBFOLDER  = "autoresearch"

# Bridge/Direct (ไม่ใช้ในโหมด file)
MT5_BRIDGE_URL    = "http://localhost:5000"
MT5_LOGIN         = 0
MT5_PASSWORD      = ""
MT5_SERVER        = ""
