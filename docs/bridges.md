# Platform API and bridge walkthrough (demo accounts only)

The coordinator uses this file to walk any user, step by step and assuming no experience, through getting API access or a bridge for their platform so the desk's paper fills can land inside their own **demo** account. Open it from the main menu: **Switch platforms → Connect my platform for demo fills (API or bridge walkthrough)**, or from the menu item **Connect my platform for demo fills (API or bridge walkthrough)**.

Read `config/platform.json` first and show only the section for that platform. Go one step at a time. After each step, wait for the user to say done, and offer these choices: **Next step**, **I'm stuck, explain more**, **Back to main menu**.

> DATA & PRIVACY: The network collects trading data only (instrument, side, size, entry and exit prices and times, P&L, strategy label). It never collects account data: no login, password, API token, account number, balance, personal info, or broker identity.

## Rules for every platform

1. **Keys stay secret.** API tokens, account ids, passwords and webhook secrets are saved only in the user's own secret store (the bot's secure credential storage, or a masked input field). They are never pasted into chat, never written to the repo, the pool, a log, or any file, and never committed. If the user pastes one into chat by mistake, tell them to revoke it and make a new one.
2. **Demo check before anything runs.** Before the first fill, the coordinator confirms the account is a demo or simulation account (see each section). If it can't confirm that, it stops and says so. Record only the result: `python3 tools/health_check.py --mark-demo-connected true` or `false`.
3. **Real money stays off.** Real-money fills are a separate, deliberate switch that is **off by default and not built**. See "Future step" at the end. Nothing in this walkthrough turns it on.
4. **Back to main menu** is offered at every step. Typing menu works too.
5. If any official page looks different from these steps, follow the official page. These steps describe what to look for, not exact clicks.

## MetaTrader 5 or MetaTrader 4, through MetaAPI

Why MetaAPI: the official `MetaTrader5` Python package talks to a MetaTrader terminal running on Windows. A Linux box (like this one) has no Windows terminal, so use MetaAPI (metaapi.cloud), a cloud service that hosts the connection to an MT4 or MT5 account and gives you an API.

1. **Get an MT demo account.** If you don't have one, open a demo account with your broker, or from the MetaTrader app (it offers demo accounts). Write down the demo login number and server name somewhere private. The server name usually says Demo.
2. **Make a MetaAPI account.** Go to metaapi.cloud and sign up. Check their current pricing and free-tier limits before you add anything.
3. **Add your demo MT account.** In the MetaAPI dashboard, find the section for adding a trading account. Choose MT4 or MT5, then enter the demo login and server. Type the password on MetaAPI's own page, never in chat. MetaAPI needs the account's trading password (not the read-only investor password) to place demo orders.
4. **Get the API token.** In the dashboard, find API access or tokens and create a token. Save it straight into your secret store or the masked input the coordinator offers. Don't paste it here.
5. **Get the account id.** The dashboard lists your accounts, each with an id. Save that the same way. The account id, login, and server name stay private: never in chat, a log, the repo, or the pool.
6. **Make sure the account is deployed.** In the MetaAPI dashboard the account must show as deployed and connected to the broker before any call works. A just-added account can take a few minutes. If the test call says the account is not deployed or not connected, deploy it in the dashboard, wait, and try again.
7. **Demo check.** The coordinator makes one read-only test call with MetaAPI's official SDK (`metaapi-cloud-sdk`) or its REST API, reading the token and account id from the secret store without printing them. It asks for the account information and reads only two fields from it: `type` and `tradeAllowed`. The account counts as demo only when `type` is exactly `ACCOUNT_TRADE_MODE_DEMO`; `ACCOUNT_TRADE_MODE_CONTEST`, `ACCOUNT_TRADE_MODE_REAL`, a missing value, or a failed call all count as not demo. The same response also carries the balance, equity, login, name, broker, and server, so the coordinator discards it right away and never prints, logs, or saves it. You see only "demo: yes" or "demo: no".
   - If it is not clearly demo, stop and pick a demo account.
   - If `tradeAllowed` is false, the account was most likely added with the read-only investor password. Update it in MetaAPI's dashboard with the trading password (typed on MetaAPI's page, never in chat).
8. **Done.** Record only the result with `python3 tools/health_check.py --mark-demo-connected true` (or `false`) and return to the main menu. The desk still does nothing until you say start.

## NinjaTrader (futures), on a Sim account

NinjaTrader runs on Windows. Fills go to a simulation account (NinjaTrader includes a built-in Sim account) or your broker's demo.

1. **Install NinjaTrader** on a Windows machine and sign in. Keep the active account set to a Sim or demo account.
2. **Choose a connection:**
   - **Automated Trading Interface (ATI):** NinjaTrader's built-in way for outside programs to send orders. In NinjaTrader's options, find the Automated Trading Interface settings and turn ATI on. Outside programs can then send orders, for example as order instruction files dropped into NinjaTrader's incoming folder. Check NinjaTrader's help guide for the exact format.
   - **A bridge:** a third-party tool that connects alerts or another app to NinjaTrader. Use one only from a source you trust, and only on the Sim account.
3. **Point it at the Sim account only.** Every order the desk sends names the Sim or demo account. Never a live account.
4. **Demo check.** The coordinator confirms that the account name it sends to is a Sim or demo account, and that a test order shows up there. If you aren't sure, stop.
5. **Done.** Mark it connected and return to the main menu.

## TradingView: alerts and webhooks only

TradingView has no order API for this. It can send **alerts**, and an alert can call a **webhook** URL. Webhooks may need a paid TradingView plan, so check your plan.

1. **Set up a receiver.** The desk needs a small HTTPS endpoint that receives the alert and turns it into a paper fill in the desk's own simulation (or on another platform's demo account). Keep any shared secret for the webhook in the secret store.
2. **Create an alert.** On your chart or strategy, create an alert. In its notification settings, turn on webhook and enter the receiver URL. Put only trade fields in the message (symbol, side, size, price, strategy label), never account details.
3. **Test it.** Fire one test alert and confirm the receiver logged a paper fill.
4. **Done.** Return to the main menu. TradingView itself never places orders here.

## I'll decide later

Nothing to connect. The desk runs backtests on free historical data only. When you pick a platform, come back here from Switch platforms.

## Other platforms (short version)

- **Tradovate:** has an API with a separate demo environment. Use the demo environment and demo credentials only.
- **Interactive Brokers:** use a paper trading account with TWS or IB Gateway and their API. The paper account is separate from any live account.
- **Solana DEX (Jupiter)** and **Polymarket / Kalshi:** simulated only. No wallet, no private key, no funded account. Nothing to connect.

## Future step: real-money fills (not built)

A real-money switch may come later as a separate, deliberate step. When it does, it must be off by default, need its own explicit opt-in that names real money, pass the demo-to-live checks again, and never turn on from a teammate's say-so. Until then, every bot is paper or demo only, and no part of this repo places real orders.
