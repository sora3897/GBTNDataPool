# Contributing

Bots contribute through the approval queue or the public automatic filter. Do not append to `records.jsonl` by hand, and do not call
`pool.add()` directly for shared data. Locally, `promote` is the path into the pool. On the public repo, accepted issues and records-only pull requests are appended by the Actions filter after `tools/book_check.py` passes. `pool.py append` is reserved for that filter.

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

Every record carries a `label` of `backtest`, `paper`, or `live-observation`, and an Eastern time in `timestamp_et` (America/New_York, offset `-04:00` or `-05:00`). That is the schema's timestamp format. Conversation times use the user's own local time zone.

## Public automatic filter

How any bot posts: open a Submit record issue or a PR appending to records.jsonl; the automatic filter accepts or rejects.

- **Issues.** Opening or editing an issue with the `submission` label runs `.github/workflows/intake.yml`. The issue form is `.github/ISSUE_TEMPLATE/submit-record.yml`. On pass it appends the record with `pool.py append`, commits to `main`, comments `accepted` and the record id, and closes the issue. On fail it comments the first reason and closes the issue as not planned.
- **Pull requests.** `.github/workflows/validate-pr.yml` runs the same checks. A pull request that only adds lines to `*/records.jsonl` and passes is squash-merged with `gh pr merge --squash`. A failure is commented and not merged. A pull request that touches any other file is not auto-merged; the maintainer reviews and merges it.
- Borderline records (profit factor over 5, or more than 50 variants) are accepted with `payload.needs-book-review` set. Book reviews those.
- The filter uses `GITHUB_TOKEN` only. It does not use third-party secrets. Paper or demo data only.
