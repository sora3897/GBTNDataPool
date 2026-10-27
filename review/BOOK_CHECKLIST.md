# Book's review checklist (network paper-trading pool)

Reviewer: Book. Role assigned by Alex via Lila, Oct 27, 2026.
Queue: /workspace/network_pool/pending/ (built by serverbot)
Decisions: append one JSON line per submission to /workspace/network_pool/review/decisions.jsonl:
`{"submission_id": "...", "verdict": "approve"|"reject", "reason": "...", "reviewer": "Book", "timestamp_et": "YYYY-MM-DDTHH:MM:SS-04:00/-05:00"}`

I review only when asked. I run no background processes or routines for this.
I never edit or delete a submission. I only append decisions.

## Approve only if every check passes. When unsure, reject and give the reason.

1. **Label.** It is labeled `backtest`, `paper`, or `live-observation`, and nothing else.
2. **Timestamp.** It has a real Eastern timestamp (ET offset -04:00 or -05:00, matching DST on that date, not in the future, not a UTC value relabeled as ET).
3. **Internal consistency.**
   - The sum of per-trade P&L (net of stated fees) matches the reported total P&L, within rounding.
   - The win/loss counts and trade count match the trade list.
   - PF (gross wins / gross losses) recomputes from the trades and is plausible. Treat PF > 5 on more than 30 trades, or a zero-loss record, as suspect unless explained.
   - Max drawdown recomputes from the equity curve, and it isn't smaller than the worst single loss.
   - Starting bank + P&L = ending bank.
4. **No look-ahead.** Every entry and exit decision uses only data timestamped before the decision. No signals computed on the bar being traded, and no future candles, closes, or rug outcomes used in filters.
5. **No impossible fills.** Fills fall inside that bar's high and low. Size is within pool liquidity. No fills on dead, rugged, or untradeable pools. No exits at pre-rug quotes after a rug. Fill vs decision price gaps are explained.
6. **Method and data source.** The strategy rules, fee/slippage model, and data source (for example GeckoTerminal, DexScreener, Kalshi or Polymarket API) are stated clearly enough to reproduce.
7. **Not a duplicate.** No matching submission_id, and no same strategy + same period + same trades already in pending/, review/decisions.jsonl, backtests/, paper_trades/, or strategies/. Check content too, not just the file name.
8. **No secrets or personal info.** No private keys, seed phrases, API keys, tokens, passwords, cookies, wallet secrets, emails, phone numbers, home addresses, or real names beyond public handles. If it has any of these: reject, don't quote the value in the reason, and flag it to Lila.
9. **Backtests only.** It reports an out-of-sample result (with a stated in-sample/out-of-sample split) and the number of variants or parameter sets tried. If either is missing, reject.
10. **Schema.** It conforms to /workspace/network_pool/schema.json.

## Reason field
- Approve: name the checks passed in short form, for example "all 10 checks pass; OOS PF 1.4 over 62 trades, 8 variants tried".
- Reject: name the first failing check and what's wrong, for example "check 3: total P&L +412 but trades sum to +188".
