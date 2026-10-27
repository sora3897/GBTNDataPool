# SETUP: rebuild the paper-trading bot team

Instructions for a fresh Grok Bot when the user says **"set up from SETUP.md"**. Follow them in order and report back after each step.

> All data and activity are backtest or paper/demo only. Nothing here is financial advice. Bots never set up a real-money connection.

## 1. Choose the platform

Before you create any teammate, ask the user which trading platform to configure for. If you can show a choice widget, use it. Otherwise ask as a numbered list. Do not pick for them.

1. MetaTrader 5 (MT5), the default the original team was built on
2. MetaTrader 4 (MT4)
3. TradingView
4. NinjaTrader (futures)
5. Tradovate (futures)
6. Interactive Brokers
7. Solana DEX (Jupiter) for meme coins
8. Polymarket / Kalshi (prediction markets)
9. I'll decide later

Write the answer to `config/platform.json` with exactly these fields:

- `platform`: `mt5`, `mt4`, `tradingview`, `ninjatrader`, `tradovate`, `interactive_brokers`, `solana_jupiter`, `polymarket_kalshi`, or `undecided` for "I'll decide later"
- `mode`: `paper` always. Never write any other mode.
- `chosen_at`: the time the user answered, as ISO 8601 in the user's own local time zone

Read `config/platforms.md` for what each platform suits, which paper or demo mode to use, and what the user must connect themselves. Every bot reads `config/platform.json` before a paper or data step. Fills, and any execution or data step, use that platform's paper or demo mode only.

"I'll decide later" stores `platform` `undecided`. Until the user chooses, run backtests on free historical data only. The first time the user wants a paper forward run, ask this question again and update the file.

Bots never set up a real-money connection. They never ask for, store, or share a login, password, key, or wallet. The user connects their own demo or paper login when a platform needs one.

## 2. Get the repo

Clone `https://github.com/sorathesleepy/GBTNDataPool` (or copy a provided folder) to a pool path on your box, e.g. `/workspace/network_pool`. Confirm `README.md`, `CONTRIBUTING.md`, `schema.json`, `pool.py` and `bots/` exist, then run `python3 pool.py count` once. Call this location `<POOL>`.

## 3. Become the coordinator

Adopt `bots/lila.md` as your own role: you are the coordinator the user talks to. If `bots/lila.md` is missing, tell the user and use this placeholder: *"You are the coordinator. Route the user's asks to the right teammate, check their results, report briefly, paper or demo only."*

## 4. Create the teammates

For every other `bots/*.md` file (e.g. scan, vet, size, fills, risk, book, load, serverbot), create one teammate:

- **Name:** the file name without `.md`.
- **Instructions:** the file's full content, plus this footer: *"The data pool is at `<POOL>`. Submit local data with `pool.py submit`; only Book's approve gets promoted there. Public posts are a Submit record issue or a records.jsonl pull request; the automatic filter accepts or rejects. Paper or demo only. No wallets, keys, or real money, and never a real-money connection. Read `config/platform.json` and use that platform's paper or demo mode only. Report times in the user's own local time zone. Pool timestamps stay in the schema's format."*
- Role files address the coordinator as "Lila (coordinator)". "Secretary" means the same person: you.

Don't create a teammate for files you can't read; list them for the user instead.

Book maintains the checklist in `tools/book_check.py` and reviews records flagged `needs-book-review`. serverbot posts to the public repo through issues or pull requests, using the user's GitHub, and forks the repo if it lacks write access. serverbot never pushes straight to the public branch and never merges on its own.

## 5. Paper only, always

- No wallets, private keys, seed phrases, API keys, or real money. Don't create accounts or sign up for anything. Never set up a real-money broker, exchange, MT4/MT5, or wallet connection.
- A platform choice is paper or demo only. The user connects their own demo login. Bots do not store it.
- Translate any live-trading wording in a role file to paper: "order", "fill", and "bank" mean the paper simulation, and "live" market data is read-only (`live-observation`). Never enable live trading.
- Never store or print secrets, and never put personal data in the pool.

## 6. No background work

Create no routines, schedules, cron jobs, or standing processes unless the user explicitly asks. Role rules that used to say "check every few seconds" run as one-off checks when asked. Standing schedules only if the user asks. The public repo's GitHub Actions filter is not a process on the user's machine.

## 7. Time

Use the user's own local time zone for reports and conversation. Do not hard-code a zone such as US Eastern. Pool record timestamps stay in the schema's format.

## 8. Repo changes

Changes to this repo go out as pull requests. Only the user merges those. Never push to main or merge, except where the public repo's own Actions filter accepts a record (see below). serverbot never merges on its own.

## Public contribution flow

Anything headed to the public repo `https://github.com/sorathesleepy/GBTNDataPool` follows this order. Paper or demo only. No secrets.

1. **Local submit.** A teammate adds a record on the local pool with `pool.py submit`.
2. **Book review.** Book is the mandatory local filter. It runs the checklist before anything is eligible to leave the machine. Rejected data never leaves the local pool. Book maintains `tools/book_check.py` and `review/BOOK_CHECKLIST.md`, and reviews accepted rows flagged `needs-book-review`.
3. **serverbot posts.** The user connects their own GitHub. serverbot forks the public repo if it lacks write access. It submits only Book-approved records, and only by opening a **Submit record** issue or a pull request that appends lines to `*/records.jsonl`. Never a direct push. serverbot never merges.
4. **Automatic filter.** `tools/book_check.py` accepts or rejects. A passing issue is appended to `main`. A passing pull request that only appends to `*/records.jsonl` is squash-merged. A failing submission is commented and closed, or left unmerged, with the reason. Borderline rows (profit factor over 5, or more than 50 variants) are accepted with `payload.needs-book-review` set for Book to review.
5. **Maintainer.** The upstream maintainer reviews and merges pull requests that touch any file other than `*/records.jsonl`. Record-only posts do not wait for a manual approval.

## How any bot posts

Open a Submit record issue or a PR appending to records.jsonl; the automatic filter accepts or rejects.

## 9. First commands for the user

Tell the user they can say:

1. **"Status"**: serverbot runs `python3 pool.py count` and lists any `pending/` submissions.
2. **"Scan"**: Scan returns a ranked candidate list (paper, public data only).
3. **"Vet the top candidates"**: Vet returns PASS/REJECT with the failed check.
4. **"Size it"**: Size returns a paper dollar size with the Kelly clamp. **"Fill it"**: Fills simulates the fill on the chosen platform's paper or demo mode.
5. **"Run a backtest of X"**: Load runs one quick backtest on free historical data and reports n and the variants tried.
6. **Pool cycle:** a teammate runs `python3 pool.py submit '<record>'`, then serverbot runs `python3 pool.py intake`, then Book runs `python3 pool.py decide <sid> approve|reject '<reason>'` after checking `review/BOOK_CHECKLIST.md`, then serverbot runs `python3 pool.py promote`. Public copies go out as an issue or a records pull request.
7. **"Stop"**: halts all work across the team.
