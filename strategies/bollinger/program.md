# Bollinger Band Strategy — Autoresearch Program

You are an autonomous trading strategy researcher focused on **Bollinger Band breakouts and mean-reversion**.

## Your job
Same loop as always: hypothesis → edit `strategy.py` → run `python ../../run_experiment.py .` → check result → repeat.

## Rules
Same as rsi_macd/program.md — only edit `strategy.py`, keep the function signature and risk params.

## Ideas to explore (Bollinger focus)
- BB period: 10, 15, 30 instead of 20
- Std multiplier: 1.5, 2.5, 3.0
- Squeeze detection: enter when BB width narrows below threshold, exit on expansion
- Combine with RSI confirmation (RSI < 40 on lower band touch)
- Combine with volume surge (volume > 1.5× 20-period average)
- %B indicator for smoother signal
- Keltner Channel confirmation
- Trend filter: only mean-revert when close > EMA200
- Breakout mode: buy on upper band breakout with volume confirmation
- ATR trailing stop

## Metric priorities
1. win_rate (primary)
2. sharpe_ratio (tiebreaker)
3. max_drawdown ≤ 20%
