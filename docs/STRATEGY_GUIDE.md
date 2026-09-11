# Strategy guide — `smc_fvg_retest_v1` (reference implementation)

Entry model (long; short mirrored):

1. **Liquidity sweep** of lows (wick pierces + closes back; level must already
   be confirmed — no repaint).
2. **Bullish CHoCH/BOS** after the sweep.
3. **Active bullish FVG** + price in **discount** (< 50% − tolerance).
4. **Retest**: price trades into the FVG → enter at close, provided confluence ≥
   threshold (default 55).
5. **SL** beyond sweep extreme (+ ATR buffer) · **TP** = R-multiple (default 2R).

## Tuning (all UI/CLI-parameterized, never hardcoded)

- `SMCConfig`: swing depth, sweep wick size, FVG min size/age, dealing-range
  lookback, equilibrium tolerance, retest tolerance.
- `ScorerWeights`: five confluence weights — re-tune per symbol/timeframe.
- `StrategyParams`: min_confluence, risk_reward, SL buffer, max hold, filters.

## Honest workflow

1. Export **real broker history** (MT5 F2 → export, or `File → Save As` from the
   terminal) to CSV: `time,open,high,low,close[,spread]`.
2. `python scripts/run_backtest.py history.csv EURUSD M5` — walk-forward OOS.
3. Only if the gate passes: switch the strategy to `paper`, trade ≥ 30 fills.
4. Only if paper passes: `live_auto` unlocks. Start with minimum risk %.

Synthetic CSVs (`scripts/make_sample_csv.py`) verify plumbing only — metrics
from them are meaningless and must never justify live trading.
