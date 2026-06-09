<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Evidence, pitfalls, and portfolio fit

**Section 7.** The evidence in favor of call overwriting is real but nuanced. Classic buy-write studies and modern benchmark factsheets show that covered-call structures have historically lowered volatility and drawdowns and, in some OTM variants, slightly improved Sharpe/Sortino ratios relative to the equity benchmark. But the evidence also says that **full, ATM, always-on overwriting is usually not the best version** if your objective is strong long-run total return. That is why the best synthesis for tech investors is **selective, OTM, regime-aware overwriting** rather than mechanical income harvesting. 

The strongest counterargument is important and should be taken seriously. The AQR paper argues that simple covered calls package a valuable short-volatility exposure together with an uncompensated reversal exposure, and the Chicago Fed’s 2025 work argues that the variance-risk-premium edge in traded options appears weaker in more recent decades than in older data. Put differently: **option selling is not a free lunch, and the lunch may be less free than it used to be**. After commissions, slippage, taxes, and single-stock event risk, a sloppy covered-call process can easily underperform both buy-and-hold and a broad-market ETF. 

The most common failure modes are predictable:

| Failure mode | Why it happens | Prevention |
|---|---|---|
| Chasing premium | Trader confuses rich premium with true expectancy | Start from the business, then the regime, then the chain |
| Selling too close to spot | ATM call maximizes premium but also maximizes regret and upside truncation | Default to OTM / ~30 delta |
| Overwriting strong winners | Trader wants monthly consistency more than long-run compounding | Partial overwrite or skip rule in strong uptrends |
| Event blindness | Own earnings or peer earnings reprice IV and delta violently | Maintain a full sector event calendar |
| Weekly overtrading | More gamma, more slippage, more emotion | Keep 30-45 DTE as default |
| Refusing assignment | Trader rolls bad positions indefinitely | Treat assignment as a valid planned exit |
| Ignoring taxes | Gross backtest looks good; net result disappoints | Prefer lower-turnover processes and document after-tax outcomes |
| Using PMCC like stock | Trader forgets LEAPs have vega and finite life | Monitor long-leg delta, extrinsic value, and time-to-expiry closely |

Where do these strategies fit in a broader portfolio? The strongest answer is: **as a sleeve, not as your whole identity**. Covered calls make the most sense on the part of a portfolio intended for **cash-flow generation, disciplined exits, and lower volatility**. LEAPs make the most sense where you have **high-conviction bullish views but want limited-dollar risk and better capital efficiency**. A broad-market core may still be superior for pure simplicity and tax efficiency, while a selective overwrite sleeve can add diversification of return path and behavior. 

The practical bottom line is this:

- If your main goal is **maximum long-run total return**, pure stock or broad-market ownership still has the best default case in strong bull markets.   
- If your goal is **competitive equity-like returns with lower drawdowns**, the best historical evidence favors **OTM or roughly 30-delta overwriting**, not ATM full overwrite.   
- If your goal is **capital efficiency**, a LEAP plus shorter-dated call can work well, but only when you understand that you have exchanged stock simplicity for more Greek complexity.   
- If your goal is **repeatable edge in tech**, the best implementation is usually: own only high-quality liquid names, avoid earnings windows, default to 30-45 DTE and 0.20-0.30 delta, use partial overwrites in strong uptrends, size semis smaller than software, and review performance after costs, taxes, and overwrite drag. That last part is the difference between a strategy that looks good on paper and one that survives real trading. 

**Open questions and limitations.** The main limitation is that the most rigorous evidence is on diversified index strategies, not on hand-picked single-stock tech portfolios. The single-stock framework in this report is therefore an evidence-based synthesis rather than a fresh, live backtest of a specific tech basket. Tax outcomes, broker treatment of PMCC assignment, and realized slippage can also vary materially across accounts and platforms.
