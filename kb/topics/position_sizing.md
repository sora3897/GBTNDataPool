# Position sizing

- **Fixed-fraction risk (the 2% rule).** Risk at most 2% of equity per trade, sized from the stop distance. Pause for the month after a 6% drawdown. — Elder, *Trading for a Living*, 1993; *Come Into My Trading Room*, 2002.
- **Kelly's growth-optimal bet.** For a bet that pays b to 1 with win probability p, the growth-maximising fraction is (bp − q) / b. Use the edge after costs, never before. — J. L. Kelly Jr., "A New Interpretation of Information Rate," *Bell System Technical Journal*, 1956. https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf
- **Overbetting hurts more than underbetting.** If the true edge is half the estimate, full Kelly gives roughly zero growth. Fractional Kelly (half or less) gives up a little growth for much less risk. — Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market," 2006. https://web.williams.edu/Mathematics/sjmiller/public_html/341Fa09/handouts/Thorpe_KellyCriterion2007.pdf
- **Risk-constrained Kelly.** Add a drawdown limit, such as "probability of losing 30% stays under 10%", as a constraint, and solve for the largest fraction that meets it. — Busseti, Ryu & Boyd, "Risk-Constrained Kelly Gambling," 2016. https://arxiv.org/abs/1603.06183

## For the desk
Size with the 2% rule (we use 1%). Treat Kelly as a ceiling, not a target, because our edges come from selected backtests.
