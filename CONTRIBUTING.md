# Contributing

Bots contribute through the approval queue. Do not append to `records.jsonl` by hand, and do not call
`pool.add()` directly for shared data: `promote` is the only path into the pool.

## Flow: submit -> intake -> decide -> promote

1. **Submit.** `python3 pool.py submit '<record json>'` (or `submit(record)`) writes
   `pending/<submission_id>.json` = `{submission_id, submitted_at_et, status: "submitted", record}`.
   `id` and `timestamp_et` are fixed at submit time. A record that trips the secret guard is refused and
   nothing is written.
2. **Intake.** `python3 pool.py intake` validates every unvalidated file in `pending/` with `schema.json` and
   the secret guard (and rejects ids already in the pool). Passing files get `status: "valid"`. Failures move to
   `pending/rejected/<sid>.json` with a `<sid>.reason.json` sidecar. If a file hits the secret guard, the file
   is deleted and only the reason (pattern name, never the value) is kept in the sidecar.
3. **Decide.** The reviewer reads `review/BOOK_CHECKLIST.md`, then runs
   `python3 pool.py decide <submission_id> approve|reject '<reason>' [--reviewer Book]`. This appends
   `{submission_id, verdict, reason, reviewer, timestamp_et}` to `review/decisions.jsonl` (append only; to change
   a verdict, append a new line, the latest one wins). The verdict must be `approve` or `reject`, the reason is
   required, and the submission must be in `pending/`.
4. **Promote.** `python3 pool.py promote` acts on valid pending submissions using the latest decision from the
   authorized reviewer (**Book**; decisions by anyone else are ignored):
   approve -> appended through `add()` to the right `records.jsonl`, file moved to `pending/archive/approved/`;
   reject -> moved to `pending/archive/rejected/`; no decision -> left in `pending/`.
   It is idempotent: a record id already in the pool is never appended twice.

## Append-only records

Records are append-only. Do not edit or delete existing lines. A record is corrected by adding a new one whose `payload.supersedes` is the id of the record it replaces.

## No secrets

Do not add private keys, API keys, tokens, seed phrases, or broker or MT5 login numbers. `submit()`, `intake`
and `add()` reject payloads that look like secrets. Keep them out of markdown, summary and decision files as well.

## Labels and time

Every record carries a `label` of `backtest`, `paper`, or `live-observation`, and an Eastern time in `timestamp_et` (America/New_York, offset `-04:00` or `-05:00`).
