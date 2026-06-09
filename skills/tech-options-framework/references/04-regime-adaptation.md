<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Regime adaptation

**Section 4.** Covered calls and LEAP structures are not one strategy. They are a menu that should change with trend, valuation, and volatility regime. The evidence says that selling upside too aggressively works best when markets are flat to moderately bullish and implied volatility is adequately rich; it works worst in strong melt-ups. The technology sector adds another layer because concentration and AI-related leadership have been unusually high: S&P research showed the 10 largest S&P 500 names were near 40% of the index by mid-2025, and much of that concentration sat in growth and tech leaders. In a concentrated market, full overwriting of leaders is more likely to cap the very stocks you most need to carry portfolio performance. 

| Market regime | Best default action | What to avoid |
|---|---|---|
| Strong uptrend, low-to-normal IV | Own stock or LEAP first; overwrite only 25%-50% of position notional with 0.10-0.20 delta calls | Full overwrite, ATM calls, weeklies |
| Healthy uptrend, normal IV | Standard 0.20-0.30 delta covered calls or PMCCs | Selling strikes too close to spot |
| Sideways/choppy, normal-to-high IV | This is the best covered-call environment; 0.25-0.35 delta, 30-45 DTE | Underwriting too little premium for the regime |
| Downtrend, high IV | Reduce long exposure first; only defensive overwrite on holdings you still want; consider collars or index hedges | Selling calls just to “earn income” on broken longs |
| Post-earnings IV crush | Good time to evaluate fresh LEAP entries or non-event overwrites once uncertainty resets | Buying short-dated premium before the crush |
| Macro shock / vol expansion | Smaller size, wider strikes, index hedges, more cash | Assuming high IV automatically means high edge |
| Semis in capex or inventory boom | Prefer partial overwrite; let winners run more | Repeatedly capping high-momentum leaders |
| Software multiple-compression regime | Favor highest-quality FCF names and wider strikes | Covered calls on expensive but deteriorating SaaS names |

A practical rule is to tie overwrite aggressiveness to both **trend strength** and **volatility richness**. If the trend is strong and IV is low, the short call is usually the weakest leg in the trade. If the trend is flat and IV is healthy, the short call can be the best leg. If the trend is down and IV is high, the problem is often the long stock, not the absence of premium. That distinction keeps you from using covered calls as emotional anesthesia for a broken core position. 

This is also where a “skip rule” creates real behavioral edge. If a stock is in a genuine momentum breakout and your thesis horizon is longer than one month, skipping a call sale can be better than forcing a low-quality overwrite. Research from AQR is helpful here: it argues that investors should explicitly choose how much equity and volatility risk premium they want rather than letting a naïve call-overwrite habit impose uncompensated timing risk.
