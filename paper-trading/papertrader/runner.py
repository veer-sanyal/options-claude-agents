"""One run of the bot: read the paper account, ask Claude, apply the limits,
then either log the plan (dry run) or send the orders to the paper account."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .decide import EMPTY, DecisionResult
from .features import compute_features
from .journal import append_run
from .risk import account_gate, apply_limits
from .state import State


class RunLock:
    """Stops two runs (say, a scheduled one and a manual one) from overlapping."""

    def __init__(self, state_dir: Path, stale_after_s: int = 3600):
        self.path = state_dir / "run.lock"
        self.stale_after_s = stale_after_s

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and time.time() - self.path.stat().st_mtime > self.stale_after_s:
            self.path.unlink(missing_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise RuntimeError(f"another run seems to be in progress ({self.path} exists)")
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def run_once(broker, decider, settings: Settings, state: State, *, trade: bool,
             mode_label: str) -> dict:
    now = datetime.now(timezone.utc)
    run_id = "pt-" + now.strftime("%Y%m%d%H%M%S")
    errors: list[str] = []

    snapshot = broker.snapshot()
    account = snapshot["account"]
    state.ensure_start_equity(account["equity"])

    prices = broker.prices(list(settings.watchlist))
    features = {
        sym: compute_features(p["closes"], p["last_price"]) for sym, p in prices.items()
    }

    # If the account gate already blocks all trading, skip the Claude call entirely.
    block_all, _, _ = account_gate(snapshot, settings, state.start_equity, state.halted)
    if block_all:
        result = DecisionResult(EMPTY, {"skipped": block_all})
    else:
        result = decider.decide(snapshot, features)
    if result.meta.get("error"):
        errors.append(f"Claude: {result.meta['error']}")

    assets: dict[str, dict] = {}
    for t in result.decision.trades:
        sym = (t.symbol or "").strip().upper()
        if sym in settings.watchlist and sym not in assets:
            try:
                assets[sym] = broker.asset(sym)
            except Exception as e:  # unknown asset: risk.py will reject it as not tradable
                assets[sym] = {}
                errors.append(f"asset lookup {sym}: {type(e).__name__}: {e}")

    risk, newly_halted = apply_limits(
        result.decision, snapshot, features, assets, settings,
        start_equity=state.start_equity, halted=state.halted, run_id=run_id,
    )
    if newly_halted:
        state.halt(risk.blocked_reason or "drawdown limit")

    results: list[dict] | None = None
    market_open = snapshot["clock"]["is_open"]
    if trade and risk.approved:
        if not broker.is_market_open():
            errors.append("market is closed; no orders sent (run again during market hours)")
            market_open = False
        else:
            results = []
            for order in risk.approved:
                try:
                    results.append(broker.submit(order))
                except Exception as e:
                    results.append({"status": f"error: {type(e).__name__}: {e}",
                                    "symbol": order.symbol})
                    errors.append(f"order {order.symbol}: {type(e).__name__}: {e}")

    record = {
        "run_id": run_id,
        "time": now.isoformat(),
        "mode": mode_label,
        "account": account,
        "start_equity": state.start_equity,
        "market_open": market_open,
        "positions": snapshot["positions"],
        "features": features,
        "decision": result.decision.model_dump(),
        "claude": result.meta,
        "approved": [o.as_dict() for o in risk.approved],
        "rejected": risk.rejected,
        "blocked_reason": risk.blocked_reason,
        "buys_blocked_reason": risk.buys_blocked_reason,
        "results": results,
        "errors": errors,
        "halted": state.halted,
    }
    state.save()
    append_run(settings.log_dir, record)
    return record
