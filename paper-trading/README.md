# Paper trading: a Claude strategy on Alpaca's fake-money account

This folder is a small bot that runs a written strategy (`strategy.md`) on an
Alpaca **paper** account, so you can watch how a Claude-driven strategy behaves
before any real money is involved.

Each run does five things:

1. Reads your paper account: equity, cash, positions, open and recent orders.
2. Pulls daily prices for the watchlist and computes trend numbers in code
   (50- and 20-day averages, 5/21/63-day returns, volatility).
3. Sends all of that plus `strategy.md` to Claude (`claude-opus-5-5`), which
   answers with proposed trades in a fixed JSON shape.
4. Runs every proposal through hard limits in code (`papertrader/risk.py`).
   Claude can propose anything; only what passes the limits can be sent.
5. Logs everything. In a dry run (the default) nothing is sent. With `--trade`,
   the approved orders go to the paper account as market orders.

## Paper only, on purpose

There is no live-money mode and no setting that turns one on.

- The Alpaca client is always created with `paper=True`, and the code checks
  that it points at `https://paper-api.alpaca.markets` when it starts and again
  right before every order.
- If your environment has an Alpaca URL variable (like `APCA_API_BASE_URL`)
  pointing anywhere else, or `ALPACA_PAPER=false`, the bot refuses to start.
- Live Alpaca key ids start with `AK`; paper ones start with `PK`. An `AK` key
  is refused.
- A test (`tests/test_bot.py`) fails if the live endpoint ever appears in the code.

## The limits (enforced by code, not by Claude)

Defaults are in `papertrader/config.py`. Override them in `.env`.

| Limit | Default | What happens |
|---|---|---|
| Watchlist | 12 large-cap tech names plus SPY and QQQ | Anything else is rejected |
| Per-position cap | 10% of equity | Buys are shrunk to fit, counting what you already hold |
| Total invested cap | 80% of equity | Keeps at least 20% cash |
| Single buy | $5,000 | Bigger buys are shrunk |
| Orders per run | 5 | Extra proposals are rejected |
| Cash only | always | Buys never use margin |
| No shorting | always | Sells are capped at shares you hold |
| Daily loss limit | 3% | If equity is down 3% since yesterday's close, no buys that day (sells still allowed) |
| Drawdown halt | 15% | If equity falls 15% below where the bot started, it stops trading until you run `--reset-halt` |
| Market hours | always | With `--trade`, nothing is sent while the market is closed |

If Claude errors, refuses, or returns something unreadable, that run makes no
trades. Any odd number (missing price, negative amount) rejects the trade.

## Setup (about 15 minutes)

### 1. Make an Alpaca paper account and keys

1. Sign up at alpaca.markets. A paper account comes with it, funded with fake
   money (usually $100,000), and needs no bank link or deposit.
2. In the dashboard, switch to the **Paper** account (top-left account menu).
3. On the paper dashboard home page, find the **API Keys** panel and generate a
   key. Copy the key id (starts with `PK`) and the secret. The secret is shown
   once.

Use the paper keys only. Do not generate live keys for this.

### 2. Get an Anthropic API key

At console.anthropic.com, create an API key under API Keys. The API is billed
per use and is separate from a Claude.ai subscription.

### 3. Install

You need Python 3.10 or newer.

```bash
cd options-claude-agents/paper-trading
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Add your keys

```bash
cp .env.example .env
```

Open `.env` and paste in your Alpaca paper key id and secret and your Anthropic
key. `.env` is gitignored, so it never gets committed. Don't paste keys anywhere
else (not in code, not in chat).

### 5. Check everything works without keys

```bash
python -m pytest -q        # offline tests
python run.py --mock       # fake account, scripted decision, no network
```

## Running it

```bash
python run.py              # dry run: real paper account, real Claude call, sends nothing
python run.py --trade      # sends the approved orders to the paper account
```

Start with a few dry runs and read what Claude proposes. When it looks sane,
add `--trade`. Run it during market hours (9:30 a.m. to 4 p.m. Eastern); with
`--trade` it will not send orders when the market is closed.

Each run makes one Claude call. Expect very roughly 5 to 25 cents per run at
`effort=high`; check the token counts in the log to see the real figure, and
set `CLAUDE_EFFORT=medium` in `.env` to make it cheaper.

## Running it on a schedule (your laptop)

Once a day, about 30 minutes after the open, is enough for this strategy. On a
Mac or Linux, open your crontab:

```bash
crontab -e
```

and add one line (change the path to where the repo lives on your laptop):

```
0 10 * * 1-5 cd $HOME/options-claude-agents/paper-trading && .venv/bin/python run.py --trade >> logs/cron.log 2>&1
```

That runs at 10:00 a.m. Monday to Friday **in your laptop's time zone**. In
Indiana (Eastern) that is 30 minutes after the open. If your laptop is on
Pacific time, use `0 7 * * 1-5` instead. The laptop has to be awake at that
time; if it's asleep, that day's run is skipped, which is harmless. Market
holidays are handled too: the run sees the market is closed and sends nothing.

Mac note: macOS blocks cron from reading folders like Desktop, Documents and
Downloads. If the repo lives in one of those, either move it (for example to
`~/code/`) or give cron Full Disk Access: System Settings > Privacy & Security >
Full Disk Access, click +, press Cmd+Shift+G, type `/usr/sbin/cron`, and add it.
After the first scheduled weekday, check that `logs/cron.log` exists and that
`python report.py` shows the run. If neither appears, cron was blocked.

To stop the schedule, run `crontab -e` again and delete the line.

## Reading the results

- `logs/latest.md`: the last run in plain English (Claude's view, orders sent,
  anything the limits rejected and why).
- `logs/runs.jsonl`: every run, one JSON object per line. It holds the account
  snapshot, every computed number Claude saw, Claude's full answer, token usage,
  what was approved or rejected, and Alpaca's response to each order.
- `python report.py`: equity over time, change since the bot started, and every
  order sent.
- The Alpaca paper dashboard shows fills, positions and P&L charts.

Compare against simply holding QQQ over the same weeks. If the bot doesn't beat
that on returns or on drawdown, the strategy is not adding anything yet.

## Changing the strategy

Edit `strategy.md` in plain English. The hard limits stay in force whatever
the strategy says. To change a limit, set it in `.env` (see `.env.example`).

## If it halts

When the drawdown limit trips, every later run logs "bot is halted" and trades
nothing. Look at what happened first. To resume:

```bash
python run.py --reset-halt
```

That clears the halt and uses today's equity as the new starting point.

## What this does not do (yet)

- No options. Your covered-call and LEAP framework in this repo needs option
  chains and Greeks; Alpaca's paper account supports options, so that could be
  a next version once the stock version has run for a while.
- No news, earnings dates or fundamentals. Claude sees only prices and your
  account, and the strategy tells it not to invent the rest.
- Prices: daily history from Alpaca's free data (complete through 15 minutes
  ago) plus the latest trade from the IEX exchange feed, which is close to but
  not exactly the consolidated price.
- Paper fills are simulated and can be kinder than real ones (no slippage
  from your own order size, no partial fills in thin markets).

## Files

```
run.py                 entry point (dry run, --trade, --mock, --reset-halt)
report.py              summary of the log
strategy.md            the strategy Claude follows (edit this)
papertrader/config.py  limits and settings
papertrader/safety.py  paper-only guards
papertrader/broker.py  Alpaca reads and order submission (plus a mock)
papertrader/features.py trend numbers computed in code
papertrader/decide.py  the Claude call and the answer format
papertrader/risk.py    the hard limits
papertrader/runner.py  one full run
papertrader/journal.py the log
tests/test_bot.py      offline tests
```
