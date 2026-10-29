# Futures papers: short summaries

Our own short summaries of 11 papers. No excerpts, and the PDFs are not shipped. For each: the key finding, what it means for a retail futures desk, and a testable rule where there is one. Paper or demo only.

## Who we are and how markets behave

**Ferko, Mixon & Onur, "Retail Traders in Futures Markets," CFTC Office of the Chief Economist Staff Paper 2023-002, Feb 2024** (CFTC staff research, public).
- *Finding:* CFTC position data from 2021–22 shows about 7,000 to 8,000 retail traders a day. Most appear for only a handful of trades (median about 4, lasting about 4 days), hold one or two contracts, prefer micros, and win or lose a few hundred dollars per episode. They tend to buy after prices fall and sell after they rise, and they go short about as often as long. A bigger loss on the first trade predicts leaving futures for good.
- *For the desk:* the typical retail entry is contrarian, and the typical first experience is short and costly. Paper-first onboarding and small, fixed risk per trade target exactly that.
- *Testable rule:* compare contrarian entries (fade the last move) with trend-filtered entries (E10) on the same contracts and costs. Our backtests favour the trend-filtered side (kb/results.md).

**Hong, "A Model of Returns and Trading in Futures Markets," *Journal of Finance* 55(2), 2000.**
- *Finding:* in an equilibrium model with hedgers and informed speculators, a futures contract gets more volatile as expiry approaches (the Samuelson effect) when information differences are small. When information differences are large, that pattern can fail. The model also explains how open interest changes with time to maturity.
- *For the desk:* don't assume volatility is constant over a contract's life. Size from current volatility, and know where you are in the expiry cycle.
- *Testable rule:* measure realised volatility by days to expiry on unadjusted contract data. If it rises into expiry, roll earlier.

**Kyle & Obizhaeva, "Market Microstructure Invariance: Empirical Hypotheses," *Econometrica* 84(4), 2016.** https://doi.org/10.3982/ECTA10486
- *Finding:* measured in "business time", the size distribution of bets and their trading costs look the same across assets. Data from more than 400,000 portfolio-transition orders support this. It implies that cost in basis points rises with volatility and falls only slowly (roughly with the cube root) as dollar volume rises.
- *For the desk:* micro and E-mini index futures are among the most liquid markets, so our cost per trade is small, but it grows quickly in thinner contracts and in volatile periods.
- *Testable rule:* scale the slippage assumption with volatility ÷ (dollar volume)^(1/3), and check that thin contracts still pay after costs.

**Kim & Hansen, "The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures," 2026.** https://arxiv.org/abs/2607.09426
- *Finding:* on six Binance perpetual futures, volatility and volume burst at minute, five-minute and quarter-hour marks. Trade sizes get less round in those bursts, which points to algorithms. Returns at quarter-hour openings were predictable out-of-sample, and order imbalance at the opening predicted returns 4 to 12 hours ahead.
- *For the desk:* clock-time bursts exist. Our NQ data shows a milder version, with the top-of-hour minute the noisiest (kb/futures-stats.md). Avoid tight stops that trigger on the burst minute.
- *Testable rule:* on CME futures, test whether the sign of the first minute after :00/:15/:30/:45 predicts the next 15 to 60 minutes, out-of-sample and after costs, before using it.

## Machine learning applied to futures

**Guo, Wang, Zhang, Huang & Ma, "Trading Under Uncertainty: A Distribution-Based Strategy for Futures Markets Using FutureQuant Transformer," 2025.** https://arxiv.org/abs/2505.05595
- *Finding:* a transformer with quantile outputs forecasts a price range instead of a single point, with well-calibrated intervals. A simple rule set (RSI, ATR, Bollinger Bands plus the forecast band) beat the authors' baselines on 30-minute futures trades.
- *For the desk:* forecasting a range and its uncertainty is more useful than a point guess, because it sets stop and target distances directly.
- *Testable rule:* use a predicted range (or just ATR) to set stops and targets, and compare against fixed-tick exits.

**Cheng, Zhang, Zeng & Xue, "MOT: A Mixture of Actors Reinforcement Learning Method by Optimal Transport for Algorithmic Trading," 2024.** https://arxiv.org/abs/2407.01577
- *Finding:* several reinforcement-learning "actors", each specialising in one market pattern, with samples routed by optimal transport and pretraining on an expert strategy, did better than single-policy agents on Chinese stock-index futures (IF, CSI 300).
- *For the desk:* markets switch regimes, and one rule for all regimes is fragile.
- *Testable rule:* split days by a simple regime tag (trend vs range, high vs low volatility) and check whether E10's edge holds in each.

**Qin, Cai, Li, Xia, Zong, Sun, Wang & An, "FineFT: Efficient and Risk-Aware Ensemble Reinforcement Learning for Futures Trading," KDD 2026.** https://arxiv.org/abs/2512.23773
- *Finding:* an ensemble of RL agents, trained with selective updates, stress-tested on simulated market dynamics, and routed away from trading when the agents are uncertain, managed leveraged crypto futures more safely than baselines.
- *For the desk:* a "don't trade when unsure" switch is a risk tool in its own right.
- *Testable rule:* skip trading on days that look unlike the training history (for example, an opening range far outside its normal size, as E21 does) and measure the effect on drawdown.

**Xiong, Zhang, Feng, Sun & You, "QuantHarness: Price-Driven Multi-Agent LLMs for High-Frequency Trading," 2025/2026.** https://arxiv.org/abs/2509.09995
- *Finding:* four LLM agents (indicators, patterns, trend, risk) working from price data alone beat baselines on 1-hour and 4-hour predictions across nine instruments, including Nasdaq futures. Accuracy fell on 1- to 15-minute bars, and LLM latency is too slow for minute-level opportunities.
- *For the desk:* a bot team suits hourly decisions, not minute scalping. That matches our 1-hour backtests.
- *Testable rule:* keep LLM-driven decisions at 30 minutes or slower, and log latency.

**Du, "Machine Learning Enhanced Multi-Factor Quantitative Trading: A Cross-Sectional Portfolio Optimization Approach with Bias Correction," 2025/2026.** https://arxiv.org/abs/2507.07107
- *Finding:* in Chinese stocks, limit-locked prices that couldn't actually be traded leaked into rolling factors before filtering, inflating apparent predictive power while lowering the real Sharpe ratio. Masking untradeable data at load time was the single biggest improvement. Code: MIT-licensed ml-quant-trading (see quant-validation-toolkit.md).
- *For the desk:* exclude bars you couldn't have traded (halts, limit-locked futures, closed sessions) **before** computing any indicator.
- *Testable rule:* rerun a backtest with a tradability mask applied first, and compare the results.

## Order books

**Linna, Baltakys, Manoharan, Iosifidis & Kanniainen, "Repurposing Deep Limit Order Book Forecasting for Scenario-Conditioned Market Impact Modeling," 2026.** https://arxiv.org/abs/2609.16930
- *Finding:* a pretrained order-book forecaster can estimate the short-term impact of a hypothetical order by comparing its forecasts with and without the order. The rankings matched real outcomes closely.
- *For the desk:* useful for execution research, not for micro-sized paper trades, where our impact is negligible.

**Chen, Liu, Xu & Yang, "Probabilistic Limit Order Book Forecasting with Conditional Diffusion Models," 2026.** https://arxiv.org/abs/2610.25495
- *Finding:* a diffusion model conditioned on recent order-book history (LOBGrad) forecasts the distribution of queue depths and mid-price moves better than baselines, and reproduces known order-book patterns.
- *For the desk:* background reading. Order-book data isn't part of our pipeline, and a distribution forecast matters more than a point forecast.
