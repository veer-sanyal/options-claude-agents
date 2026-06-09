<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Underlier selection

**Section 3.** For a LEAP or covered-call process focused on technology, stock selection matters more than in generic index overwriting because single-name dispersion and event risk are much higher. The biggest mistake is starting with the options chain instead of the business. Your best underliers are usually firms where you would be comfortable owning the equity through a normal drawdown: durable demand, visible cash generation, manageable leverage, and enough structural liquidity that you can adjust or exit without donating edge to the spread. That is especially important because most of the research evidence for covered calls comes from diversified index exposures, so single-stock selection has to do more of the work. 

Recent industry data strengthen the case for separating software/cloud names from semiconductors and hardware.  forecast worldwide public-cloud end-user spending at about $723 billion in 2025 and worldwide IT spending above $6.3 trillion in 2026, with AI infrastructure and software as major drivers.  reported global semiconductor sales of $791.7 billion in 2025 and projected roughly $1 trillion in 2026, while  described AI adoption as broadening but still uneven, with software business models also shifting from classic seat-based subscriptions toward more consumption-oriented pricing. Those facts matter because they imply very different option behaviors: software names often carry **valuation and monetization risk**, whereas semis tend to carry **cyclical, supply-chain, capex, and inventory risk**. 

| Underlier factor | What to look for | Why it matters more in tech |
|---|---|---|
| Revenue quality | Recurring revenue, backlog, good retention, broad customer base | Software and cloud rerate hard when retention or expansion weakens |
| Cash generation | Positive or improving FCF, not just adjusted EPS | LEAPs magnify thesis errors; cash flow reduces “story stock” risk |
| Balance sheet | Net cash or very manageable leverage | Tech drawdowns can become financing events in weak capital markets |
| Valuation context | Compare to own history and peer group, not only absolute multiples | High-duration tech can collapse on multiple compression even with growth |
| Product and capex cycle | Know whether the next 1-3 quarters are driven by launches, AI capex, memory pricing, or digestion | Especially important in chips and hardware |
| Options liquidity | Tight spreads, plenty of strikes, meaningful open interest across 30-90 DTE and LEAP maturities | You do not have an edge if you cannot adjust efficiently |
| Event calendar | Own earnings, peer earnings, guidance days, product launches, court rulings, export controls | Tech is unusually headline sensitive |
| Technical trend | Favor stable or improving trends for bullish LEAPs | Long-dated optionality punishes buying broken trends too early |

A conservative **house-rule filter** for single-name tech is to require all of the following before a new trade: strong average daily dollar volume in the stock, a visibly tradable options chain at your intended strikes, no earnings within roughly two weeks, and a thesis that survives at least one bad quarter. Those are not universal academic thresholds; they are process defaults designed to keep you out of positions where slippage and gap risk dominate the theoretical edge.

For LEAP-based structures, a practical checklist is even tighter. The long call should typically be **deep enough in the money to behave like stock** but **long enough dated that theta does not dominate the trade prematurely**. The  defines LEAPS as long-dated options that can expire up to about two years and eight months in the future, and both OIC materials and broker education emphasize that long diagonal call structures can function as capital-efficient stock substitutes. In practice, many traders use long calls in the roughly **0.70-0.85 delta range** and then sell shorter-dated calls against them. 

One more tech-specific filter is often missed: **peer-event spillover**. A 2018 academic study found that implied volatility commonly **rises into earnings and drops sharply after**, and that volatility-relevant information also transfers to industry peers, meaning one company’s earnings can change implied volatility in related firms. In tech, where peer groups are tight and narratives move in clusters, that means your short call can be mispriced by **someone else’s earnings date**, not only your own. That is a strong reason to keep a “sector event calendar” for semis, cloud, cybersecurity, and hardware ecosystems.
