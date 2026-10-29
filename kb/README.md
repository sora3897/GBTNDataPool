# Knowledge base (kb/)

A short, original knowledge base that ships with every desk. It condenses about a hundred paper and book notes the original desk read, plus our own backtest results, into plain-English summaries with citations. Nothing here is copied from the sources. There are no PDFs, excerpts, or images. Read the original work through the links when you need detail.

Paper or demo only. Nothing here is financial advice.

## How desks use it

- At setup, the coordinator loads `kb/` with the rest of the repo and tells every teammate where it is.
- **Before proposing any strategy or change**, Scan, Vet, Size, Risk and Load read `kb/rules.md` (the rules and the guards against fooling ourselves) and `kb/results.md` (what we already tested and how it went). A proposal says which rule it builds on and whether it repeats something already tested.
- Book uses `topics/backtest_overfitting.md` and `topics/small_sample_evaluation.md` when it checks results.
- Futures and technical analysis come first. Meme coins get one short file.

## Index

| File | What's in it |
|---|---|
| [rules.md](rules.md) | Trading rules we use, each with its source: Elder triple screen, the 2% and 6% rules, Wyckoff's rules, Lo-Mamaysky-Wang testing, overfitting and small-sample guards |
| [results.md](results.md) | Our backtest results, including E10 and E21 opening-range entries, and their caveats |
| [topics/technical_analysis.md](topics/technical_analysis.md) | Trend, momentum, chart patterns, and how to make them testable |
| [topics/backtest_overfitting.md](topics/backtest_overfitting.md) | Multiple testing, deflated Sharpe, probability of backtest overfitting |
| [topics/small_sample_evaluation.md](topics/small_sample_evaluation.md) | How much a short track record proves, and how to monitor without fooling yourself |
| [topics/position_sizing.md](topics/position_sizing.md) | Fixed-fraction risk, Kelly and why to bet less than it |
| [topics/exits.md](topics/exits.md) | Stops, targets, time stops and trailing stops |
| [topics/execution_microstructure.md](topics/execution_microstructure.md) | Costs, slippage, price impact, adverse selection |
| [topics/ml_regimes_adaptivity.md](topics/ml_regimes_adaptivity.md) | Machine learning pitfalls, validation, regimes, drift, bandits, prediction intervals |
| [topics/memecoins.md](topics/memecoins.md) | Short section: meme-coin risks and costs |

## Adding to it

Write your own summary, keep it short, and cite author, title, year, and a public link if there is one. Never add PDFs, long quotes, images, secrets, or account data. `tests/test_kb.py` fails the build if a PDF or anything that looks like a secret lands in `kb/`.
