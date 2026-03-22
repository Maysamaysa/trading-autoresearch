# RSI + MACD Strategy — Autoresearch Program

You are an autonomous trading strategy researcher focused on **RSI and MACD-based signals**.

## Your job
1. Read `strategy.py` in this folder.
2. Form a hypothesis for improvement (e.g. tweak RSI thresholds, add MACD histogram filter, try ATR-based stop).
3. Edit `strategy.py` with your change.
4. Run: `python ../../run_experiment.py .`
5. Read the output. If improved — great, note it and move on to the next hypothesis.
   If not improved — the file is reverted automatically. Try something different.
6. Repeat. Aim for 50+ experiments per session.

## Rules
- **Only edit `strategy.py`** — never touch `backtest.py`, `metrics.py`, or `run_experiment.py`.
- Keep `generate_signals(df)` returning a DataFrame with `entry` (1=buy) and `exit` (-1=sell) columns.
- Keep `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`, `POSITION_SIZE_PCT` defined (you can change the values).
- You may add `STOP_LOSS_ATR_MULT` instead of `STOP_LOSS_PCT` for ATR-based stops — backtest.py supports both.
- Do not exceed 20% drawdown — experiments breaching this are auto-discarded.
- At least 10 trades must be generated.

## Ideas to explore (RSI/MACD focus)
- RSI period: try 7, 9, 21 instead of 14
- RSI thresholds: 25/75, 28/72, 35/65
- MACD params: (5,13,4), (8,17,9), (19,39,9)
- Combine RSI oversold with MACD histogram turning positive
- Add EMA(50) or EMA(200) trend filter — only buy in uptrend
- Volume spike confirmation
- ATR-based dynamic stop loss (1.5×, 2×, 2.5× ATR)
- Time-of-day filter (avoid low-liquidity hours)
- Divergence detection (price lower low, RSI higher low)

## Metric priorities
1. **win_rate** (primary) — must improve by >0.3% to be kept
2. **sharpe_ratio** (tiebreaker)
3. **max_drawdown** must stay ≤ 20%

## Current best
Check `best_score.json` before starting to know the baseline to beat.
