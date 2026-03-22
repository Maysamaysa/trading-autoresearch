//+------------------------------------------------------------------+
//| AutoresearchBridge.mq5                                           |
//| วางไฟล์นี้ใน: MT5 → File → Open Data Folder                     |
//|   → MQL5 → Experts → AutoresearchBridge.mq5                     |
//| แล้ว Compile และ Attach ลงบน Chart BTCUSD H1                    |
//+------------------------------------------------------------------+
#property copyright "trading-autoresearch"
#property version   "1.00"
#property strict

//── inputs ──────────────────────────────────────────────────────────
input string   Symbol_      = "BTCUSDm";   // ชื่อ symbol ใน Exness (มักมี m ต่อท้าย)
input ENUM_TIMEFRAMES TF    = PERIOD_H1;   // timeframe
input int      HistoryDays  = 90;          // จำนวนวันย้อนหลัง
input int      ExportEvery  = 60;          // export ทุก N วินาที
input string   DataFolder   = "autoresearch"; // โฟลเดอร์ใน MT5 Files

//── globals ─────────────────────────────────────────────────────────
datetime g_last_export = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("AutoresearchBridge: เริ่มต้นแล้ว symbol=", Symbol_, " tf=", EnumToString(TF));
   ExportAll();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(TimeCurrent() - g_last_export >= ExportEvery)
   {
      ExportAll();
      g_last_export = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
void ExportAll()
{
   ExportCandles();
   ExportTick();
   Print("AutoresearchBridge: exported @ ", TimeToString(TimeCurrent()));
}

//── Export OHLCV candles ────────────────────────────────────────────
void ExportCandles()
{
   int bars = iBars(Symbol_, TF);
   int want = (int)MathMin(bars - 1, HistoryDays * 24); // H1 = 24 bars/day

   string path = DataFolder + "\\candles.csv";
   int fh = FileOpen(path, FILE_WRITE | FILE_CSV | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE) {
      Print("AutoresearchBridge: ไม่สามารถเปิดไฟล์ได้: ", path, " error=", GetLastError());
      return;
   }

   // header
   FileWrite(fh, "timestamp", "open", "high", "low", "close", "volume");

   // เขียนจากเก่าไปใหม่ (index สูง = เก่ากว่า)
   for(int i = want - 1; i >= 1; i--)
   {
      datetime t = iTime(Symbol_,   TF, i);
      double   o = iOpen(Symbol_,   TF, i);
      double   h = iHigh(Symbol_,   TF, i);
      double   l = iLow(Symbol_,    TF, i);
      double   c = iClose(Symbol_,  TF, i);
      long     v = iVolume(Symbol_,  TF, i);

      FileWrite(fh,
         TimeToString(t, TIME_DATE|TIME_MINUTES),
         DoubleToString(o, 2),
         DoubleToString(h, 2),
         DoubleToString(l, 2),
         DoubleToString(c, 2),
         IntegerToString(v)
      );
   }

   FileClose(fh);
}

//── Export live tick (bid/ask/spread) ──────────────────────────────
void ExportTick()
{
   string path = DataFolder + "\\tick.csv";
   int fh = FileOpen(path, FILE_WRITE | FILE_CSV | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE) return;

   MqlTick tick;
   if(SymbolInfoTick(Symbol_, tick))
   {
      FileWrite(fh, "timestamp", "bid", "ask", "last", "spread");
      double spread = (tick.ask - tick.bid) / SymbolInfoDouble(Symbol_, SYMBOL_POINT);
      FileWrite(fh,
         TimeToString(tick.time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
         DoubleToString(tick.bid, 2),
         DoubleToString(tick.ask, 2),
         DoubleToString(tick.last, 2),
         DoubleToString(spread, 1)
      );
   }

   FileClose(fh);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("AutoresearchBridge: หยุดทำงาน reason=", reason);
}
//+------------------------------------------------------------------+
