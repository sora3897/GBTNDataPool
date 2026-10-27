# Contributing

Bots add records only through `pool.add()` in a pull request. Do not append to `records.jsonl` by hand.

## Append-only records

Records are append-only. Do not edit or delete existing lines. A record is corrected by adding a new one whose `payload.supersedes` is the id of the record it replaces.

## No secrets

Do not add private keys, API keys, tokens, seed phrases, or broker or MT5 login numbers. `add()` rejects payloads that look like secrets. Keep them out of markdown and summary files as well.

## Labels and time

Every record carries a `label` of `backtest`, `paper`, or `live-observation`, and an Eastern time in `timestamp_et` (America/New_York, offset `-04:00` or `-05:00`).
