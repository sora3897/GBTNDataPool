# Quant validation toolkit (adapted for futures)

Adapted from **ml-quant-trading** by Yimin Du (https://github.com/initial-d/ml-quant-trading), MIT License, Copyright (c) 2025 Yimin Du. That project targets Chinese A-shares (CSI 300), not futures. This page keeps only the parts that carry over, rewritten in our own words. The paper behind it is Du (2025/2026), https://arxiv.org/abs/2507.07107. The small helper `tools/validation_checks.py` is our own code, written after that project's audit ideas and credited the same way.

## Audit checklist: run it before believing any backtest

1. **Know what was available, and when.** Every input must be timestamped no later than the decision. Bar timestamps can be the bar's start or its end (our NQ file labels the end), so check before you build an opening range.
2. **Mask untradeable bars first.** Halts, limit-locked futures, closed sessions, holiday half-days, and the days after a contract's last trade aren't ordinary zeroes or prices. Exclude them **before** computing rolling indicators, or they leak into every average. That was the biggest single fix in Du's paper.
3. **Labels stop at the sample edge.** A forward return at bar t needs bar t+1. The last bar has no label. Don't let it count as a zero return.
4. **Lag positions by one bar.** The position chosen at the close of bar t-1 earns bar t's return. If the same bar both picks the trade and pays it, that's look-ahead. `tools/validation_checks.py` checks this.
5. **Split by time, and purge overlaps.** Train on earlier data and test on later data. When labels span several bars, drop (purge) training samples whose label window overlaps the test period, and leave a gap (embargo) after it. Prefer walk-forward over a single split.
6. **Don't tune on the test period.** Every rerun on the same out-of-sample window spends it. Count each variant (kb/rules.md guards 16–27).
7. **Universe as of the day.** Use contracts that existed and were liquid at the time, and roll as you really would.
8. **Determinism.** The same data and the same seed must give the same result, so a change in results can be blamed on a change in code.

## Metrics, units, and cost drag

- Report every metric with its **unit** (fraction, dollars, ticks, R, ratio) and its **time basis** (per trade, per day, per year, or cumulative over the run). Never put a cumulative number next to annual ones without labelling it.
- **Cost drag:** the sum of per-trade costs is cumulative. It doubles when the test doubles in length, and it scales linearly with the fee. Subtracting net annual return from gross annual return only approximates annual cost, because returns compound. Report gross and net, plus the cumulative cost, each labelled.
- Standard set: annualised return and volatility, Sharpe and Sortino ratios, max drawdown, Calmar ratio, turnover, and (for ranked signals) information coefficient and rank IC. For futures trades, also report net dollars, profit factor, win rate, average R, and trade count.
- **Cost sensitivity:** rerun at 0.5×, 1× and 2× the assumed commission and slippage. A strategy that only works at the low end isn't robust.

## Factor ideas that transfer to futures

- **Momentum / trend:** past 1- to 12-month returns, moving-average differences, Donchian position. The daily file includes many of these as columns. Our stats show weak raw persistence (kb/futures-stats.md), so use trend as a filter.
- **Carry / term structure:** the price gap between the front and next contracts (contango vs backwardation), annualised. Needs per-contract data, which the continuous series doesn't have.
- **Volatility:** ATR, range relative to its recent median (E21's wide-range skip), volatility expansion (short over long average range).
- **Volume and liquidity:** relative volume against its recent average, range per unit of volume (an illiquidity proxy), and the open's share of daily volume.
- **Gap and VWAP:** overnight gap size and direction, and the regular-session price relative to VWAP. The NQ file includes RTH and ETH VWAP columns.

## What this toolkit does not prove

Passing these checks doesn't show an edge exists, that costs are fully modelled, or that results will repeat. It only shows the pipeline does what its code claims. Paper or demo only.

## MIT License (for the adapted material)

```text
MIT License

Copyright (c) 2025 Yimin Du

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
