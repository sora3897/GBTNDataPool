# Trading rules and their sources

Each rule is our paraphrase, followed by where it comes from. "Desk choice" means we picked it, not a source. Freeze every threshold before a test runs (see the guards at the end).

## Trend and entry: Elder's triple screen

1. **First screen (the tide).** Trade only in the direction of the longer-timeframe trend. We use the slope of a 13-period EMA on the daily chart (the prior completed day): rising means long only, falling means short only.
2. **Second screen (the wave).** On the trading timeframe, wait for a pullback against that trend. We use a 2-period EMA of the Force Index (price change × volume): below zero in an uptrend is a buy setup, above zero in a downtrend is a sell setup.
3. **Third screen (the entry).** Enter with a stop order just beyond the signal bar's high (long) or low (short), valid for the next bar only. If it doesn't trigger, the setup expires.

Source: Alexander Elder, *Trading for a Living*, Wiley, 1993 (triple screen chapter).

How it went for us: the raw triple screen on 1-hour futures lost money in every risk setup we tried (see results.md). Its first screen did help as a trend filter on opening-range entries (E5, E10, E21).

## Risk per trade and per month

4. **The 2% rule.** Never risk more than 2% of account equity on one trade. Size = (equity × risk %) ÷ distance to the stop, rounded down to whole contracts. If that's less than one contract, skip the trade. Source: Elder, *Trading for a Living* (1993), the 2 percent rule.
5. **The 6% rule.** Stop opening new trades for the rest of the month once losses for the month reach 6% of equity. Source: Elder, *Come Into My Trading Room*, Wiley, 2002.
6. **Our default (desk choice, inside the 2% rule):** risk 1% per trade, stop for the day after a 2% daily loss, at most 3 trades a day, at most 10 micros per trade and 2 open positions.

## Trade management: Jim Wyckoff's rules

7. **Never add to a losing position.** One position per symbol, no averaging down. Source: Jim Wyckoff, *Trading Smart: 92 Tools, Methods and Helpful Hints to Help You Succeed at Futures Trading*, 2003.
8. **Keep strategies simple, and always use a protective stop.** Same source.
9. **Trade with the trend.** Same source. It agrees with Elder's first screen.

## Making technical rules testable: Lo, Mamaysky and Wang

10. **Define the pattern objectively.** Smooth prices over a fixed window, then define the pattern with exact inequalities on the turning points. No "looks like".
11. **Test conditional against unconditional.** A pattern is useful only if returns after it differ from ordinary returns, tested formally. Then, separately, check whether it still pays after costs. Those are two different hurdles.
12. **Every free threshold counts as a variant.** Window lengths, bands and smoothing settings all add to the multiple-testing count.

Source: Andrew W. Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation," *Journal of Finance* 55(4), 2000. https://www.nber.org/papers/w7613

## Exits

13. **Time stop.** Close a trade that hasn't worked within a set time (we use 24 bars, or the session close for opening-range trades). A support or breakout thesis decays. Source: Vicky Henderson, Saul Jacka, Ruiqi Liu and Junichi Maeda, "The Support and Resistance Line Method: An Analysis via Optimal Stopping," 2021/2025. https://arxiv.org/abs/2103.02331
14. **Breakeven stop.** After the trade moves +0.5R in your favour, move the stop to the entry price (desk choice, used in E10 and E21).
15. **Pick exits from the population, not from a grid search.** Choose stop, target and time limit from a model of how past trades behaved after entry, rather than by trying many exits on the same data. Source: Peter Carr and Marcos López de Prado, "Determining Optimal Trading Rules without Backtesting," 2014. https://arxiv.org/abs/1408.1159

## Guards against overfitting and small samples

16. **Freeze rules before the run.** Write the rule, thresholds, costs and test split down first, and don't change them after seeing results. Source: Lo, Mamaysky and Wang (2000), and Bailey et al. (below).
17. **Split by time.** Test on a later, untouched period (we use 60% in-sample, 40% out-of-sample). Walk forward when you can. Source: Daniel P. Palomar, "Backtesting Portfolios," HKUST MAFS5310 lecture slides, 2020. https://palomar.home.ece.ust.hk/MAFS5310_lectures/slides_backtesting.pdf
18. **Beat a random baseline.** Compare against random entries with the same stop, target and costs. We require the 95th percentile or better. Desk practice.
19. **Count every variant you tried.** With many variants, the best one looks good by luck. Raise the bar to about t ≈ 3 instead of 2. Source: Campbell R. Harvey and Yan Liu, "Backtesting," *Journal of Portfolio Management*, 2015.
20. **Deflate the Sharpe ratio.** Adjust the best Sharpe ratio for the number of trials, skew and fat tails before believing it. Source: David H. Bailey and Marcos López de Prado, "The Deflated Sharpe Ratio," *Journal of Portfolio Management*, 2014.
21. **Estimate the probability of backtest overfitting.** Use combinatorially symmetric cross-validation across your variants. If the in-sample winner often lands below median out-of-sample, don't promote it. Source: David H. Bailey, Jonathan Borwein, Marcos López de Prado and Qiji Jim Zhu, "The Probability of Backtest Overfitting," *Journal of Computational Finance*, 2017.
22. **Expect backtests to shrink.** Assume a live Sharpe ratio around half the backtest's, or worse after heavy iteration. Source: Adam Rej, Philip Seager and Jean-Philippe Bouchaud, "How Should You Discount Your Backtest PnL?," 2018. https://arxiv.org/abs/1902.01802
23. **Check for look-ahead leaks separately.** Overfitting statistics don't catch a feature that peeks at the future. Every input must be timestamped no later than the decision. Source: E. Gençay, "What survives honest evaluation?," 2026. https://arxiv.org/abs/2608.27734
24. **Don't trust a short record.** Work out the minimum track record length before calling an edge real. Source: David H. Bailey and Marcos López de Prado, "The Sharpe Ratio Efficient Frontier," *Journal of Risk*, 2012. https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf
25. **Remove the top few trades.** If dropping the best 3 trades flips the sign, there's no demonstrated edge. Source: A. U. Kamat, 15-day paper-trading case study, 2026. https://arxiv.org/abs/2606.08232
26. **Don't peek and stop.** Checking results often and stopping at the first p < 0.05 inflates false positives. Use always-valid tests if you monitor continuously. Source: Ramesh Johari, Leonid Pekelis and David Walsh, "Always Valid Inference," 2019. https://arxiv.org/abs/1512.04922
27. **Bet less than full Kelly.** Edges from small, selected samples are overstated, so size at half Kelly or less, inside the 2% rule. Source: Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market," 2006.
