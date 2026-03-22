//+------------------------------------------------------------------+
//| PaperBridge.mq5                                                  |
//| EA สำหรับ bridge ระหว่าง MT5 กับ Python autoresearch             |
//| ติดตั้ง: copy ไฟล์นี้ไปที่                                       |
//|   MT5 → File → Open Data Folder → MQL5 → Experts               |
//| แล้วกด Compile (F7) และลาก EA ไปวางบน chart                     |
//+------------------------------------------------------------------+
#property copyright "Trading Autoresearch"
#property version   "1.0"
#property strict

input string   Symbol_Name    = "";          // ปล่อยว่าง = ใช้ symbol ปัจจุบัน
input ENUM_TIMEFRAMES TF      = PERIOD_H1;   // timeframe
input int      Candles        = 500;         // จำนวน candle ที่ export
input double   Lot_Size       = 0.01;        // lot size สำหรับ paper trade
input int      Poll_Seconds   = 10;          // เช็ค signal ทุกกี่วินาที

// ── paths (Wine จะ map เป็น path บน Mac อัตโนมัติ) ──────────────
string data_file   = "C:\\mt5_bridge\\ohlcv.csv";
string signal_file = "C:\\mt5_bridge\\signal.txt";
string status_file = "C:\\mt5_bridge\\status.txt";

string sym;
datetime last_export = 0;
datetime last_signal = 0;
int      ticket      = -1;

//+------------------------------------------------------------------+
int OnInit()
{
   sym = (Symbol_Name == "") ? _Symbol : Symbol_Name;

   // สร้าง folder (Wine map C:\ → ~/.wine/drive_c/)
   // Python จะอ่านจาก path นี้
   WriteStatus("EA started | symbol=" + sym +
               " | tf=" + EnumToString(TF) +
               " | lot=" + DoubleToString(Lot_Size, 2));

   ExportOHLCV();
   EventSetTimer(Poll_Seconds);
   Print("🦞 PaperBridge EA started — symbol: ", sym);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteStatus("EA stopped");
}

//+------------------------------------------------------------------+
void OnTimer()
{
   // Export OHLCV ทุกครั้งที่มี candle ใหม่
   datetime current_bar = iTime(sym, TF, 0);
   if (current_bar != last_export)
   {
      ExportOHLCV();
      last_export = current_bar;
   }

   // อ่าน signal จาก Python
   ReadAndExecuteSignal();
}

//+------------------------------------------------------------------+
void ExportOHLCV()
{
   int fh = FileOpen(data_file, FILE_WRITE | FILE_CSV | FILE_COMMON, ',');
   if (fh == INVALID_HANDLE)
   {
      Print("[ERROR] เปิดไฟล์ไม่ได้: ", data_file);
      return;
   }

   // Header
   FileWrite(fh, "timestamp,open,high,low,close,volume");

   // ดึง candles ย้อนหลัง
   for (int i = Candles - 1; i >= 0; i--)
   {
      datetime ts     = iTime  (sym, TF, i);
      double   o      = iOpen  (sym, TF, i);
      double   h      = iHigh  (sym, TF, i);
      double   l      = iLow   (sym, TF, i);
      double   c      = iClose (sym, TF, i);
      long     v      = iVolume(sym, TF, i);

      FileWrite(fh,
         TimeToString(ts, TIME_DATE | TIME_SECONDS),
         DoubleToString(o, _Digits),
         DoubleToString(h, _Digits),
         DoubleToString(l, _Digits),
         DoubleToString(c, _Digits),
         IntegerToString(v)
      );
   }

   FileClose(fh);
   WriteStatus("exported " + IntegerToString(Candles) +
               " candles | last_bar=" + TimeToString(iTime(sym, TF, 0)));
}

//+------------------------------------------------------------------+
void ReadAndExecuteSignal()
{
   if (!FileIsExist(signal_file, FILE_COMMON)) return;

   int fh = FileOpen(signal_file, FILE_READ | FILE_TXT | FILE_COMMON);
   if (fh == INVALID_HANDLE) return;

   string line = FileReadString(fh);
   FileClose(fh);
   FileDelete(signal_file, FILE_COMMON);  // ลบทิ้งหลังอ่านแล้ว

   line = StringTrimRight(StringTrimLeft(line));
   if (line == "") return;

   // Parse: "BUY" / "SELL" / "CLOSE" / "HOLD"
   string sig = line;
   StringToUpper(sig);

   Print("📨 Signal received: ", sig);

   if (sig == "BUY")
   {
      // ปิด short ก่อน (ถ้ามี)
      ClosePosition(ORDER_TYPE_SELL);
      // เปิด long
      OpenPosition(ORDER_TYPE_BUY);
   }
   else if (sig == "SELL")
   {
      ClosePosition(ORDER_TYPE_BUY);
      OpenPosition(ORDER_TYPE_SELL);
   }
   else if (sig == "CLOSE")
   {
      ClosePosition(ORDER_TYPE_BUY);
      ClosePosition(ORDER_TYPE_SELL);
   }
   // HOLD = ไม่ทำอะไร
}

//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE order_type)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = sym;
   req.volume    = Lot_Size;
   req.type      = order_type;
   req.price     = (order_type == ORDER_TYPE_BUY)
                   ? SymbolInfoDouble(sym, SYMBOL_ASK)
                   : SymbolInfoDouble(sym, SYMBOL_BID);
   req.deviation = 20;
   req.magic     = 20250322;
   req.comment   = "autoresearch";
   req.type_filling = ORDER_FILLING_IOC;

   if (!OrderSend(req, res))
      Print("[ERROR] OrderSend ล้มเหลว: ", res.retcode, " | ", res.comment);
   else
      Print("✅ ", EnumToString(order_type), " opened | ticket=", res.order);
}

//+------------------------------------------------------------------+
void ClosePosition(ENUM_ORDER_TYPE pos_type)
{
   for (int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if (!PositionSelectByTicket(ticket)) continue;
      if (PositionGetString(POSITION_SYMBOL) != sym) continue;

      ENUM_POSITION_TYPE pt = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      if ((pos_type == ORDER_TYPE_BUY  && pt != POSITION_TYPE_BUY)  ||
          (pos_type == ORDER_TYPE_SELL && pt != POSITION_TYPE_SELL)) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = sym;
      req.volume    = PositionGetDouble(POSITION_VOLUME);
      req.type      = (pt == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price     = (req.type == ORDER_TYPE_BUY)
                      ? SymbolInfoDouble(sym, SYMBOL_ASK)
                      : SymbolInfoDouble(sym, SYMBOL_BID);
      req.deviation = 20;
      req.magic     = 20250322;
      req.comment   = "autoresearch-close";
      req.type_filling = ORDER_FILLING_IOC;
      req.position  = ticket;

      if (!OrderSend(req, res))
         Print("[ERROR] Close ล้มเหลว: ", res.retcode);
      else
         Print("🔴 Position closed | ticket=", ticket);
   }
}

//+------------------------------------------------------------------+
void WriteStatus(string msg)
{
   int fh = FileOpen(status_file, FILE_WRITE | FILE_TXT | FILE_COMMON);
   if (fh == INVALID_HANDLE) return;
   FileWriteString(fh, TimeToString(TimeCurrent()) + " | " + msg + "\n");
   FileClose(fh);
}
