import numpy as np
import pandas as pd

from app.confluence_engine import add_indicators
from app.confluence_engine.scorer import ConfluenceScorer
from app.smc_analyzer import SMCAnalyzer


def _df(n=150, seed=3):
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2024-01-01", tz="UTC")
    rows = []
    p = 100.0
    for i in range(n):
        o = p
        c = o + rng.normal(0.05, 0.3)
        rows.append({"time": base + pd.Timedelta(minutes=5 * i), "open": o,
                     "high": max(o, c) + 0.1, "low": min(o, c) - 0.1,
                     "close": c, "spread": 1.0})
        p = c
    return pd.DataFrame(rows)


def test_indicators_present():
    df = add_indicators(_df())
    for c in ["ema9", "ema21", "ema50", "atr", "rsi", "adx", "plus_di", "minus_di"]:
        assert c in df.columns
    assert df["rsi"].iloc[-1] == df["rsi"].iloc[-1]  # not NaN


def test_score_range_and_breakdown():
    raw = _df()
    df = add_indicators(raw)
    smc = SMCAnalyzer().analyze(raw)
    s = ConfluenceScorer().score(df, len(df) - 1, smc)
    assert 0 <= s["score"] <= 100
    assert set(s["votes"]) == {"trend_ema_stack", "momentum_rsi", "trend_strength_adx",
                               "smc_checklist", "valuation_align"}
    assert "disclaimer" in s
