# 🦞 Trading Autoresearch

An autoresearch loop for trading strategies, inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch), powered by [OpenClaw](https://github.com/openclaw/openclaw).

Instead of training an LLM, an AI agent iterates on trading strategies overnight — editing, backtesting, measuring, and keeping improvements automatically.

---

## Setup

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Edit config.py — add your broker API key and set SYMBOL
nano config.py

# 3. Initialise each strategy's best score
for d in strategies/*/; do
  cp "$d/strategy.py" "$d/best_strategy.py"
  echo '{"win_rate":0,"sharpe":0,"max_drawdown":1}' > "$d/best_score.json"
done

# 4. Install OpenClaw
npm install -g openclaw@latest
openclaw onboard
```

---

## Running strategies

### Single strategy (agent edits one strategy.py)
```bash
# Point your OpenClaw agent at a strategy folder:
openclaw agent --message "Read strategies/rsi_macd/program.md and start researching"
```

### Multi-strategy orchestrator

Pick a competition mode per run:

```bash
# Mode 1: parallel — each strategy researches independently
python orchestrator.py --mode parallel --rounds 50

# Mode 2: capital allocation — better strategies get more capital weight
python orchestrator.py --mode capital_allocation --rounds 20

# Mode 3: majority vote — strategies vote on each candle
python orchestrator.py --mode majority_vote --rounds 20
```

---

## Dashboard

```bash
python serve_dashboard.py
# Open → http://127.0.0.1:8080
```

The dashboard auto-refreshes every 10 seconds and shows:
- Live win rate & Sharpe per strategy
- Equity curves for all strategies
- Experiment iteration log
- Strategy comparison table
- Ensemble results (capital allocation / majority vote)

---

## Project structure

```
trading-autoresearch/
├── config.py               ← broker API key, symbol, timeframe
├── backtest.py             ← fixed engine (never edited by agents)
├── metrics.py              ← compute win rate, Sharpe, drawdown
├── run_experiment.py       ← single experiment loop
├── orchestrator.py         ← multi-strategy competition modes
├── serve_dashboard.py      ← localhost dashboard server
├── dashboard/
│   └── index.html          ← dashboard UI
└── strategies/
    ├── rsi_macd/
    │   ├── strategy.py     ← agent edits this
    │   ├── best_strategy.py← saved when improved
    │   ├── best_score.json
    │   ├── experiment_log.jsonl
    │   └── program.md      ← agent instructions
    ├── bollinger/
    └── ema_trend/
```

---

## How it works

| autoresearch (karpathy) | This project |
|---|---|
| `train.py` — agent edits | `strategy.py` — agent edits |
| `prepare.py` — fixed | `backtest.py` — fixed |
| val_bpb metric | win_rate + Sharpe ratio |
| 5-min training budget | 90-day backtest window |
| `program.md` — human edits | `program.md` — per strategy |

---

## Adding a new strategy

```bash
mkdir strategies/my_strategy
cp strategies/rsi_macd/strategy.py strategies/my_strategy/
cp strategies/rsi_macd/program.md  strategies/my_strategy/
# edit strategy.py and program.md to match your new approach
echo '{"win_rate":0,"sharpe":0,"max_drawdown":1}' > strategies/my_strategy/best_score.json
cp strategies/my_strategy/strategy.py strategies/my_strategy/best_strategy.py
```

---

## ⚠️ Risk warning

Backtested results do not guarantee live performance. Always paper-trade a strategy for 2–4 weeks before going live. Use read-only API keys during the research phase.
