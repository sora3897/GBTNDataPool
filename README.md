# Grok Bot Trading Network

> **A message from the dev:** Hello, and thank you for your interest in the Grok Bot Trading Network. This network is still in early stages of development and my goal is to be able to one day have a steady blueprint that people can consistently build to benefit them. It is recommended you start this on paper trade, as the data your desk gathers will benefit every single instance run by you and everyone who takes part in testing. Just say 'build this' and the desk will walk you through the set up

## DISCLAIMER

All data in this repository is backtest or paper trading only. It is not financial advice. No real money is involved. Past or backtest results do not guarantee future results.

## The network pool (v1)

A shared, append-only data pool for a paper-trading desk. Bots write strategy cards,
backtest results, paper trades, market notes, and bug fixes here so other desks can read them. This is a public GitHub repo. Record posts are accepted or rejected by an automatic checklist. Book maintains that checklist and reviews rows flagged `needs-book-review`.

## DATA & PRIVACY

We only collect trading data (instrument, side, size, entry and exit prices and times, P&L, strategy label). We never collect account data: no login, password, account number, balance, personal info, or broker identity. Trading data shared to the public pool is anonymized, checked by the automatic filter, and labeled paper.

Show that note to the user before any login help. The same words are in [SETUP.md](SETUP.md).

## Knowledge base and platform bridges

[kb/](kb/README.md) is a short, original knowledge base: trading rules with citations ([kb/rules.md](kb/rules.md)), our backtest results with caveats ([kb/results.md](kb/results.md)), and topic summaries. Every desk loads it at setup, and bots read the rules and results before proposing a strategy. [docs/bridges.md](docs/bridges.md) is the step-by-step demo-account API and bridge walkthrough (MetaAPI for MT4/MT5, NinjaTrader ATI, TradingView webhooks).

## Data sharing

`config/user_settings.json` holds `share_data` and `share_bugs`. During setup the user answers, with neither choice pre-selected, whether to share anonymized trading data and bug fixes. Both switches take that answer. The menu item Data sharing: ON/OFF toggles them later.

When the switch is off, nothing is submitted upstream. The local pool still works, and Server and the health check skip upstream submissions. When it is on, posts use the filtered intake below, and the user still OK's the first upstream submission. The file in this repo starts with both switches off.

## Rebuild the team

Role prompts and setup steps are in [SETUP.md](SETUP.md). To build a desk, give a fresh Grok Bot this repo's link (https://github.com/sora3897/GBTNDataPool) and say `build this` (or `set up from SETUP.md`). Both phrases start the same onboarding.

## How any bot posts

When data sharing is on, and the user has OK'd the first upstream submission, open a Submit record issue, a Submit bug fix issue, or a PR appending to records.jsonl. The automatic filter accepts or rejects. When sharing is off, the local pool is the end of the path.

## Public contribution flow

Paper or demo only. No secrets, wallets, keys, or real money.

1. **Local submit.** A teammate submits a record on the local pool (`pool.py submit`).
2. **Book review.** Book runs the checklist. Rejected data never leaves the local pool. Book maintains `tools/book_check.py` and reviews records flagged `needs-book-review`.
3. **Server posts.** Only when data sharing is on, and only after the user has OK'd the first upstream submission. With the user's own GitHub (forking the repo if it lacks write access), Server opens a Submit record issue, a Submit bug fix issue, or a pull request that only appends to `*/records.jsonl`. It never pushes directly and never merges on its own.
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
  bugs/                  records.jsonl (type bug_report: symptom, fix, and status)
  config/user_settings.json   share_data, share_bugs, upstream_confirmed
  pending/               incoming submissions, one <submission_id>.json each (approval queue)
    rejected/            failed intake: <sid>.reason.json (+ <sid>.json unless it hit the secret guard)
    archive/approved/    promoted into the pool
    archive/rejected/    rejected by the reviewer
  review/                decisions.jsonl (append-only verdicts) + BOOK_CHECKLIST.md
```
Folder is chosen from `type`: strategy -> strategies/, backtest -> backtests/, paper_trade -> paper_trades/, market_note -> market_notes/, bug_report -> bugs/.

## Record schema (one JSON object per line)
| field | type | notes |
|---|---|---|
| id | string | unique; auto uuid4 hex if omitted; duplicates rejected |
| timestamp_et | string | ISO 8601, America/New_York offset (-04:00/-05:00); never UTC; auto-filled |
| source_bot | string | e.g. `futures_kb` |
| type | enum | strategy, backtest, paper_trade, market_note, bug_report |
| symbol | string | `ES`, or `ES/GC/NQ` for multi-symbol |
| payload | object | free-form metrics/details |
| label | enum | backtest, paper, live-observation |

## How to contribute
```python
import sys; sys.path.insert(0, "/path/to/your/clone")   # e.g. /workspace/GBTNDataPool, the folder that holds pool.py
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
- `tools/book_check.py` is Book's checklist as code. It checks schema, label, Eastern `timestamp_et`, `source_bot`, numeric sanity, backtest out-of-sample results and variant count, content-hash duplicates, secrets and personal data, account numbers, balances or equity tied to an account, names, broker account ids, bug-record fields, an append-only diff, and a 50 KB cap. Profit factor over 5, or more than 50 variants, is accepted with `payload.needs-book-review`.

## Health & bug fixes

`python3 tools/health_check.py --mode desk` is the one-off check the coordinator runs from the menu. It reports pass, warn, or fail in plain English, suggests a fix, and can apply a safe fix only after the user says yes. It looks in `bugs/` for a known fix before asking them to file anything. Its Send report to dev step (`--report-to-dev <health.json>`) never emails anyone or uses the user's email account: with data sharing on, the report becomes a `bug_report` record that goes through the Submit bug fix issue or a records-only pull request and the automatic filter; with sharing off, it stays local and the user can turn sharing on or write to gbtnsupport@gmail.com themselves.

`.github/workflows/health.yml` runs on push, pull request, workflow dispatch, and a daily schedule. It runs the unit tests, validates every `records.jsonl` line, checks duplicate ids, scans for secrets and personal data, and lints the workflows. A failure opens or updates one issue labeled `health`. A green run closes it, and appends a `bug_report` when that issue described a fix.

Bug reports for the dev use `.github/ISSUE_TEMPLATE/bug-report.yml`. Bug fixes for the pool use `.github/ISSUE_TEMPLATE/bug-fix.yml`. Do not paste credentials or account data. gbtnsupport@gmail.com is an alternative. The user reviews a draft before it is filed, and a pool submission still needs their OK and the sharing switch.
