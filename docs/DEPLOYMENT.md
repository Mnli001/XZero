# Deployment

## Why two hosts (§3.1)

The `MetaTrader5` Python package works on **Windows only**. The stack therefore
splits in production:

| Piece | Host | Notes |
|---|---|---|
| Web terminal (Next.js) | Vercel | `NEXT_PUBLIC_API_BASE=https://api.yourdomain` |
| FastAPI + backtest + paper | Windows VPS | `MT5_MODE=live`, terminal logged in |
| MT5 bridge | same VPS (in-process) | `MT5_LOGIN/PASSWORD/SERVER` env |
| DB | Supabase Postgres | `DATABASE_URL=postgresql://…` (default: local SQLite) |

## Backend (Windows VPS)

```powershell
cd backend
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install MetaTrader5   # Windows only
copy ..\.env.example .\.env
# edit .env: MT5_MODE=live, MT5_* creds, ALLOW_CIRCUIT_RESET=false,
# ANTHROPIC_API_KEY, TELEGRAM_* (optional)
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run under NSSM / Task Scheduler with auto-restart; keep the MT5 terminal open
and logged in on the same machine. The circuit-breaker state file
(`./data/circuit_breaker.json`) must persist across restarts — never delete it
to "clear" a lock; locks expire by time.

## Frontend (Vercel)

Root directory: `frontend`. Env: `NEXT_PUBLIC_API_BASE=https://<vps-host>:8000`
(HTTPS via Caddy/nginx reverse proxy on the VPS recommended).

## Production checklist

- [ ] `ALLOW_CIRCUIT_RESET=false`
- [ ] `DATABASE_URL` points at Postgres (backups on)
- [ ] Backend behind HTTPS reverse proxy
- [ ] Telegram alerts configured and tested
- [ ] Strategy passed backtest gate on **real broker history** (≥30 OOS trades)
- [ ] Strategy passed paper gate (≥30 paper trades, expectancy R > 0)
- [ ] Started in `alert_only`, then `paper`, then `live_auto`
