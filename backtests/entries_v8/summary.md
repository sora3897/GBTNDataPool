# entries_v8 (E21-E24 on E10), offline backtest, S4 risk, fixed $50K

Windows: r200a/r200b = recent-200 trades split 60/40; IS/OOS = full history 60/40. Pctile = vs 50 random-entry seeds.

| E | n | r200a $ | r200b $ | IS $ | OOS $ | OOS PF | maxDD% (worst win) | per-sym sign (OOS ES/GC/NQ) | rand pctile (r200a/r200b/IS/OOS) | all 4 + |
|---|---|---|---|---|---|---|---|---|---|---|
| E10 | 816 | 6235 | 4371 | 23021 | 21090 | 1.89 | -4.57 | +/+/+ | 100.0/98.0/100.0/100.0 | yes |
| E21 | 646 | 11671 | 4621 | 20282 | 20099 | 2.06 | -4.29 | +/+/+ | 100.0/100.0/100.0/100.0 | yes |
| E22 | 816 | 5337 | 4312 | 26924 | 20171 | 1.85 | -4.09 | +/+/+ | 94.0/100.0/100.0/100.0 | yes |
| E23 | 816 | 6123 | 3131 | 24466 | 19267 | 1.67 | -6.55 | +/+/+ | 100.0/94.0/100.0/100.0 | yes |
| E24 | 819 | 7520 | -1831 | 3921 | 6808 | 1.37 | -8.57 | +/+/+ | 100.0/30.0/94.0/98.0 | no |

Notes: E23 uses +0.75R breakeven (E10 already +0.5R). E24 uses 09:00+10:00 2-bar range (E10 already flat at session close; 30-min range impossible on 1h data).
Caveat: ~2.4y of yfinance continuous 1h data, Panama-adjusted; variants are tweaks of an already-selected winner (multiple-testing bias).

OOS maxDD%: E10 -2.66, E21 -2.78, E22 -2.68, E23 -3.27, E24 -4.31. Recent-200 halves are first 60% / last 40% of the last 200 candidates (E21/E24 windows start earlier: fewer trades).
