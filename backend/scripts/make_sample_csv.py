"""Generate a SYNTHETIC sample CSV for pipeline smoke-tests.

WARNING: this data is randomly generated. It exists ONLY to verify that the
backtest engine runs end-to-end. Any metrics produced from it are MEANINGLESS
for live trading and must never be presented as strategy performance (§2.3).
Real validation requires real broker history (see scripts/export_mt5_csv.md).
"""
import numpy as np
import pandas as pd


def main(path: str = "data/samples/EURUSD_M5_SYNTHETIC.csv", n: int = 6000, seed: int = 42):
    rng = np.random.default_rng(seed)
    t = pd.Timestamp("2024-01-01", tz="UTC")
    rows = []
    p = 1.0850
    drift = 0.0
    while len(rows) < n:
        if t.weekday() < 5:
            if rng.random() < 0.015:
                drift = rng.choice([-1.0, 0.0, 1.0]) * 0.00009
            shock = rng.normal(0, 0.0012) if rng.random() < 0.01 else 0.0  # news spike
            o = p
            c = o + drift + rng.normal(0, 0.00055) + shock
            h = max(o, c) + abs(rng.normal(0, 0.00028))
            l = min(o, c) - abs(rng.normal(0, 0.00028))
            rows.append((t.isoformat(), o, h, l, c, round(float(abs(rng.normal(0.00012, 0.00004))), 6)))
            p = c
        t += pd.Timedelta(minutes=5)
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "spread"]).to_csv(path, index=False)
    print(f"wrote SYNTHETIC {len(rows)} bars -> {path}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "data/samples/EURUSD_M5_SYNTHETIC.csv")
