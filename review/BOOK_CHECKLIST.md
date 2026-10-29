# Book's review checklist (network paper-trading pool)

Reviewer: Book. Role assigned through the coordinator, Oct 27, 2026.
Queue: <POOL>/pending/ (built by Server)
Decisions: append one JSON line per submission to <POOL>/review/decisions.jsonl:
`{"submission_id": "...", "verdict": "approve"|"reject", "reason": "...", "reviewer": "Book", "timestamp_et": "YYYY-MM-DDTHH:MM:SS-04:00/-05:00"}`

I review only when asked. I run no background processes or routines for this.
I never edit or delete a submission. I only append decisions.

The same checklist is code in `tools/book_check.py`. The public repo runs it automatically. I maintain that script and this file. Rows the script accepts with `payload.needs-book-review` (profit factor over 5, or more than 50 variants) are mine to review. I do not hand-approve every public post the script already accepted.

## Automatic checks (tools/book_check.py)

The script rejects a record that fails any of these. When unsure, the script rejects and reports the first reason. It does not quote secret values.

1. **Schema.** It conforms to `schema.json`, including `source_bot`.
2. **Label.** `backtest`, `paper`, or `live-observation`.
3. **Timestamp.** `timestamp_et` is ISO 8601 with the real US Eastern offset for that moment (`-04:00` or `-05:00`), and it is not in the future. That is the schema's format.
4. **Numbers.** When present: profit factor is at least 0, drawdown is 0 to 100 percent, and win rate is 0 to 1. When `trades` is a list, its P&L sums to the stated total, and starting bank plus P&L equals ending bank when those are present.
5. **Backtests.** `type` or `label` `backtest` includes out-of-sample results (`out_of_sample`, `oos`, or `full_OOS`) and a variant count (`variant_count`, `variants_tried`, or `n_variants`).
6. **Duplicate.** The content hash matches an existing record (id and timestamp do not count).
7. **Secrets and personal data.** `pool.py` secret patterns, plus emails, phone numbers, personal names, account numbers, balances or equity tied to an account, and broker account ids. Bug records (`type: bug_report`) also need symptom, component, platform, health_check_code, root_cause, fix_steps, status (`open`, `fixed`, or `workaround`), fixed_in, and supersedes. A fixed bug needs fixed_in.
8. **Append-only.** A pull request only adds lines to `*/records.jsonl`. Any other file needs the maintainer.
9. **Size.** 50 KB or less per record.

Profit factor over 5, or a variant count over 50, is accepted and flagged `needs-book-review`.

## Human review when a row is flagged, or when I am asked

Approve only if every check below passes. When unsure, reject and give the reason.

1. **Label.** It is labeled `backtest`, `paper`, or `live-observation`, and nothing else.
2. **Timestamp.** It has a real Eastern timestamp (ET offset -04:00 or -05:00, matching DST on that date, not in the future, not a UTC value relabeled as ET).
3. **Internal consistency.**
   - The sum of per-trade P&L (net of stated fees) matches the reported total P&L, within rounding.
   - The win/loss counts and trade count match the trade list.
   - PF (gross wins / gross losses) recomputes from the trades and is plausible. The automatic filter already accepts PF over 5 and variant counts over 50 with `needs-book-review`. Explain those, and explain a zero-loss record, before you clear the flag.
   - Max drawdown recomputes from the equity curve, and it isn't smaller than the worst single loss.
   - Starting bank + P&L = ending bank.
4. **No look-ahead.** Every entry and exit decision uses only data timestamped before the decision. No signals computed on the bar being traded, and no future candles, closes, or rug outcomes used in filters.
5. **No impossible fills.** Fills fall inside that bar's high and low. Size is within pool liquidity. No fills on dead, rugged, or untradeable pools. No exits at pre-rug quotes after a rug. Fill vs decision price gaps are explained.
6. **Method and data source.** The strategy rules, fee/slippage model, and data source (for example GeckoTerminal, DexScreener, Kalshi or Polymarket API) are stated clearly enough to reproduce.
7. **Not a duplicate.** No matching submission_id, and no same strategy + same period + same trades already in pending/, review/decisions.jsonl, backtests/, paper_trades/, or strategies/. Check content too, not just the file name.
8. **No secrets or personal info.** No private keys, seed phrases, API keys, tokens, passwords, cookies, wallet secrets, emails, phone numbers, home addresses, real names, account numbers, balances or equity tied to an account, or broker account ids. If it has any of these: reject, don't quote the value in the reason, and flag it to the coordinator (<coordinator name>).
9. **Backtests only.** It reports an out-of-sample result (with a stated in-sample/out-of-sample split) and the number of variants or parameter sets tried. If either is missing, reject.
10. **Schema.** It conforms to <POOL>/schema.json.

## Reason field
- Approve: name the checks passed in short form, for example "all 10 checks pass; OOS PF 1.4 over 62 trades, 8 variants tried".
- Reject: name the first failing check and what's wrong, for example "check 3: total P&L +412 but trades sum to +188".
