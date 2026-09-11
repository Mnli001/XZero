# PROJECT ZERO — AI-Powered SMC/ICT Order Flow Trading Terminal

Real-time SMC/ICT market-structure terminal with a quant confluence layer, an
advisory AI reviewer (RAG over a curated knowledge base), server-side risk
enforcement, walk-forward backtesting, and a three-mode execution pipeline.

> **No hype, by design:** the system never shows performance numbers without
> real backtest/paper/live data behind them, never promises entry accuracy, and
> cannot enable Live Auto until a strategy proves itself through the Backtest
> Gate (≥30 OOS trades + ≥30 paper trades, both with positive expectancy).

## Layout

```
backend/   FastAPI gateway + mt5_bridge + smc_analyzer + confluence_engine
           + ai_reasoning + risk_manager + backtest_engine
           + execution_modes + journal_logger   (33 pytest green)
frontend/  Next.js terminal: Overview · Live · Backtest · Strategies
           · Risk · Journal · Knowledge
docs/      ARCHITECTURE · DEPLOYMENT · API · STRATEGY_GUIDE
```

## Quickstart (dev — MT5 mock mode, full pipeline works without a broker)

```bash
# 1. backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/make_sample_csv.py /tmp/EURUSD_M5_SYNTHETIC.csv
python scripts/run_backtest.py /tmp/EURUSD_M5_SYNTHETIC.csv EURUSD M5  # exit 2 = gate honestly failed on random data
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000  # docs at /docs

# 2. frontend (new shell)
cd frontend
npm install
npm run dev   # http://localhost:3000 — /api/* proxied to :8000
```

## Production split (read this before going live)

`MetaTrader5` runs on **Windows only** → dashboard on Vercel, backend + bridge
on a Windows VPS. Full checklist in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
Key env (`ALLOW_CIRCUIT_RESET` **must** be `false` in prod):

```
MT5_MODE=live  MT5_LOGIN=…  MT5_PASSWORD=…  MT5_SERVER=…
ANTHROPIC_API_KEY=…  TELEGRAM_BOT_TOKEN=…  TELEGRAM_CHAT_ID=…
DATABASE_URL=postgresql://…
```

## Hard constraints (enforced in code, not just documented)

| # | Rule | Where |
|---|---|---|
| 1 | Backtest + paper gate before Live Auto | `execution_modes/gate.py`, execution-time re-check in `routes_execution.py` |
| 2 | Status badge on every strategy | `derive_status()` → UI `StatusBadge` |
| 3 | No fabricated performance | metrics only from `backtest_engine` / paper / live; "insufficient data" otherwise |
| 4 | Risk cap server-side (2% / max 5%) | `risk_manager/position_sizing.py` |
| 5 | Circuit breaker 2 losses → 24h, backend-owned | `risk_manager/circuit_breaker.py` |
| 6 | Explainability: checklist + confluence + why-not | `SignalPanel`, journal `SKIP`/`RISK_BLOCK` |
| 7 | Knowledge base = read-only RAG reference | `ai_reasoning/rag_store.py` — never imported/executed |

## Testing

```bash
cd backend && .venv/bin/python -m pytest -q   # 33 passed
```
