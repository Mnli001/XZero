# Project Zero — Backend (FastAPI + quant core)

## Quickstart (Linux / dev — MT5 mock mode)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # or create backend/.env
python scripts/make_sample_csv.py data/samples/EURUSD_M5_SYNTHETIC.csv
python scripts/run_backtest.py data/samples/EURUSD_M5_SYNTHETIC.csv EURUSD M5
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## Production split (§3.1)

- Dashboard (Next.js) → Vercel
- This backend + MT5 bridge → **Windows VPS** (the `MetaTrader5` package is Windows-only).
  Set `MT5_MODE=live`, `MT5_LOGIN/PASSWORD/SERVER`, `ALLOW_CIRCUIT_RESET=false`.
