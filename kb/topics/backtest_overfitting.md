# Backtest overfitting and multiple testing

The more variants you try, the better the best one looks by luck alone. These papers measure that and correct for it.

- **Probability of backtest overfitting (PBO).** Split the history into blocks and test every combination of in-sample and out-of-sample halves. PBO is how often the in-sample winner lands in the bottom half out-of-sample. A high PBO means the leaderboard's top spot is mostly noise. — Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting," *Journal of Computational Finance*, 2017.
- **Deflated Sharpe ratio and minimum backtest length.** Adjust the best Sharpe ratio for the number of trials, skew and fat tails. With enough trials, even random strategies show a high Sharpe ratio on a short backtest. — Bailey & López de Prado, "The Deflated Sharpe Ratio," *Journal of Portfolio Management*, 2014.
- **Haircut the Sharpe ratio for multiple testing.** Use Bonferroni, Holm or BHY adjustments. With about 20 variants, the bar is roughly t ≈ 3, not 2. — Harvey & Liu, "Backtesting," *Journal of Portfolio Management*, 2015; Harvey, Liu & Zhu, "...and the Cross-Section of Expected Returns," *Review of Financial Studies*, 2016.
- **Data-snooping tests.** White's Reality Check, Hansen's SPA test and Romano-Wolf's stepwise method test the best of many strategies against a benchmark while allowing for the search. — White, *Econometrica*, 2000; Hansen, *Journal of Business & Economic Statistics*, 2005; Romano & Wolf, *Econometrica*, 2005.
- **Discount your backtest.** Iterating until a strategy looks good inflates its Sharpe ratio. Expect roughly half in live trading. — Rej, Seager & Bouchaud, 2018. https://arxiv.org/abs/1902.01802
- **Choose exits without grid-searching them.** Fit a simple model of post-entry price paths and pick stop, target and holding time from simulations. — Carr & López de Prado, 2014. https://arxiv.org/abs/1408.1159
- **Leakage is separate from overfitting.** Overfitting statistics can't detect look-ahead leaks. Check timestamps as their own gate. — Gençay, 2026. https://arxiv.org/abs/2608.27734
- **Survivorship bias.** Testing only on assets that still exist, or with data that peeks ahead, inflates results. Build the universe as it was at each date. — summary of crypto survivorship and look-ahead studies (Zhang & Watts; Kuehn & Adnan; Glasserman & Lin).

## For the desk
Keep a running count of every rule set tested (about 25 so far, see results.md). Quote it next to any result, and apply the deflated Sharpe ratio or a t ≈ 3 bar before promoting anything.
