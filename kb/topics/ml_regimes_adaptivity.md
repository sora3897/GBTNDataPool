# Machine learning, validation, regimes and adaptivity

## Machine learning pitfalls
- **Regularise hard.** With many predictors, unregularised models overfit to negative out-of-sample results. Shrinkage and shallow models do better. — Gu, Kelly & Xiu, "Empirical Asset Pricing via Machine Learning," *Review of Financial Studies*, 2020. https://www.nber.org/papers/w25398
- **Purge and embargo cross-validation.** Overlapping labels leak information across folds. Remove overlaps and add a gap after each test fold. Also covers meta-labelling and fractional differencing. — Marcos López de Prado, "The 7 Reasons Most Machine Learning Funds Fail," 2017, and *Advances in Financial Machine Learning*, Wiley, 2018.
- **Walk-forward testing** is closest to live trading, but it tests one path. Add randomised resampling to check whether rankings are stable. — Palomar, "Backtesting Portfolios," HKUST slides, 2020. https://palomar.home.ece.ust.hk/MAFS5310_lectures/slides_backtesting.pdf

## Regimes and drift
- **Bayesian online changepoint detection** tracks the time since the last regime change as data arrives. — Adams & MacKay, 2007. https://arxiv.org/abs/0710.3742
- **Use a robust version,** so a single outlier isn't read as a new regime. — Altamirano, Briol & Knoblauch, 2023. https://arxiv.org/abs/2302.04759
- **Hidden Markov models** find persistent regimes in large crypto assets. — Koki, Leonardos & Piliouras, 2020. https://arxiv.org/abs/2011.03741
- **Concept drift** can be sudden or gradual. Detect it and retrain or switch accordingly. — Lu et al., "Learning under Concept Drift: A Review," 2020. https://arxiv.org/abs/2004.05785
- **Test-then-train evaluation** scores each decision before it updates the model, which avoids look-ahead. — Montiel et al., "River," 2020. https://arxiv.org/abs/2012.04740

## Choosing among strategies over time
- **Bandits.** Picking whichever variant has the best average so far is the greedy policy, and it under-explores. Upper confidence bounds and Thompson sampling balance trying and using. — Lattimore & Szepesvári, *Bandit Algorithms*, Cambridge University Press, 2020 (free draft: https://tor-lattimore.com/downloads/book/book.pdf); Russo et al., "A Tutorial on Thompson Sampling," 2018 (https://arxiv.org/abs/1707.02038); Li et al., LinUCB, 2010 (https://arxiv.org/abs/1003.0146).

## Prediction intervals
- **Adaptive conformal inference** keeps prediction intervals calibrated when the market shifts. — Gibbs & Candès, 2021. https://arxiv.org/abs/2106.00170
- **Calibrated isn't the same as useful.** Judge intervals on width as well as coverage. — Aich, Aich & Jain, 2025. https://arxiv.org/abs/2507.05470
