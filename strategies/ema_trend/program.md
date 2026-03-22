# EMA Trend Following — Autoresearch Program

You are an autonomous trading strategy researcher focused on **EMA crossovers and trend-following**.

## Your job
Hypothesis → edit `strategy.py` → run `python ../../run_experiment.py .` → read result → repeat. Aim for 50+ experiments.

## Ideas to explore (EMA/trend focus)
- EMA pairs: (5,13), (9,21), (20,50), (50,200)
- Triple EMA: fast/mid/slow — only trade when all aligned
- ADX threshold: 15, 25, 30 (filter weak trends)
- Add Parabolic SAR as trailing stop
- VWAP as additional filter (only buy above VWAP)
- Combine with RSI — exit when RSI overbought
- Heikin-Ashi candles for smoother signals
- ATR-based trailing stop (1.5× to 3× ATR)
- Higher timeframe trend filter (check EMA on 4h)
- Chandelier exit

## Rules
Only edit `strategy.py`. Keep `generate_signals(df)` returning entry/exit columns + keep risk params.
