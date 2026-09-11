"""Walk-forward (in-sample / out-of-sample) splits for honest validation."""
from __future__ import annotations


def walk_forward_splits(n_bars: int, n_splits: int = 3, train_ratio: float = 0.7, min_test_bars: int = 500) -> list[dict]:
    """Rolling-origin splits. Each split: train window -> test window.

    Windows roll forward so every test segment is out-of-sample relative to
    the data before it (no look-ahead).
    """
    if n_bars < min_test_bars + 50:
        return [{"name": "single", "train": (0, int(n_bars * train_ratio)), "test": (int(n_bars * train_ratio), n_bars - 1)}]
    splits: list[dict] = []
    total_test = n_bars - int(n_bars * train_ratio)
    test_len = max(min_test_bars, total_test // n_splits)
    for k in range(n_splits):
        test_end = n_bars - (n_splits - 1 - k) * test_len
        test_start = test_end - test_len
        train_end = test_start - 1
        train_len = int(test_len * train_ratio / (1 - train_ratio))
        train_start = max(0, train_end - train_len)
        if test_start <= 0 or train_end <= train_start + 50:
            continue
        splits.append({
            "name": f"fold_{k + 1}",
            "train": (train_start, min(train_end, n_bars - 1)),
            "test": (max(test_start, 0), min(test_end, n_bars - 1)),
        })
    if not splits:
        m = int(n_bars * train_ratio)
        splits.append({"name": "single", "train": (0, m), "test": (m, n_bars - 1)})
    return splits
