#!/usr/bin/env python3
"""Paper-trading bot entry point.

    python run.py                # dry run: reads your PAPER account, asks Claude, sends nothing
    python run.py --trade        # same, then sends the approved orders to your PAPER account
    python run.py --mock         # no keys needed: fake account and a scripted decision
    python run.py --reset-halt   # clear the drawdown halt and restart the drawdown baseline

There is no live-money mode. See README.md.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from papertrader.config import load_settings  # noqa: E402
from papertrader.safety import LiveTradingRefused, check_environment  # noqa: E402


def load_dotenv_file() -> None:
    env_file = HERE / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        # Values already set in the shell win over the file.
        load_dotenv(env_file, override=False)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Claude paper-trading bot (Alpaca paper only).")
    p.add_argument("--trade", action="store_true",
                   help="send approved orders to the Alpaca PAPER account (default is a dry run)")
    p.add_argument("--mock", action="store_true",
                   help="fake account and scripted decision; no keys, no network")
    p.add_argument("--reset-halt", action="store_true",
                   help="clear the drawdown halt and use current equity as the new baseline")
    args = p.parse_args(argv)

    load_dotenv_file()
    try:
        settings = load_settings()
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    from papertrader.broker import AlpacaBroker, MockBroker
    from papertrader.decide import ClaudeDecider, ScriptedDecider
    from papertrader.runner import RunLock, run_once
    from papertrader.state import State

    if args.mock:
        settings = dataclasses.replace(
            settings, log_dir=settings.log_dir / "mock", state_dir=settings.state_dir / "mock")
        broker, mode = MockBroker(), "mock"
    else:
        try:
            check_environment()
            key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
            if not key or not secret:
                print("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY. Put your PAPER keys in "
                      "paper-trading/.env (see README.md), or use --mock.", file=sys.stderr)
                return 2
            if not args.reset_halt and not (os.environ.get("ANTHROPIC_API_KEY")
                                            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
                print("Missing ANTHROPIC_API_KEY. Put it in paper-trading/.env (see README.md), "
                      "or use --mock.", file=sys.stderr)
                return 2
            broker = AlpacaBroker(key, secret)
        except LiveTradingRefused as e:
            print(f"REFUSING TO START: {e}", file=sys.stderr)
            return 2
        mode = "paper-trade" if args.trade else "dry-run"

    def load_state():
        try:
            return State(settings.state_dir)
        except ValueError as e:
            raise SystemExit(f"state file is unreadable ({e}); fix or delete "
                             f"{settings.state_dir}/state.json")

    if args.reset_halt:
        # Under the lock, so a scheduled run cannot write the old halt flag back over this.
        try:
            with RunLock(settings.state_dir):
                state = load_state()
                equity = broker.snapshot()["account"]["equity"]
                state.reset_halt(new_start_equity=equity)
                state.save()
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"Halt cleared. New drawdown baseline: ${equity:,.2f}")
        return 0

    if args.mock:
        decider = ScriptedDecider()
    else:
        decider = ClaudeDecider(settings)

    try:
        with RunLock(settings.state_dir):
            state = load_state()  # loaded inside the lock so runs never overwrite each other
            record = run_once(broker, decider, settings, state,
                              trade=args.trade, mode_label=mode)
    except LiveTradingRefused as e:
        print(f"REFUSING: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # Alpaca/network errors, a bad symbol, another run holding the lock
        msg = f"{type(e).__name__}: {e}"
        print(f"Run failed: {msg}", file=sys.stderr)
        from papertrader.runner import log_failed_run
        log_failed_run(settings, mode, msg)
        return 1

    print((settings.log_dir / "latest.md").read_text())
    if mode == "dry-run" and record["approved"]:
        print("Dry run: nothing was sent. Add --trade to send these to the paper account.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
