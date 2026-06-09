---
name: tech-options-framework
description: >-
  The covered-call and LEAP/PMCC methodology for technology stocks used by this
  desk. Load when screening an underlier, structuring a covered call or PMCC,
  choosing a strike/expiration, adapting to a market regime, sizing a position,
  reviewing a closed trade, or grading an analysis. Encodes the research-backed
  defaults: OTM ~0.20-0.30 delta strikes, 30-45 DTE (not weeklies), regime-gated
  partial overwriting, no new short calls within 15 days of own/peer earnings,
  smaller size in semis/hardware than software/cloud, and "premium yield is not
  edge." Use it to ground every recommendation in the documented framework rather
  than priors.
---

# Tech Options Framework

This skill is the single source of truth for how this desk trades covered calls
and LEAP/PMCC structures on technology names. It is generated from the canonical
research synthesis (`deep-research-report.md`); the section files under
`references/` are verbatim splits of that document — read the one that matches the
task instead of working from memory.

## How to use this skill

Pull the section you need; do not load all seven for every task.

| If the task is… | Read |
|---|---|
| "Should I even trade this / pre-trade gate" | `references/01-workflow.md` (the decision tree) |
| Choosing strike + expiration, covered-call vs PMCC | `references/02-strategy-design.md` |
| Screening / rating an underlier, peer-event spillover | `references/03-underlier-selection.md` |
| Adjusting aggressiveness to trend + IV regime | `references/04-regime-adaptation.md` |
| Greeks, sizing, exposure caps, stop/adjust triggers | `references/05-risk-management.md` |
| Liquidity, order handling, assignment/ex-div, the review loop | `references/06-execution-and-review.md` |
| Failure modes, what the evidence does and does not support | `references/07-evidence-pitfalls.md` |

## Non-negotiable rules (hard gates)

These are the rules that protect capital. They are also enforced deterministically
by tools (`check_position_triggers`, `size_position`, `screen_underlier`) — the
skill states *why*; the tools enforce *that*. Never recommend around them on the
strength of prose alone.

1. **Event gate.** No new short call within ~15 calendar days of the name's own
   earnings, or a curated peer's earnings, unless the trade is explicitly an
   event-volatility sale. (§1 workflow tree, §3 peer spillover, §7 event blindness.)
2. **Strike default.** OTM, ~0.20-0.30 delta — not at-the-money. Premium yield is
   not edge; ATM full overwriting caps secular winners. (§2, §7.)
3. **Expiration default.** 30-45 DTE. Avoid weeklies as a default — more gamma,
   slippage, and event risk. (§2, §5.)
4. **Regime gate.** Strong uptrend → cover only 25-50% of notional with 0.10-0.20
   delta. Sideways/healthy-IV → standard 0.25-0.35 delta. Downtrend → fix the long
   first; do not sell calls as "income" on a broken thesis. (§4.)
5. **Sizing.** Small single-name risk; size PMCC net debit smaller than stock-based
   covered calls; cut size further for semis/hardware and violent-gap names. (§5.)
6. **Assignment is a planned exit, not a failure.** Never sell calls on stock you
   are unwilling to lose; do not roll indefinitely to dodge assignment. (§1, §5, §7.)

## The mindset (one line)

Find quality long exposure first, *then* decide whether an overwrite improves the
total portfolio — not "find premium and sell it." (§1.)

## What this skill is not

It is evidence-based synthesis, strongest at the **index** level (Cboe BXM/BXY/BXMD,
S&P DJI, AQR, Chicago Fed). Single-stock application carries higher event and
dispersion risk, and the variance-risk-premium edge is weaker in recent data. Treat
the framework as risk-adjusted and behavioral edge, not a guaranteed raw-return edge.
After costs, taxes, and overwrite drag, a sloppy process underperforms buy-and-hold.
(§7, and the report's Open questions.)
