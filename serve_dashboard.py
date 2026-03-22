"""
serve_dashboard.py — Serves the dashboard HTML + a live /api/data endpoint.

Run:
    python serve_dashboard.py

Then open:
    http://127.0.0.1:8080
"""

import json, os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from config import DASHBOARD_HOST, DASHBOARD_PORT, STRATEGIES_DIR, INITIAL_CAPITAL

ROOT = Path(__file__).parent


def build_api_data() -> dict:
    """Read all experiment_log.jsonl files and return structured data."""
    strategies = {}
    ensemble_vote    = []
    ensemble_capital = []

    for log_file in sorted(Path(STRATEGIES_DIR).glob("*/experiment_log.jsonl")):
        name  = log_file.parent.name
        lines = [json.loads(l) for l in open(log_file) if l.strip()]
        if not lines:
            continue

        best = {}
        best_json = log_file.parent / "best_score.json"
        if best_json.exists():
            best = json.loads(best_json.read_text())

        # Build equity curves from log (last run per experiment)
        equity_points = []
        for entry in lines:
            eq = entry.get("equity", [])
            if eq:
                equity_points = eq  # use most recent non-empty

        strategies[name] = {
            "name":         name,
            "best":         best,
            "n_experiments": len(lines),
            "log":          lines[-50:],          # last 50 for log panel
            "win_rate_history": [
                e["metrics"].get("win_rate", 0)
                for e in lines if e.get("metrics")
            ],
            "equity_curve": equity_points or [INITIAL_CAPITAL],
        }

    # Ensemble logs
    vote_log = ROOT / "ensemble_vote_log.jsonl"
    if vote_log.exists():
        ensemble_vote = [json.loads(l) for l in open(vote_log) if l.strip()][-50:]

    capital_log = ROOT / "ensemble_capital_log.jsonl"
    if capital_log.exists():
        ensemble_capital = [json.loads(l) for l in open(capital_log) if l.strip()][-50:]

    return {
        "strategies":        strategies,
        "ensemble_vote":     ensemble_vote,
        "ensemble_capital":  ensemble_capital,
        "initial_capital":   INITIAL_CAPITAL,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dashboard"), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
            return super().do_GET()

        if self.path == "/api/data":
            try:
                data = build_api_data()
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(500, str(e))
            return

        return super().do_GET()

    def log_message(self, fmt, *args):
        pass  # suppress request logs for cleanliness


if __name__ == "__main__":
    server = HTTPServer((DASHBOARD_HOST, DASHBOARD_PORT), Handler)
    print(f"\n  🦞 Trading Autoresearch Dashboard")
    print(f"  Open → http://{DASHBOARD_HOST}:{DASHBOARD_PORT}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
