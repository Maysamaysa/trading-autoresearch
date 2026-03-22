#!/bin/bash
# init.sh — First-time setup for trading-autoresearch

set -e
echo ""
echo "🦞 Trading Autoresearch — Setup"
echo "════════════════════════════════"

# Install Python deps
echo ""
echo "→ Installing Python dependencies..."
pip install -r requirements.txt --quiet

# Initialise each strategy
echo "→ Initialising strategy baselines..."
for d in strategies/*/; do
  name=$(basename "$d")
  if [ ! -f "$d/best_strategy.py" ]; then
    cp "$d/strategy.py" "$d/best_strategy.py"
    echo "  ✓ $name — best_strategy.py created"
  fi
  if [ ! -f "$d/best_score.json" ]; then
    echo '{"win_rate":0.0,"sharpe":0.0,"max_drawdown":1.0}' > "$d/best_score.json"
    echo "  ✓ $name — best_score.json initialised"
  fi
  touch "$d/experiment_log.jsonl"
done

echo ""
echo "→ Done! Next steps:"
echo ""
echo "  1. Edit config.py — add your broker API key"
echo "  2. Start dashboard:  python serve_dashboard.py"
echo "  3. Run research:     python orchestrator.py --mode parallel --rounds 50"
echo "     or via OpenClaw:  openclaw agent --message \"Read strategies/rsi_macd/program.md and start researching\""
echo ""
