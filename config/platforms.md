# Platforms

The coordinator writes the choice to `config/platform.json` (`platform`, `mode`, `chosen_at`). `mode` is always `paper`. Every bot reads that file before a paper or data step.

Bots never set up a real-money connection. The coordinator can walk the user through connecting their own demo or paper account with that platform's official login or API. A secret may sit in the bot's secure credential storage when the user wants that help. It is never pasted in chat, never written to the repo, the pool, or any file, and never shared. Step-by-step instructions are available instead. If a platform needs an account, it is the user's own demo or paper account.

While `platform` is `undecided`, the team runs backtests on free historical data only. No paper forward run.

## MetaTrader 5 (MT5)

Stored value: `mt5`. This is the platform the original team was built on. It suits forex, CFDs, and futures offered by an MT5 broker. Use the broker's **demo** account only. The user creates and logs into that demo account. The login stays out of chat, the repo, the pool, and files. Secure storage is the only place it may sit, and only if the user asks.

## MetaTrader 4 (MT4)

Stored value: `mt4`. It suits forex and CFD practice on the older terminal. Use an MT4 **demo** account only. The user connects their own demo login. The login stays out of chat, the repo, the pool, and files.

## TradingView

Stored value: `tradingview`. It suits chart-based paper tests and alerts. Use TradingView **Paper Trading**. Market history used for backtests must be free data the user can already see. The user signs into their own TradingView account if a paper session needs it. The login stays out of chat, the repo, the pool, and files.

## NinjaTrader (futures)

Stored value: `ninjatrader`. It suits futures practice. Use NinjaTrader **simulation** only, not a live futures account. The user connects their own sim connection. The login stays out of chat, the repo, the pool, and files.

## Tradovate (futures)

Stored value: `tradovate`. It suits futures practice. Use a Tradovate **simulation / demo** environment only. The user connects their own demo login. The login stays out of chat, the repo, the pool, and files.

## Interactive Brokers

Stored value: `interactive_brokers`. It suits multi-asset paper tests. Use an Interactive Brokers **paper-trading** account only. The user connects their own paper login. The login stays out of chat, the repo, the pool, and files. Never enable a live account.

## Solana DEX (Jupiter) for meme coins

Stored value: `solana_jupiter`. It suits paper study of Solana meme-coin quotes. Use public Jupiter quote data and a paper fill simulation only. There is no demo wallet. Bots never create, hold, or connect a wallet or a key.

## Polymarket / Kalshi (prediction markets)

Stored value: `polymarket_kalshi`. It suits paper outcome bets from public prediction-market prices. Use read-only public prices and a paper stake only. The user does not hand the bots a funded account. Bots never place a real-money order.

## I'll decide later

Stored value: `undecided`. The team runs backtests on free historical data only. The coordinator asks again the first time the user wants a paper forward run, then updates `platform` and `chosen_at`.
