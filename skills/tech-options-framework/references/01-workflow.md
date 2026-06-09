<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Workflow

**Section 1.** A winning process should be built as a sequence of gatekeeping decisions. The edge is revealed in four places: **information edge** from better underlier selection, **structural edge** from selling expensive optionality more carefully than you buy it, **behavioral edge** from pre-committed rules that prevent emotional overrides, and **portfolio edge** from position sizing and diversification that reduce the frequency of ruinous outcomes. Research on buy-write benchmarks, volatility risk premia, and option pricing all point in the same direction: the best workflow is not “find premium and sell it,” but “find quality long exposure first, then decide whether an overwrite improves the total portfolio.” 

| Workflow stage | Core question | What creates edge | Primary output | Typical kill switch |
|---|---|---|---|---|
| Idea generation | Why this tech name now? | Starting with industry demand, business quality, and catalysts instead of premium alone | Watchlist candidate | No durable thesis |
| Underlier research | Is this a business you want to own through noise? | Favor quality balance sheets, real cash generation, and durable demand | Green / yellow / red rating | Binary or weak fundamentals |
| Options analysis | Is volatility rich enough and liquidity good enough? | Choose structures only where spreads, open interest, and event calendar cooperate | Candidate structure | Illiquid chain or bad event timing |
| Entry rules | Is this the right strike, DTE, and regime? | OTM / 30-delta bias, earnings avoidance, partial overwrite in uptrends | Executable trade plan | Overwrite too aggressive for regime |
| Position sizing | Can this lose without harming the portfolio? | Small single-name risk, smaller size in semis and event-heavy names | Dollar risk and max loss | Position too large |
| Monitoring | Has delta, IV, or regime changed enough to matter? | Manage early instead of waiting for forced decisions | Roll / hold / close decision | Unplanned thesis drift |
| Exit or assignment | Is assignment acceptable here? | Treat assignment as a valid exit, not a failure | Realized P&L and next action | Refusal to take assignment |
| Post-trade review | Was the edge real or imagined? | Separate process quality from outcome luck | Journal, metrics, playbook updates | No review loop |

The practical decision tree below is the simplest version of a repeatable pre-trade filter:

```text
Start
│
├─ Do I want to own this tech business for 6-18 months?
│  ├─ No → reject the trade
│  └─ Yes
│
├─ Is there earnings, a major product event, or a key peer earnings report inside 15 calendar days?
│  ├─ Yes → do not open a fresh short call unless the trade is explicitly an event-volatility sale
│  └─ No
│
├─ Is the options chain liquid enough?
│  ├─ No → reject
│  └─ Yes
│
├─ Is implied volatility low, normal, or high versus the stock’s own history?
│  ├─ Low → favor stock or LEAP; use light or no overwrite
│  ├─ Normal → standard covered call or PMCC candidate
│  └─ High → wider strike, smaller size, partial overwrite only
│
├─ What is the price regime?
│  ├─ Strong uptrend → cover only part of the position and use lower-delta calls
│  ├─ Sideways/choppy → standard overwrite is most attractive
│  └─ Downtrend → avoid new covered calls as “income trades”; reduce or hedge long exposure first
│
└─ Is assignment an acceptable outcome?
   ├─ No → do not sell the call
   └─ Yes → trade
```

That tree is a synthesis of benchmark research, earnings-volatility evidence, and options education guidance from the  and . The two biggest workflow errors are opening short calls too close to earnings and treating assignment as a mistake rather than a planned exit.
