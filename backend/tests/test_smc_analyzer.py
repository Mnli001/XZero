import numpy as np
import pandas as pd

from app.smc_analyzer import SMCAnalyzer, SMCConfig
from app.smc_analyzer.choch import detect_structure
from app.smc_analyzer.fvg import detect_fvgs
from app.smc_analyzer.premium_discount import evaluate
from app.smc_analyzer.swings import find_swings


def _frame(rows):
    base = pd.Timestamp("2024-01-01", tz="UTC")
    times = [base + pd.Timedelta(minutes=5 * i) for i in range(len(rows))]
    return pd.DataFrame([{"time": t, "open": o, "high": h, "low": l, "close": c, "spread": 1.0}
                         for t, (o, h, l, c) in zip(times, rows)])


def _trend(n=40, start=100.0, step=0.5, noise=0.05, seed=7, wick=0.15):
    rng = np.random.default_rng(seed)
    rows = []
    p = start
    for _ in range(n):
        o = p
        c = o + step + rng.normal(0, noise)
        # independent wick noise (realistic: no tied highs/lows)
        rows.append((o, max(o, c) + abs(rng.normal(0, wick)),
                     min(o, c) - abs(rng.normal(0, wick)), c))
        p = c
    return _frame(rows)


def test_find_swings_marks_obvious_fractal():
    rows = [(100, 100.2, 99.8, 100)] * 3 + [(100, 105, 99.9, 104)] + [(100, 100.2, 99.8, 100)] * 3
    df = _trend(20, start=100, step=0.0, noise=0.01)
    df2 = _frame(rows)
    sw = find_swings(df2, left=3, right=3)
    assert not sw.empty
    assert (sw["kind"] == "high").any()


def test_detect_fvgs_finds_constructed_gap():
    df = _trend(30)
    # force a bullish FVG at bars 20..22: low[22] > high[20]
    df.loc[22, "low"] = df.loc[20, "high"] + 1.0
    df.loc[22, "close"] = df.loc[22, "low"] + 0.5
    df.loc[22, "high"] = df.loc[22, "close"] + 0.3
    df.loc[22, "open"] = df.loc[22, "low"] + 0.1
    # keep later bars above the zone so it stays active
    for j in range(23, 30):
        df.loc[j, "low"] = df.loc[22, "low"] + 0.2
        df.loc[j, "high"] = df.loc[j, "low"] + 0.5
        df.loc[j, "close"] = df.loc[j, "low"] + 0.3
        df.loc[j, "open"] = df.loc[j, "low"] + 0.25
    zones = detect_fvgs(df, min_atr_mult=0.0)
    bull = [z for z in zones if z.direction == "bullish"]
    assert bull, "constructed bullish FVG not detected"


def test_structure_events_on_trend_break():
    up = _trend(40, start=100, step=0.35, noise=0.4)
    rng = np.random.default_rng(3)
    down_rows = []
    p = float(up["close"].iloc[-1])
    for _ in range(30):
        o = p
        c = o - 0.5 + rng.normal(0, 0.4)
        down_rows.append((o, max(o, c) + 0.1, min(o, c) - 0.1, c))
        p = c
    base = pd.Timestamp("2024-01-01", tz="UTC")
    times = [base + pd.Timedelta(minutes=5 * (30 + i)) for i in range(20)]
    dn = pd.DataFrame([{"time": t, "open": o, "high": h, "low": l, "close": c, "spread": 1.0}
                       for t, (o, h, l, c) in zip(times, down_rows)])
    df = pd.concat([up, dn], ignore_index=True)
    evts = detect_structure(df, swing_left=3, swing_right=3)
    assert len(evts) > 0
    assert any(e.kind in ("choch_bearish", "bos_bearish") for e in evts)


def test_valuation_zones():
    df = _trend(60, start=100, step=0.3)
    v = evaluate(df, lookback=50)
    assert v is not None
    assert v.zone in ("premium", "discount", "equilibrium")
    assert 0 <= v.position_pct <= 100


def test_analyzer_snapshot_shape():
    df = _trend(120)
    out = SMCAnalyzer(SMCConfig()).analyze(df)
    assert out["ok"] is True
    assert set(out["checklist"]) == {"sweep", "choch", "structure_break", "fvg", "valuation", "retest"}
    assert out["bias"] in ("bullish", "bearish", "neutral")


def test_analyzer_repaint_safe_slice():
    df = _trend(120)
    a = SMCAnalyzer(SMCConfig())
    full = a.analyze(df)
    part = a.analyze(df, at_index=60)
    assert part["ok"] is True
    assert part["bar_index"] == 60
