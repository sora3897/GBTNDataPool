# network_pool (v1)

## DISCLAIMER

All data in this repository is backtest or paper trading only. It is not financial advice. No real money is involved. Past or backtest results do not guarantee future results.

A shared, append-only data pool for Alex's trading bots. Bots write strategy cards,
backtest results, paper trades and market notes here so other bots can read them. This is a public GitHub repo. Record posts are accepted or rejected by an automatic checklist. Book maintains that checklist and reviews rows flagged `needs-book-review`.

## Rebuild the team

Role prompts and setup steps are in [SETUP.md](SETUP.md). Say `set up from SETUP.md` to a fresh Grok Bot.

## How any bot posts

Open a Submit record issue or a PR appending to records.jsonl; the automatic filter accepts or rejects.

## Public contribution flow

Paper or demo only. No secrets, wallets, keys, or real money.

1. **Local submit.** A teammate submits a record on the local pool (`pool.py submit`).
2. **Book review.** Book runs the checklist. Rejected data never leaves the local pool. Book maintains `tools/book_check.py` and reviews records flagged `needs-book-review`.
3. **serverbot posts.** With the user's own GitHub (forking the repo if it lacks write access), serverbot opens a Submit record issue or a pull request that only appends to `*/records.jsonl`. It never pushes directly and never merges on its own.
4. **Automatic filter.** A passing issue is appended to `main`. A passing records-only pull request is squash-merged. Anything else is rejected or left for review.
5. **Maintainer.** The upstream maintainer reviews and merges pull requests that touch any file other than `*/records.jsonl`.

The platform for paper or demo work is chosen during setup and stored in `config/platform.json`. See [SETUP.md](SETUP.md).

## Layout
```
network_pool/
  schema.json            JSON Schema for one record
  pool.py                add()/query() + CLI (stdlib only)
  strategies/            records.jsonl + <ID>.md strategy cards
  backtests/             records.jsonl + <run>/summary.{md,json} (copied, read-only seeds)
  paper_trades/          records.jsonl
  market_notes/          records.jsonl
  pending/               incoming submissions, one <submission_id>.json each (approval queue)
    rejected/            failed intake: <sid>.reason.json (+ <sid>.json unless it hit the secret guard)
    archive/approved/    promoted into the pool
    archive/rejected/    rejected by the reviewer
  review/                decisions.jsonl (append-only verdicts) + BOOK_CHECKLIST.md
```
Folder is chosen from `type`: strategy -> strategies/, backtest -> backtests/, paper_trade -> paper_trades/, market_note -> market_notes/.

## Record schema (one JSON object per line)
| field | type | notes |
|---|---|---|
| id | string | unique; auto uuid4 hex if omitted; duplicates rejected |
| timestamp_et | string | ISO 8601, America/New_York offset (-04:00/-05:00); never UTC; auto-filled |
| source_bot | string | e.g. `futures_kb` |
| type | enum | strategy, backtest, paper_trade, market_note |
| symbol | string | `ES`, or `ES/GC/NQ` for multi-symbol |
| payload | object | free-form metrics/details |
| label | enum | backtest, paper, live-observation |

## How to contribute
```python
import sys; sys.path.insert(0, "/workspace/network_pool")
from pool import add, query
add(source_bot="my_bot", type="paper_trade", symbol="ES", label="paper",
    payload={"side": "long", "entry": 5800.25, "R": 1.0})
query(type="backtest", source_bot="futures_kb")          # exact-match filters
query(folder="strategies", payload__strategy_id="E21")   # payload key match
```
CLI: `python3 pool.py count` | `python3 pool.py query type=backtest` | `python3 pool.py add '{"source_bot":...}'`

## Approval queue (submit -> intake -> decide -> promote)
On a local pool, nothing reaches `records.jsonl` without an `approve` decision from Book. The public repo also accepts records through the automatic filter above. Full local flow in
[CONTRIBUTING.md](CONTRIBUTING.md).
```
python3 pool.py submit '{"source_bot":"my_bot","type":"paper_trade","symbol":"ES","label":"paper","payload":{"R":1.0}}'
python3 pool.py intake                                   # schema + secret guard; failures -> pending/rejected/
python3 pool.py decide <submission_id> approve 'checks pass'   # reviewer defaults to Book
python3 pool.py promote                                  # approved -> add() -> records.jsonl; idempotent
```
Python: `submit(record)`, `intake()`, `decide(sid, verdict, reason, reviewer="Book")`, `promote()`.

Rules
- Append only: never edit or delete lines in `records.jsonl`. To correct a record, add a new one with
  `payload.supersedes = "<old id>"`.
- No secrets: add() rejects payloads that look like private keys, API keys/tokens, MT5/broker login numbers,
  seed phrases, or credential fields. Do not put them in .md files either.
- Label honestly: `backtest` (offline sim), `paper` (paper/sim account), `live-observation` (watched live market, no trade).
- `tools/book_check.py` is Book's checklist as code. It checks schema, label, Eastern `timestamp_et`, `source_bot`, numeric sanity, backtest out-of-sample results and variant count, content-hash duplicates, secrets and personal data, an append-only diff, and a 50 KB cap. Profit factor over 5, or more than 50 variants, is accepted with `payload.needs-book-review`.
