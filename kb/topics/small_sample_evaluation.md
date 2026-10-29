# Small samples: how much a short record proves

- **Probabilistic Sharpe ratio and minimum track record length.** These give the probability that the true Sharpe ratio is above a benchmark, given the record's length, skew and fat tails, and how long a record you need before believing it. — Bailey & López de Prado, "The Sharpe Ratio Efficient Frontier," *Journal of Risk*, 2012. https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf
- **Compare Sharpe ratios robustly.** Use a block bootstrap, not a formula that assumes normal, independent returns. Trade results are fat-tailed and clustered. — Ledoit & Wolf, "Robust Performance Hypothesis Testing with the Sharpe Ratio," *Journal of Empirical Finance*, 2008. https://www.econ.uzh.ch/apps/workingpapers/wp/iewwp320.pdf
- **Continuous monitoring inflates false positives.** Checking a test repeatedly and stopping at the first significant result is misleading. Always-valid p-values (mSPRT) fix that. — Johari, Pekelis & Walsh, "Always Valid Inference," 2019. https://arxiv.org/abs/1512.04922
- **Anytime-valid confidence sequences** for bounded quantities such as win rate let you look as often as you like. — Waudby-Smith & Ramdas, "Estimating Means of Bounded Random Variables by Betting," *JRSS-B*, 2024.
- **E-values and test martingales.** A strategy's paper P&L is itself a betting wealth process, which fits safe, anytime-valid testing. — Ramdas, Grünwald, Vovk & Shafer, "Game-Theoretic Statistics and Safe Anytime-Valid Inference," 2023. https://arxiv.org/abs/2210.01948
- **Bayesian A/B tests need FDR control too.** A fixed 95% posterior threshold across many variants doesn't control false discoveries. Choose the threshold and the sample size together. — Hagar & Stevens, 2025. https://arxiv.org/abs/2312.10814
- **A case study in fragility.** A 15-day paper-trading record looked strong but depended on a handful of trades. Always show results with the top few trades removed. — Kamat, 2026. https://arxiv.org/abs/2606.08232

## For the desk
Report the trade count with every result. Show a "top 3 removed" line. Don't promote a rule on a record shorter than its minimum track record length.
