# Futures stats (historical, descriptive)

> **Historical descriptive statistics, not signals.** These describe what the data looked like in the past. They are not trade recommendations, nothing here is financial advice, and every desk stays paper or demo only.
>
> **Data source:** user-provided Kaggle-style datasets (`daily_futures_data.csv`: 24 US futures, continuous daily bars, 2000–Sep 2025; `Dataset_NQ_1min_2022_2025.csv`: NQ 1-minute bars, ET timestamps). **License unverified.** The raw data is **not** shipped. Only these small summaries are. Machine-readable version: [data/futures_stats.json](data/futures_stats.json).

## Daily: volatility, range, persistence (24 contracts)

Method: daily log returns with zero-volume days dropped. Jumps over 6× the trailing 60-day standard deviation are treated as roll or data jumps and removed (a handful per series). "Last 5y" is the last five years of each series. Ticks use standard CME tick sizes, so check them against [data/contract_specs.json](data/contract_specs.json) or the exchange. "Persistence" is how often the next 20-day return had the same sign as the prior 20 days, where 0.50 is a coin flip.

| Ticker | Contract | Years | Ann. vol % (full) | Ann. vol % (last 5y) | Avg daily range % (5y) | Avg range, ticks (5y) | Avg range, $/contract (5y) | Autocorr daily | Autocorr monthly | 20d persistence |
|---|---|---|---|---|---|---|---|---|---|---|
| NG | Natural gas | 2000–2025-09 | 55.8 | 70.6 | 5.95 | 235 | 2,352 | -0.063 | -0.042 | 0.508 |
| HO | Heating oil | 2004–2025-09 | 34.6 | 36.8 | 3.42 | 926 | 3,887 | -0.005 | 0.193 | 0.508 |
| CL | WTI crude oil | 2000–2025-09 | 40.7 | 36.2 | 3.48 | 266 | 2,656 | -0.055 | 0.137 | 0.5 |
| W | Wheat | 2000–2025-09 | 31.2 | 33.3 | 3.05 | 86 | 1,075 | -0.0 | -0.071 | 0.453 |
| SI | Silver | 2000–2025-09 | 30.4 | 30.7 | 2.86 | 149 | 3,718 | -0.025 | -0.048 | 0.469 |
| PL | Platinum | 2000–2025-09 | 25.7 | 29.9 | 2.95 | 302 | 1,508 | 0.023 | 0.062 | 0.468 |
| C | Corn | 2000–2025-09 | 27.0 | 25.9 | 2.27 | 50 | 620 | 0.023 | 0.028 | 0.513 |
| HG | Copper | 2000–2025-09 | 26.5 | 24.4 | 2.42 | 201 | 2,518 | -0.067 | 0.078 | 0.492 |
| RTY | E-mini Russell 2000 | 2017–2025-09 | 23.9 | 23.2 | 2.24 | 450 | 2,249 | -0.096 | -0.087 | 0.468 |
| NQ | E-mini Nasdaq-100 | 2000–2025-09 | 26.7 | 22.6 | 2.01 | 1237 | 6,185 | -0.046 | 0.063 | 0.544 |
| S | Soybeans | 2000–2025-09 | 23.1 | 21.7 | 1.91 | 100 | 1,255 | -0.002 | 0.001 | 0.501 |
| GF | Feeder cattle | 2002–2025-09 | 17.9 | 17.0 | 1.44 | 120 | 1,502 | 0.073 | 0.025 | 0.515 |
| ES | E-mini S&P 500 | 2000–2025-09 | 19.2 | 16.7 | 1.5 | 274 | 3,430 | -0.07 | 0.029 | 0.534 |
| GC | Gold | 2000–2025-09 | 17.1 | 15.7 | 1.46 | 319 | 3,190 | -0.016 | -0.112 | 0.492 |
| YM | E-mini Dow | 2002–2025-09 | 18.0 | 15.1 | 1.39 | 493 | 2,465 | -0.097 | -0.011 | 0.514 |
| US | 30-year T-bond | 2000–2025-09 | 10.5 | 11.6 | 1.11 | 47 | 1,468 | -0.017 | 0.075 | 0.483 |
| JY | Japanese yen | 2001–2025-09 | 10.3 | 10.1 | 0.88 | 131 | 817 | -0.076 | 0.06 | 0.476 |
| BP | British pound | 2001–2025-09 | 9.1 | 8.5 | 0.82 | 104 | 650 | 0.01 | 0.049 | 0.501 |
| SF | Swiss franc | 2001–2025-09 | 9.6 | 8.1 | 0.75 | 168 | 1,050 | -0.02 | -0.109 | 0.485 |
| EU | Euro FX | 2001–2025-09 | 9.1 | 7.8 | 0.73 | 160 | 998 | 0.002 | 0.004 | 0.508 |
| CD | Canadian dollar | 2001–2025-09 | 8.5 | 6.6 | 0.64 | 97 | 484 | -0.013 | -0.067 | 0.487 |
| TY | 10-year T-note | 2000–2025-09 | 6.2 | 6.4 | 0.59 | 44 | 685 | -0.019 | 0.011 | 0.498 |
| FV | 5-year T-note | 2000–2025-09 | 4.1 | 4.5 | 0.39 | 56 | 438 | -0.016 | 0.025 | 0.503 |
| TU | 2-year T-note | 2000–2025-09 | 1.7 | 2.0 | 0.16 | 43 | 336 | -0.036 | 0.079 | 0.484 |

What stands out:
- **Daily returns don't trend day to day.** Lag-1 autocorrelation is near zero or slightly negative almost everywhere. Equity indices are the most negative (ES −0.07, YM −0.10, RTY −0.10), which means a mild next-day reversal tendency.
- **Month-to-month persistence is weak and mixed.** Energy is the most positive (HO +0.19, CL +0.14), gold and some currencies are negative, and the 20-day sign-persistence measure sits between 0.45 and 0.54 for every contract. Equity indices are slightly above 0.5 (NQ 0.54, ES 0.53). Any trend edge is small, so filters matter more than raw momentum.
- **Range per contract varies about 10×.** A typical ES day moved about $3,430 per full contract (about $343 per micro), NQ about $6,185 (about $619 per micro). Size from the stop distance, never from a fixed contract count.

## Correlation clusters (daily returns since 2015)

Clusters with average correlation of at least 0.5: **equity indices** (ES, NQ, RTY, YM), **Treasuries** (TU, FV, TY, US), **European currencies** (BP, EU, SF), **precious metals** (GC, SI, PL), **grains** (C, W), **petroleum** (CL, HO). Standing alone: CD, GF, HG, JY, NG, S.

Highest pairs: FV–TY 0.97, ES–YM 0.95, ES–NQ 0.93, TY–US 0.92. Cross-asset pairs are low: ES–TY −0.14, ES–GC 0.02, ES–CL 0.23, JY–TY +0.53. **Running ES, NQ and YM together is roughly one bet, not three.** Count them as one when you apply risk caps.

## Roll behaviour

Not visible in this file. The series look continuous (back-adjusted or stitched): there are no clusters of jumps around the quarterly roll. Average absolute returns in the roll week were about the same as on other days (ES 0.82% vs 0.81%, NQ 1.10% vs 1.13%, TY 0.30% vs 0.29%). Rolls still matter for live contracts. See [topics/futures-contracts-and-sessions.md](topics/futures-contracts-and-sessions.md).

## NQ 1-minute: data check

- **First bar:** 2022-12-26 18:01:00 ET. **Last bar:** 2025-12-11 20:52:00 ET. Timestamps label the **end** of each minute (the first regular-session VWAP bar is labelled 09:31), so these stats shift bars to their start.
- **Truncated: yes, almost certainly.** The file has exactly 1,048,576 lines including the header, which is Excel's row limit, and it stops mid-evening on 2025-12-11. The name says 2022–2025, but treat the end as an artefact of the row limit, not the real end of the data.
- **Missing days:** regular-session data exists on 764 weekdays. Against an approximate exchange calendar, the only missing weekday is 2025-01-09 (one bar, the national day of mourning closure). There are 29 short days (early closes and holidays such as July 3, Black Friday, Christmas Eve, and federal holidays when CME closes equities early). There are 2 gaps longer than 5 minutes inside regular hours.

## NQ opening range (regular session from 09:30 ET, 735 full days)

"Break" means price trades beyond the opening-range high or low later that session. "Close beyond" means the 16:00 close is past the side that broke first. "Extension" is how far price went past the first break, in multiples of the opening range.

| Opening range | Median size | Breaks either side | Breaks both sides | First break up | Close beyond first-break side | Median extension | Reaches 1× OR beyond |
|---|---|---|---|---|---|---|---|
| 15min | 71.75 pts (287 ticks, 0.37%) | 100.0% | 53.9% | 51.4% | 51.0% | 1.26× | 58.6% |
| 30min | 95.75 pts (383 ticks, 0.489%) | 99.7% | 38.8% | 53.5% | 54.2% | 0.89× | 43.5% |
| 60min | 127.0 pts (508 ticks, 0.669%) | 97.4% | 22.0% | 52.1% | 52.4% | 0.56× | 23.3% |

Plain words:
- Almost every day breaks the opening range at least once. A "breakout" alone is not an edge.
- **The first break is close to a coin flip on direction (51–54% up) and on whether the day closes beyond it (51–54%).** That's why our E10 and E21 entries add a daily trend filter, a 1R target and a breakeven stop (kb/results.md).
- Longer ranges get fewer false breaks: both sides broke on 54% of days with a 15-minute range, 39% with 30 minutes, and 22% with 60 minutes.

## NQ time-of-day volatility (mean absolute 1-minute move in ticks, mean volume, 30-minute buckets, ET)

| Bucket start (ET) | Abs move (ticks) | Volume |
|---|---|---|
| 00:00 | 6.17 | 48 |
| 00:30 | 6.0 | 47 |
| 01:00 | 7.19 | 58 |
| 01:30 | 7.75 | 64 |
| 02:00 | 9.6 | 93 |
| 02:30 | 8.93 | 84 |
| 03:00 | 13.61 | 162 |
| 03:30 | 11.72 | 134 |
| 04:00 | 13.21 | 166 |
| 04:30 | 10.86 | 122 |
| 05:00 | 10.31 | 115 |
| 05:30 | 9.55 | 108 |
| 06:00 | 10.23 | 117 |
| 06:30 | 10.1 | 122 |
| 07:00 | 11.74 | 160 |
| 07:30 | 11.05 | 161 |
| 08:00 | 12.34 | 221 |
| 08:30 | 18.39 | 460 |
| 09:00 | 14.71 | 429 |
| 09:30 | 38.06 | 2349 |
| 10:00 | 32.56 | 1755 |
| 10:30 | 27.3 | 1406 |
| 11:00 | 24.04 | 1161 |
| 11:30 | 21.92 | 1028 |
| 12:00 | 20.26 | 881 |
| 12:30 | 19.19 | 811 |
| 13:00 | 20.29 | 846 |
| 13:30 | 19.39 | 799 |
| 14:00 | 20.34 | 865 |
| 14:30 | 19.84 | 859 |
| 15:00 | 19.71 | 887 |
| 15:30 | 23.16 | 1490 |
| 16:00 | 13.91 | 496 |
| 16:30 | 7.75 | 119 |
| 18:00 | 11.33 | 112 |
| 18:30 | 7.92 | 63 |
| 19:00 | 8.56 | 72 |
| 19:30 | 7.76 | 67 |
| 20:00 | 10.11 | 96 |
| 20:30 | 8.62 | 80 |
| 21:00 | 8.37 | 78 |
| 21:30 | 8.14 | 76 |
| 22:00 | 7.38 | 66 |
| 22:30 | 6.53 | 55 |
| 23:00 | 6.32 | 52 |
| 23:30 | 6.08 | 47 |

The first 30 minutes of the regular session are the most volatile (about 38 ticks per minute, roughly 6× the overnight lull). Volatility fades into midday and picks up again into the 15:30–16:00 close. 08:30 ET (US data releases) is the busiest pre-market bucket.

**Quarter-hour check** (regular session, excluding the 09:30 minute): the mean absolute 1-minute move at :00, :15, :30 and :45 was 26.44 ticks, against 23.3 ticks for other minutes. The top-of-hour minute was the largest (31.77 ticks), partly because scheduled releases land on the hour (10:00 ET). This is the same clock-time burst pattern Kim and Hansen (2026) document in crypto futures (see rules.md).
