#!/usr/bin/env python3
"""Small backtest sanity checks. Standard library only.

Our own code, written after the pipeline-audit ideas in ml-quant-trading by
Yimin Du (https://github.com/initial-d/ml-quant-trading), MIT License,
Copyright (c) 2025 Yimin Du. See kb/topics/quant-validation-toolkit.md for the
full MIT notice.

These checks show a pipeline does what its code claims. They do not show an edge.
"""
import json
import sys


def lagged_pnl(positions, returns):
    """Position chosen at bar t-1 earns the return of bar t. Bar 0 earns nothing."""
    if len(positions) != len(returns):
        raise ValueError("positions and returns must be the same length")
    return [0.0] + [positions[i - 1] * returns[i] for i in range(1, len(returns))]


def check_lag_alignment(positions, returns, pnl):
    """True when pnl matches the one-bar lag. A same-bar pnl (look-ahead) fails."""
    expected = lagged_pnl(positions, returns)
    return all(abs(a - b) <= 1e-12 for a, b in zip(expected, pnl)) and len(expected) == len(pnl)


def forward_labels(closes, tradable=None):
    """One-bar forward return per bar, with a mask. The last bar has no label."""
    n = len(closes)
    tradable = tradable or [True] * n
    labels, mask = [], []
    for t in range(n):
        ok = t + 1 < n and tradable[t] and tradable[t + 1] and closes[t]
        labels.append(closes[t + 1] / closes[t] - 1 if ok else 0.0)
        mask.append(bool(ok))
    return labels, mask


def cost_drag_cumulative(positions, cost_per_unit_turnover):
    """Sum of per-bar costs over the whole run. Cumulative, not annualised."""
    total, prev = 0.0, 0.0
    for pos in positions:
        total += abs(pos - prev) * cost_per_unit_turnover
        prev = pos
    return total


def masked_mean(values, mask, window):
    """Rolling mean that never reads a masked (untradeable) value. None until enough valid values."""
    out = []
    for t in range(len(values)):
        lo = max(0, t - window + 1)
        valid = [values[i] for i in range(lo, t + 1) if mask[i]]
        out.append(sum(valid) / len(valid) if mask[t] and len(valid) == window else None)
    return out


def check_mask_isolation(values, mask, window):
    """Poison masked cells with a huge number; valid outputs must not change."""
    poisoned = [v if m else 1e9 for v, m in zip(values, mask)]
    clean = masked_mean(values, mask, window)
    dirty = masked_mean(poisoned, mask, window)
    return all((a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 1e-9)
               for a, b in zip(clean, dirty))


def run_self_audit():
    pos = [0, 1, 1, -1, 0]
    rets = [0.0, 0.01, -0.02, 0.03, 0.01]
    one = cost_drag_cumulative(pos, 0.0001)
    ten = cost_drag_cumulative(pos, 0.001)
    labels, mask = forward_labels([100, 101, 99, 102])
    vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    vmask = [True, True, False, True, True, True]
    checks = {
        "lag_alignment": check_lag_alignment(pos, rets, lagged_pnl(pos, rets)),
        "same_bar_pnl_is_caught": not check_lag_alignment(pos, rets, [p * r for p, r in zip(pos, rets)]),
        "label_boundary": mask[-1] is False and labels[-1] == 0.0,
        "cost_linear_in_fee": abs(ten / one - 10.0) < 1e-9,
        "mask_isolation": check_mask_isolation(vals, vmask, 2),
    }
    return {"ok": all(checks.values()), "checks": checks}


if __name__ == "__main__":
    result = run_self_audit()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
