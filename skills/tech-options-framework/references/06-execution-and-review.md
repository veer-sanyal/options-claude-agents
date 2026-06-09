<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Execution and review

**Section 6.** Practical execution is where many theoretical edges disappear. The first requirement is liquidity. OIC materials caution that wide bid/ask spreads often reflect uncertainty in hedging the underlying, and market participants frequently overestimate the usefulness of raw volume or open interest alone as a proxy for true liquidity. Cboe’s retail education materials similarly define liquidity primarily through the ability to enter and exit near the bid/ask midpoint. That means a process-driven trader should judge the chain using **spread width, displayed size, open interest, and the stock’s own liquidity**, not one metric in isolation. 

The next execution rule is simple: use **limit orders**, not market orders. The  explains that market orders can be filled at worse prices in fast markets, while limit orders cap the price you pay or set the minimum you accept. That matters even more in options, where spreads can widen sharply in volatile conditions; Schwab also notes that low liquidity and irregular order flow tend to widen option bid/ask spreads. 

A conservative liquidity checklist for single-stock tech covered calls is reasonable even if not academically standardized:

| Execution item | Conservative default |
|---|---|
| Stock liquidity | Trade only names with excellent share liquidity |
| Option spreads | Prefer chains where exiting near midpoint is realistic |
| Open interest | You should see meaningful depth at intended short strikes and LEAP strikes |
| Time of day | Prefer normal market hours; avoid rushing fills into open or close unless liquidity is clearly present |
| Event windows | Avoid new trades into earnings, peer earnings clusters, product launches, or ex-dividend assignment traps |
| Order type | Start at mid, improve patiently, and widen only if the trade still has edge |
| Roll discipline | Roll for a reason: better strike, more time, or cleaner event risk profile |

Two example templates are below. The numbers are deliberately **process templates**, not live recommendations.

| Template | When to use | Example structure | Management default |
|---|---|---|---|
| Standard tech covered call | High-quality stock, normal IV, no event in next 2 weeks | Long 100 shares + sell 1 call 30-45 DTE at 0.20-0.30 delta | Take profits on the short call early if most premium is earned; roll only if still bullish and assignment is undesirable for a good reason |
| PMCC / long call diagonal | Want bullish exposure with lower capital; chain has liquid LEAPS | Buy deep-ITM LEAP call 365-540 DTE, sell 30-45 DTE OTM call above short-term upside target | Keep short strike above long strike; exit if long-call delta deteriorates materially or if IV and thesis both break |
| Partial overwrite growth sleeve | Strong trend, expensive premium not rich enough to justify full cap | Own stock or LEAP and cover only 25%-50% of exposure with low-delta calls | Err on the side of under-covering rather than over-capping |

For assignments and dividends, best practice is straightforward. OIC notes that assignment risk rises as a short option becomes deeper in the money and as expiration approaches, and increases just before the ex-dividend date for short calls. OIC also notes that early exercise is generally not optimal except around ex-dividend, where assignment can cost the covered-call writer the dividend. So the correct discipline is to inspect any in-the-money short call before ex-dividend and decide explicitly whether you prefer to keep the stock, lose the dividend, or preemptively close or roll the call. 

Tax treatment deserves caution, not bravado. For U.S. taxpayers, the  discusses “qualified covered call” rules, deep-in-the-money disqualifications, and the fact that stock holding periods can be affected while you are the writer of the option. Publication 550 also shows that option-writer outcomes can differ depending on whether the option expires, is bought back, or is exercised. In practice, that means taxes can be a major reason live results underperform backtests, especially in high-turnover call-writing. 

For analysis tools, the most useful stack is boring and repeatable: **charting + options risk graph + journal + event calendar**. On the broker side, ’s thinkorswim Analyze tab can model price, time, and IV impacts on positions;  offers Probability Lab and Option Strategy Lab for forecast-based scenario analysis;  is useful for visual payoff analysis; and  offers scanners and automation workflows that can help enforce entry and exit rules if used carefully. None of these tools create edge by themselves; they mainly reduce execution sloppiness and behavioral drift. 

The review loop should be rigid. Every closed trade should answer five questions: Was the underlier still one I wanted to own? Did I sell the right amount of upside for the regime? Was IV actually rich enough after costs? Did my roll improve expectancy or just delay pain? Did assignment help or hurt after taxes? That journal is where behavioral edge becomes measurable.
