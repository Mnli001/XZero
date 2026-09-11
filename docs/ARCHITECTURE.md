# Architecture

```
┌─────────────────────────────────────────────────────────┐
│  WEB TERMINAL (Next.js, /frontend) — Vercel / :3000      │
│  Overview · Live · Backtest · Strategies · Risk ·        │
│  Journal · Knowledge — polling via /api rewrites         │
└──────────────────────────┬──────────────────────────────┘
                           │ same-origin /api/* → proxy
┌──────────────────────────▼──────────────────────────────┐
│  API GATEWAY (FastAPI, /backend/app) — VPS / :8000       │
│  REST + /ws/live                                         │
└──┬────────┬────────┬────────┬────────┬────────┬──────────┘
   │        │        │        │        │        │
 mt5_bridge smc_   conflu- risk_   backtest journal
 (live on   analyzer ence_   manager engine   _logger
 Windows,   (pure    engine  (server  (CSV,   (+Telegram)
 mock on    pandas,  (ATR/   -side    walk-
 Linux)     tuned)   RSI/    caps)   forward)
                     EMA/
                     ADX)
   │                          │
   │        ai_reasoning (RAG over curated KB → Claude;
   │         advisory only, risk re-checks everything)
   │
 execution_modes: alert_only → paper → live_auto (Backtest Gate)
```

## Data flow (execution)

1. `MarketData` candles → `SMCAnalyzer` (sweep/CHoCH/FVG/valuation checklist)
2. `ConfluenceScorer` weighted votes → 0–100 (relative, not probability)
3. `SMCStrategy.signal` → enter/skip + explanation
4. `AIReasoner.review` → advisory verdict (can veto, never force)
5. `RiskManager.evaluate` → **binding** allow/block + lots (caps, breaker, guards)
6. Mode routing: alert_only (notify) · paper (virtual fill) · live_auto
   (gate + live bridge re-verified at execution time)
7. `JournalLogger` records every outcome incl. skips/blocks/errors

## Hard guarantees

- Risk cap (default 2%, ceiling 5%) + circuit breaker (2 losses → 24h) live in
  backend code paths every order must pass — no UI bypass exists.
- Live Auto requires backtest gate (≥30 OOS trades, expectancy R > 0,
  maxDD ≤ 25%, PF ≥ 1.1) AND paper gate (≥30 paper trades, expectancy R > 0).
- UI statistics originate only from backtest reports / paper / live logs.
- Knowledge sources are text references for RAG — never imported/executed.
