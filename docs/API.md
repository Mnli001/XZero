# API reference (base: `/api`, interactive docs at backend `/docs`)

## Health / market (read-only)

- `GET /api/health` — version, MT5 mode, circuit status
- `GET /api/market/candles?symbol=EURUSD&timeframe=M5&count=300`
- `GET /api/market/tick?symbol=EURUSD`
- `GET /api/market/analysis?symbol=&timeframe=&count=&ai=true|false` — full
  signal + SMC + confluence (+ optional AI advisory)

## Backtest & strategies

- `POST /api/backtest/run` `{csv_path, symbol, timeframe, strategy_params, risk_pct, spread, slippage, n_splits}` → report + gate eval (persisted)
- `GET /api/backtest/reports` / `GET /api/backtest/reports/{id}`
- `GET /api/strategies` — rows with `status` badge, gates, `live_auto_allowed`, reasons
- `POST /api/strategies/{name}/mode` `{mode}` — 403 unless gate passes for `live_auto`

## Risk (binding, server-side)

- `GET /api/risk/status` — circuit, caps, guards
- `POST /api/risk/evaluate` — dry-run the exact execution-time checks
- `POST /api/risk/circuit/reset` — dev only (`ALLOW_CIRCUIT_RESET=true`), 403 in prod

## Execution

- `POST /api/execution/signal` `{symbol, timeframe, strategy, balance, risk_pct?, use_ai}` — full pipeline; routes by strategy mode
- `GET /api/execution/paper` — paper account state
- `POST /api/execution/paper/tick` `{symbol, bid, ask}` — advance paper fills (poller/tests)

## Journal / knowledge

- `GET /api/journal?kind=&limit=` · `GET /api/journal/export.csv` · `.../export.xlsx`
- `GET/POST /api/knowledge` · `DELETE /api/knowledge/{id}` · `GET /api/knowledge/search?q=`

## WebSocket

- `WS /ws/live` — send `{"symbol","timeframe","interval"}` then receive
  `{type:"snapshot", tick, price, signal, confluence, smc, circuit}` every N sec.
  (The web UI uses polling by default for proxy compatibility.)
