<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Strategy design

**Section 2.** The cleanest evidence for strike and expiration design comes from benchmark indexes. As of March 31, 2026, the classic at-the-money BuyWrite benchmark had materially lower volatility and drawdown than the S&P 500, but it also gave up too much upside for many investors. By contrast, the 2% OTM benchmark and the 30-delta benchmark came much closer to the market’s annualized return while still posting lower volatility, smaller drawdowns, and slightly better Sharpe/Sortino ratios. That is the strongest high-confidence case for **defaulting to OTM / ~30-delta overwriting instead of ATM overwriting** when the goal is a realistic edge over buy-and-hold on a risk-adjusted basis. 

| Strategy benchmark | Long-run annualized return | Annualized volatility | Max drawdown | Sharpe | What it implies for real traders |
|---|---:|---:|---:|---:|---|
| S&P 500 Total Return | 10.9%-11.1% | 14.6%-15.2% | -50.9% | 0.54 | Baseline buy-and-hold comparison |
| BXM ATM monthly overwrite | 8.4% | 10.7% | -35.8% | 0.53 | Smoother ride, but too much upside sacrificed |
| BXY 2% OTM monthly overwrite | 10.1% | 12.0% | -40.3% | 0.57 | Better compromise between premium and upside |
| BXMD 30-delta monthly overwrite | 10.4% | 12.9% | -42.7% | 0.59 | Best benchmark evidence for a “default” overwrite style |

*Benchmark data above are from Cboe factsheets as of March 31, 2026. These are theoretical, pre-tax index statistics and may include backtested periods before launch, so they are useful as design evidence, not as a promise of live single-stock results.* 

The most useful strike-selection lesson from the research is not just that OTM is “better,” but **why**. In S&P Dow Jones research, OTM calls collected less premium than ATM calls, but the retained equity growth helped the OTM approach beat the ATM benchmark in both long-term return and cash-flow sustainability. The same study also found that if you force too high a distribution target, you can suffocate equity growth and deplete the portfolio faster. In other words, **premium yield is not the same thing as edge**. 

A powerful but underappreciated point from the same research is that covered-call traders often focus too much on monthly “income” and not enough on the source of return. In one sample from March 2006 to December 2016, the BXM short call finished in the money in about 65% of months, meaning a large fraction of upside was offset by call settlement rather than retained by the equity holder. That is exactly why full, near-the-money overwriting is usually a poor fit for strong secular-growth tech stocks. 

Expiration choice matters too. S&P Dow Jones research found that compared with standard monthly options, **quarterly options can reduce losses from repeated cash settlement of expiring calls**, while **weekly selling can incur more loss**. In single-stock tech names, weeklys also layer on more commission drag, more slippage, and much more gamma/event risk. A sensible default for single-name covered calls is therefore **30-45 DTE**, not weeklys, unless you are trading only the most liquid megacaps and you have a very specific event view. 

The best default tactics, grounded in the research and then translated to single-stock tech, are these:

| Objective | Default setup | Why it tends to work |
|---|---|---|
| Risk-adjusted core overwrite | 30-45 DTE, 0.20-0.30 delta short call | Preserves more upside than ATM while still harvesting time value |
| Strong uptrend participation | 30-45 DTE, 0.10-0.20 delta and only partial coverage | Reduces the chance of repeatedly capping a secular winner |
| Sideways/high-IV environment | 30-45 DTE, 0.25-0.35 delta | Best premium capture when trend is muted |
| Capital-efficient bullish income | Deep-ITM LEAP call plus 30-45 DTE OTM short call | Mimics stock with lower capital, but adds vega/time sensitivity |
| Defensive management in weak tape | Light overwrite only, or no new call sale | Premium is not enough if the long equity thesis has broken |

The common “45 DTE / around 30 delta / manage before expiration” playbook is also consistent with practitioner backtests from established educators such as tastylive, though those findings are not peer-reviewed and are usually based on broad liquid underlyings rather than single tech names. That makes them useful as **execution mechanics**, but weaker than the Cboe index evidence as proof of durable alpha.
