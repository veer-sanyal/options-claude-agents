#!/usr/bin/env python3
"""Summarize the decision log: equity over time and every order sent.

    python report.py          # paper runs
    python report.py --mock   # mock runs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from papertrader.config import PROJECT_DIR  # noqa: E402
from papertrader.journal import read_runs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true")
    args = p.parse_args(argv)
    log_dir = PROJECT_DIR / "logs" / ("mock" if args.mock else "")
    runs = read_runs(log_dir)
    if not runs:
        print(f"No runs logged yet in {log_dir}/runs.jsonl")
        return 0

    start = next((r["start_equity"] for r in runs if r.get("start_equity")), None)
    print(f"{'time (UTC)':<20} {'mode':<12} {'equity':>12} {'vs start':>9} {'orders':>6}  notes")
    for r in runs:
        eq = (r.get("account") or {}).get("equity") or 0.0
        vs = f"{eq / start - 1:+.2%}" if start else ""
        sent = sum(1 for x in (r.get("results") or []) if not str(x.get("status", "")).startswith("error"))
        note = r.get("blocked_reason") or r.get("buys_blocked_reason") or "; ".join(r.get("errors") or [])
        print(f"{r['time'][:19]:<20} {r['mode']:<12} {eq:>12,.2f} {vs:>9} {sent:>6}  {note[:60]}")

    print("\nOrders sent:")
    any_sent = False
    for r in runs:
        for o, res in zip(r.get("approved") or [], r.get("results") or []):
            any_sent = True
            amount = f"${o['notional']:,.2f}" if o.get("notional") else f"{o.get('qty')} sh"
            print(f"  {r['time'][:10]} {o['side'].upper():<4} {o['symbol']:<6} {amount:>12}  "
                  f"{res.get('status')}  {o.get('reason', '')[:70]}")
    if not any_sent:
        print("  none yet")
    print("\nFill prices and current P&L are on the Alpaca paper dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
