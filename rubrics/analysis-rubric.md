# Portfolio Analysis Rubric

This rubric grades a portfolio analysis / action brief produced by the Options
Portfolio Coordinator. It is sent with a `user.define_outcome` event so the
managed-agents grader (independent context) scores each iteration and the agent
revises until satisfied. Criteria are derived from `deep-research-report.md`
§5 (risk management), §6 (execution & review), and §7 (failure modes) — the
sections that define what a *correct* analysis looks like.

Each criterion is independently gradeable. A brief is **satisfied** only when all
hard-gate criteria pass; quality criteria raise or lower the score but do not by
themselves fail the brief.

## Hard gates (any failure → needs_revision)

1. **Event gate respected.** No recommendation opens or holds a *new* short call
   within ~15 calendar days of the name's own earnings or a curated peer's
   earnings, unless the brief explicitly labels it an event-volatility sale and
   justifies it. (§7 event blindness, §1 workflow.)
2. **Strike discipline.** Every proposed short call is OTM and in the documented
   delta band for its regime (0.10-0.20 strong uptrend / 0.20-0.30 core /
   0.25-0.35 sideways-high-IV). No ATM full overwrites on secular winners. (§2, §7.)
3. **Expiration discipline.** Proposed expirations are 30-45 DTE unless a weekly is
   explicitly justified on a liquid megacap with a specific event view. (§2, §5.)
4. **Regime consistency.** Overwrite aggressiveness matches the classified regime
   for each name (partial/low-delta in strong uptrends; standard in sideways;
   no new income calls on downtrending broken theses). (§4.)
5. **Sizing & exposure.** No single-name or subindustry concentration breach;
   semis/hardware sized smaller than software/cloud; PMCC net debit sized below
   stock-based covered calls. Portfolio-level caps (short-call notional, names with
   earnings next month, net long LEAP vega) are checked, not just per-trade. (§5.)
6. **Assignment framed correctly.** Where assignment is likely, the brief treats it
   as a valid planned exit and inspects ITM short calls before ex-dividend — it does
   not recommend rolling solely to avoid assignment. (§5, §6.)

## Quality criteria (raise/lower score)

7. **Greek-package reasoning.** Each position is assessed as a Greek package
   (delta/gamma/theta/vega), not just as a premium stream; PMCC briefs note long-leg
   delta and extrinsic-value bleed. (§5.)
8. **Edge stated honestly.** Recommendations distinguish premium yield from edge and,
   where relevant, acknowledge the implied-minus-realized-vol / after-cost reality
   rather than treating premium as free. (§5, §7.)
9. **Underlier still wanted.** Each held name is re-checked against the §3 quality
   factors (revenue quality, cash generation, balance sheet, valuation context);
   broken theses are flagged for the long, not overwritten. (§3, §6 review loop.)
10. **Liquidity & execution.** Strikes are judged on spread/open-interest/displayed
    size, not one metric; orders specified as limit-at-mid, not market. (§6.)
11. **Actionable & prioritized.** Output is a ranked hold / roll / close / no-new-call
    list with per-item rationale tied to a specific section, and a clear "why now."
12. **Drift acknowledged.** Where the Pattern Reviewer flagged behavioral drift vs.
    documented strategy, the brief addresses it rather than repeating the pattern. (§7.)

## Grading notes

- Prefer concrete, checkable findings over vibes. "Capped NVDA at 0.45 delta in a
  strong uptrend — violates §2/§4" is gradeable; "looks aggressive" is not.
- The hard gates are also tool-enforced; if a recommendation contradicts a tool
  result (`check_position_triggers`, `size_position`), that is an automatic fail.
- **Tool outputs inlined.** The brief must include the verbatim JSON outputs from
  `classify_regime`, `check_position_triggers`, and `size_position` for every name
  so this grader can verify consistency. The grader cannot see raw custom-tool-result
  events — only the agent's text output is visible.
- Max iterations: start at 4. If still failing hard gates after 4, the brief should
  state which gate it cannot satisfy and why, rather than silently shipping.
