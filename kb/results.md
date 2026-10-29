# Our test results (backtest only)

Everything here is an offline **backtest**. None of it has been forward-tested, and all of it is paper only. Read the caveats before using any number.

## Setup

- **Markets:** ES, NQ and GC futures (CL in the first round), traded as micros (MES $5/pt, MNQ $2/pt, MGC $10/oz).
- **Data:** about 2.4 years of free 1-hour continuous futures data (yfinance), back-adjusted across rolls (Panama method).
- **Costs:** $1.24 round-trip commission per micro, and 1 tick of slippage on every fill, including targets. Gaps fill at the open. If the stop and target are both inside one bar, we assume the stop hit first.
- **Risk:** 1% per trade, 2% daily loss cap, at most 3 trades a day, fixed $50K account, at most 10 micros per trade and 2 open positions.
- **Test split:** full history split 60/40 by time into in-sample (IS) and out-of-sample (OOS). Each segment starts at $50K. Rules were frozen before each run.
- **Random baseline:** random entries with the same stop and exit mechanics, 50 seeds. "Pctile" is where the rule ranks against them.

## Headline: opening-range entries E10 and E21

**E10, trend-filtered opening-range breakout.** Take the 09:00 (New York) 1-hour bar's range. Trade a break of it only in the direction of the daily 13-EMA trend (Elder's first screen). Target 1R. Move the stop to breakeven after +0.5R. Exit at the session close.

**E21, E10 plus a wide-range skip.** The same as E10, but skip days when the opening range is more than 1.5× the median of the prior 20 sessions.

| Rule | Window | Dates | Trades | Win % | Net $ | Profit factor | Max drawdown | Random pctile |
|---|---|---|---|---|---|---|---|---|
| E10 | IS | 2024-06-06 to 2025-10-31 | 427 | 43.8 | +23,021 | 1.58 | 4.57% | 100 |
| E10 | **OOS** | 2025-11-04 to 2026-10-23 | 267 | 46.4 | **+21,090** | **1.89** | **2.66%** | 100 |
| E21 | IS | 2024-07-03 to 2025-12-11 | 350 | 43.1 | +20,282 | 1.61 | 4.29% | 100 |
| E21 | **OOS** | 2025-12-15 to 2026-10-23 | 225 | 47.6 | **+20,099** | **2.06** | **2.78%** | 100 |

Both made money on each of ES, GC and NQ out-of-sample. Source files: `backtests/entries_v8/summary.json` and `summary.md`, and `strategies/E10.md` and `strategies/E21.md` in this repo.

## Close relatives of E10 (entries_v8)

| Rule | Change from E10 | OOS net $ | OOS PF | OOS max DD |
|---|---|---|---|---|
| E22 | 1.5R target instead of 1R | +20,171 | 1.85 | 2.68% |
| E23 | breakeven moved at +0.75R instead of +0.5R | +19,267 | 1.67 | 3.27% |
| E24 | 2-bar (09:00 + 10:00) opening range | +6,808 | 1.37 | 4.31% |

E24 lost money in one recent window, so it fails our "positive in every window" check.

## Everything else we tried (OOS net $, profit factor)

- **Elder triple screen, as written** (1-hour, four risk setups): lost money in-sample in every setup (profit factor 0.68 to 0.80), and three of the four setups also lost out-of-sample. Its trend filter survives inside E10.
- **entries_v5_7** (E1 and E5 references plus E9 to E20): E1 plain opening-range breakout +10,054 (1.16); E5 trend-filtered ORB +16,930 (1.48); E9 +8,525 (1.44); E10 +21,090 (1.89); E11 +12,002 (1.37); E12 +16,260 (1.58); E13 +989 (1.04); E14 +6,364 (1.17); E15 +6,823 (1.15); E16 +11,709 (1.34); E17 −10,346 (0.87); E18 −15,571 (0.84); E19 +6,650 (1.29); E20 −138 (1.00).
- **entries_v2 to v4:** Donchian 55/20 breakout, RSI(2) reversion, EMA 20/50 cross with the Elder filter, and E5 to E8. These were screened and the opening-range family was carried forward. See `backtests/entries_v3/` and `backtests/entries_v4/`.

## Caveats (read these)

- **Selection bias.** About 25 rule sets have been tested (the triple screen plus E1 to E24), and E10 and E21 are the best of them. E21 to E24 are tweaks of an already-selected winner. The best of 25 looks better than its true edge. Apply the guards in rules.md (deflated Sharpe, t ≈ 3, expect roughly half the backtest's performance).
- **Not forward-tested.** No rule here has a forward paper record yet. The next step is a paper forward run with the rules frozen.
- **Short, free data.** About 2.4 years of 1-hour bars from a free source, back-adjusted. Hourly bars can't show what happened inside the bar, so fill order inside a bar is assumed.
- **Paper only.** No real money, and nothing here is financial advice.
