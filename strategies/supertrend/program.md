# Supertrend Strategy — Autoresearch Program

You are an autonomous trading strategy researcher focused on **Supertrend and volatility-adaptive signals**.

## Your job
Hypothesis → edit `strategy.py` → run `python ../../run_experiment.py .` → check result → repeat. Aim for 50+ experiments.

## Ideas to explore (Supertrend focus)
- ATR period: 7, 14, 20 instead of 10
- Multiplier: 1.5, 2.0, 2.5, 3.5, 4.0
- Combine with EMA trend filter (only trade in direction of EMA200)
- Add RSI confirmation on entry (RSI > 50 for longs)
- Volume filter: require above-average volume on signal candle
- Use Supertrend as trailing stop only, enter on RSI/MACD signal
- Dual Supertrend (fast + slow) — only enter when both agree
- Combine with VWAP: only buy when price is above VWAP
- Add ADX filter: only trade when ADX > 20 (trending market)
- Chandelier exit as alternative to supertrend bands

## Rules
Only edit `strategy.py`. Keep `generate_signals(df)` signature with `entry`/`exit` columns.
You may use `STOP_LOSS_ATR_MULT` (ATR-based) instead of `STOP_LOSS_PCT`.
Max drawdown limit: 20%. Min trades: 10.
