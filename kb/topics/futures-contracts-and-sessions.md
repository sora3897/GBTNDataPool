# Futures contracts and sessions

Contract facts for 75 futures (tick, multiplier, sessions with ET equivalents, expiry rules and upcoming expiries) are in [../data/contract_specs.json](../data/contract_specs.json). **Contract data compiled by FuturesClock (https://futuresclock.com), reused with attribution under the FuturesClock Open Data Compilation License.** Exchange facts belong to the exchanges. Verify every fact against official exchange notices before trading.

## Sessions: RTH and ETH

- **CME Globex** equity index, metals, energy and FX futures trade nearly 24 hours, Sunday to Friday: 18:00 to 17:00 ET (17:00 to 16:00 Chicago time), with a one-hour daily halt.
- **RTH (regular trading hours)** for US equity index futures means the stock market's hours, 09:30 to 16:00 ET. Most volume and volatility happen then (kb/futures-stats.md).
- **ETH (extended or overnight hours)** is everything else. It's thinner, so spreads and slippage are worse, and moves can reverse at the RTH open.
- **Grains (CBOT corn, soybeans)** have a day session plus a separate night session with a break between them (see the contract file).
- **Holidays and early closes:** CME closes early (around 13:00 ET for equities) on many US holidays and around Thanksgiving, July 4 and Christmas. Our NQ data shows those short days clearly.
- **Daylight saving:** the ET equivalents in the contract file are given for a January date and a July date, because European and Asian sessions shift against ET when clocks change.

## Expiries and rolls

- **Equity index futures (ES, NQ, MES, MNQ, YM, RTY)** are quarterly (March, June, September, December). They're cash-settled to a special opening quotation on the 3rd Friday of the contract month.
- **Rolling:** volume moves to the next quarterly contract about a week before expiry (CME's roll date is commonly the Thursday about eight days before expiry). Trade the contract with the most volume, and roll before liquidity leaves.
- **Physically delivered contracts (CL, NG, GC, SI, HG, grains):** the **first notice day** comes before last trading day. Paper desks must be flat or rolled before first notice. CL's last trading day is 3 business days before the 25th of the month before delivery. GC has its first notice on the last business day of the month before delivery.
- **Continuous data:** backtests stitch contracts together. Back-adjusting (we use the Panama method) removes the jump at each roll, but it changes past price levels, so use returns or ranges rather than absolute price levels in rules.
- **Volatility near expiry:** in theory, volatility can rise as expiry approaches (the Samuelson effect; Hong, 2000). Another reason to roll early.

## The opening range

- The **opening range (OR)** is the high and low of the first 15, 30 or 60 minutes after 09:30 ET.
- On NQ in 2022–2025, almost every day broke its opening range. The first break was close to 50/50 for direction and for whether the day closed beyond it. Both sides broke on 54% of days with a 15-minute range, 39% with 30 minutes and 22% with 60 minutes (kb/futures-stats.md).
- Our tested rule (E10) uses the 09:00 1-hour bar, a daily trend filter, a 1R target, a breakeven stop and an exit at the session close. E21 adds a skip for unusually wide ranges (kb/results.md).
- Opening ranges are larger and noisier in the first minutes and around 08:30 and 10:00 ET data releases. Wider ranges mean wider stops and fewer contracts.

## Tick values (common US contracts)

| Contract | Multiplier | Tick | Tick value |
|---|---|---|---|
| ES / MES | $50 / $5 × index | 0.25 pt | $12.50 / $1.25 |
| NQ / MNQ | $20 / $2 × index | 0.25 pt | $5.00 / $0.50 |
| CL | 1,000 bbl | $0.01 | $10 |
| GC | 100 oz | $0.10 | $10 |
| 6E (Euro FX) | €125,000 | $0.00005 | $6.25 |

Source: FuturesClock compilation of exchange specifications (futuresclock.com). Verify with the exchange.
