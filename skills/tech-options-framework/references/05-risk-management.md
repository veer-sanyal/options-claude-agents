<!-- GENERATED FILE — do not edit by hand.
     Source: deep-research-report.md  ·  Regenerate: python options-agents/scripts/build_skill.py -->

## Risk management

**Section 5.** If you want a repeatable edge, you need to manage the position as a **Greek package**, not as a premium stream. The core relationships are straightforward. A covered call is **long delta, short upside convexity, long some theta via the short call, and short vega**. A LEAP call is **long delta, long vega, and long theta decay**, so a PMCC partially offsets the LEAP’s theta by selling the short call, but it also creates a delicate balance: if IV falls and the stock stalls, the long LEAP can bleed faster than many traders expect. The OIC’s Greeks education is clear that delta, gamma, theta, and vega are the essential dashboard variables for any options position. citeturn18search2turn18search3turn18search12

| Risk area | Standard covered call | PMCC / LEAP diagonal | Conservative house rule |
|---|---|---|---|
| Delta risk | Stock drawdown dominates | Delta lower than stock and can fall quickly if trend breaks | Reduce size if long-leg delta falls below thesis threshold |
| Gamma risk | Largest near expiry on short call | Same, with extra complexity from long/short maturities | Prefer 30-45 DTE; avoid weeklies as default |
| Theta | Positive from short call | Net can be favorable, but long LEAP still decays | Roll or take profits before gamma dominates |
| Vega | Mildly short via the call | Mixed, often net long-ish on the LEAP and short on the front call | Avoid buying LEAPs before obvious vol crush unless intentional |
| Assignment risk | Real on any short equity call | Real, and handling may involve exercising or closing the long leg | Never sell calls on stock you are unwilling to lose |
| Gap risk | High around earnings/news | High plus more complex option repricing | No new short calls inside event windows |

At portfolio level, the single most important control is **small single-name sizing**. A good default for concentrated tech trading is something like: cap any one standard covered call at a modest share of portfolio equity, size PMCC net debit even smaller than stock-based covered calls, and cut size again for semiconductors, hardware, or names with unusually violent earnings gaps. The exact percentage is personal, but the logic is not: single-stock tech options are much closer to **discrete-event risk** than index overwriting.

A second essential control is to define **portfolio exposure limits**, not just trade limits. For example, you can cap total short-call notional, total exposure to one tech subindustry, total positions with earnings inside the next month, and total net long vega from LEAPS. This is how a portfolio avoids becoming “secretly the same trade” in cloud, cybersecurity, or AI infrastructure names.

The quantitative scorecard should be just as explicit. At minimum, track:

\[
\text{Expected value per trade} = P(\text{win}) \times \text{avg win} - P(\text{loss}) \times \text{avg loss} - \text{costs}
\]

\[
\text{Premium capture} = \frac{\text{credit kept}}{\text{initial short-call credit}}
\]

\[
\text{Realized overwrite drag} = \text{stock-only return} - \text{covered-call return}
\]

\[
\text{Sharpe} = \frac{\text{annualized return} - r_f}{\text{annualized volatility}}
\]

\[
\text{Sortino} = \frac{\text{annualized return} - r_f}{\text{downside deviation}}
\]

The edge metric that matters most for option selling is not win rate alone. It is **whether your realized implied-minus-realized volatility spread, after costs and taxes, is actually positive**. A high win rate with repeated capped upside can still underperform simple ownership badly.

The major stop or adjustment triggers should also be predefined. Examples that hold up well in practice are: close or roll the short call after capturing a meaningful share of premium, manage before the final high-gamma phase of expiration, cut or fully exit the structure if the fundamental thesis is broken, and do not keep rolling simply to avoid assignment. The tastylive “50% winner” and “manage before 21 DTE” framework is useful as a mechanical template, but it should be treated as a **starting point**, not as universal truth. citeturn27search0turn27search1turn27search4turn27search8
