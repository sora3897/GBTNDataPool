# Exits: stops, targets and time

- **Time stops fit support and resistance trading.** A favourable regime fades, so exit if the trade hasn't worked within a set time. — Henderson, Jacka, Liu & Maeda, 2021/2025. https://arxiv.org/abs/2103.02331
- **Trailing stops as a third trigger.** Combine a take-profit, a stop-loss, and a trailing floor. The best take-profit level depends on volatility. — Leung & Zhang, "Optimal Trading with a Trailing Stop," 2017/2019. https://arxiv.org/abs/1701.03960
- **All-or-nothing exits under simple models.** If expected drift after entry is negative, exit at once. If it's strongly positive relative to risk, hold to the horizon. Partial exits make sense only under other goals. — Majumdar & Bouchaud, 2008. https://arxiv.org/abs/0809.2878
- **Drawdown aversion justifies stops.** A trader who dislikes drawdowns can rationally use a stop even when it lowers expected value. Say which goal you optimise. — Rodosthenous & Zhang, 2020. https://arxiv.org/abs/2006.00282
- **Triple-barrier labelling.** Label historical trades with the same take-profit, stop and time limit that the strategy trades, so tests match execution. — Marcos López de Prado, *Advances in Financial Machine Learning*, Wiley, 2018.

## For the desk
E10 and E21 use a 1R target, a breakeven stop after +0.5R, and a session-close time stop. A 1.5R target (E22) and a later breakeven (E23) did slightly worse out-of-sample (results.md).
