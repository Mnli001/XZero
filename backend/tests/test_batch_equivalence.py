"""BatchContext snapshots must equal per-bar prefix analysis (repaint-safe)."""
import numpy as np
import pandas as pd

from app.smc_analyzer import SMCAnalyzer, SMCConfig
from app.smc_analyzer.batch import BatchContext


def _df(n=400, seed=9):
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2024-03-01", tz="UTC")
    rows, p, drift = [], 1.0850, 0.0
    t = base
    for _ in range(n):
        if t.weekday() >= 5:
            t += pd.Timedelta(minutes=5)
            continue
        if rng.random() < 0.03:
            drift = rng.choice([-1.0, 0.0, 1.0]) * 0.00012
        o = p
        c = o + drift + rng.normal(0, 0.0005)
        rows.append({"time": t, "open": o, "high": max(o, c) + abs(rng.normal(0, 0.0002)),
                     "low": min(o, c) - abs(rng.normal(0, 0.0002)), "close": c, "spread": 0.0001})
        p = c
        t += pd.Timedelta(minutes=5)
    return pd.DataFrame(rows)


def _canon(smc: dict) -> dict:
    return {
        "bias": smc.get("bias"),
        "checklist": smc.get("checklist"),
        "sweep_idx": (smc.get("sweep") or {}).get("index"),
        "struct_idx": (smc.get("structure") or {}).get("index"),
        "fvg_idx": sorted(z["index"] for z in (smc.get("active_fvgs") or [])),
        "zone": (smc.get("valuation") or {}).get("zone"),
    }


def test_batch_matches_prefix():
    df = _df()
    cfg = SMCConfig()
    a = SMCAnalyzer(cfg)
    ctx = BatchContext(df, cfg)
    for i in [50, 100, 150, 200, 250, 300, len(df) - 1]:
        slow = a.analyze(df, at_index=i)
        fast = ctx.snapshot_at(i)
        assert slow["ok"] and fast["ok"]
        assert _canon(fast) == _canon(slow), f"mismatch at bar {i}"
