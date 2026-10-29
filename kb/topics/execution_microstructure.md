# Execution, costs and microstructure

- **Optimal execution trade-off.** Selling fast costs price impact, and selling slowly costs exposure to price moves. Split large orders accordingly. — Almgren & Chriss, "Optimal Execution of Portfolio Transactions," *Journal of Risk*, 2000; see also Baldacci & Benveniste, 2020. https://arxiv.org/abs/2006.11426
- **Price impact is concave and decays.** Impact grows roughly with the square root of size and fades over time. — Bouchaud, "Price Impact," 2009; Tóth, Eisler & Bouchaud, 2017.
- **Adverse selection.** Market makers widen spreads because some traders know more (Glosten-Milgrom). Informed traders hide their trades over time (Kyle). If you're the uninformed side, expect worse fills. — Kyle, *Econometrica*, 1985; Glosten & Milgrom, *Journal of Financial Economics*, 1985.
- **Order-flow toxicity (VPIN).** One-sided volume measured in volume buckets warns of toxic flow and liquidity stress. — Easley, López de Prado & O'Hara, *Review of Financial Studies*, 2012. https://www.stern.nyu.edu/sites/default/files/assets/documents/con_035928.pdf
- **Trading mechanics.** Order types, spreads and the costs of trading, in course form. — Joel Hasbrouck, *Securities Trading: Principles and Procedures* (NYU Stern course materials). https://pages.stern.nyu.edu/~jhasbrou/STPP/drafts/STPPms14cQ.pdf

## For the desk
Our futures backtests charge commission plus 1 tick of slippage on every fill, including targets, and fill gaps at the open. Keep costs at least that conservative in any new test.
