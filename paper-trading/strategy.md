# Strategy: trend-following tech, long only

This file is the strategy Claude follows. Edit it to change how Claude trades.
The hard limits (position size, cash floor, loss limits, watchlist) are enforced
in code by `papertrader/risk.py`, so changing this file can never loosen them.

## What we are trying to do

Hold quality large-cap tech names while they are in an uptrend, sit in cash when
they are not, and trade rarely. The benchmark is simply holding QQQ. We want
similar or better returns with smaller drawdowns, not more trades.

## Universe and instruments

- Only symbols in the watchlist you are given.
- Stocks and ETFs only. Long only: no shorting, no options, no leverage.
- Orders are market orders for the regular session.

## When to buy

A symbol is a buy candidate only when all of these are true:

1. `above_sma50` is true (price is above its 50-day average).
2. `sma20_above_sma50` is true (the short trend is above the long trend).
3. `return_63d` is positive (up over roughly the last three months).
4. `enough_history` is true.

Among candidates, prefer stronger 63-day returns with lower volatility. Do not
chase a name that rose more than 15% in the last 5 days; wait for it to settle.

## How much to buy

- Target 5% to 8% of equity per stock. Go toward 5% when `vol_20d_annualized`
  is above 0.45 (a jumpy stock), toward 8% when it is below 0.30.
- SPY and QQQ may be held up to the per-position cap as a "default" holding when
  few single names qualify.
- Build positions in steps: if a position is below target, add at most the gap.
- Keep at least 20% of equity in cash.

## When to sell

- Sell the whole position when price closes below the 50-day average
  (`above_sma50` is false) and `sma20_above_sma50` is false.
- Trim back to target when a position has grown above 10% of equity.
- Do not sell just because a position is down a little while the trend holds.

## Behavior

- Doing nothing is a fine answer. Most days should have zero or one trade.
- Do not buy and sell the same symbol on the same day. Look at `recent_orders`
  to avoid undoing yesterday's trade without a clear reason.
- If data for a symbol looks missing or strange, skip that symbol.
- You cannot see news, earnings dates or fundamentals here. Do not invent them.
  Base every decision on the numbers provided.
- Give a short, specific reason for every trade, naming the numbers that drove it.
