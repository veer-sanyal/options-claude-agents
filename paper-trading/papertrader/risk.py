"""Hard limits. Claude proposes; this module decides what actually gets sent.

Every rule here is deterministic and fails closed: if a number is missing or
odd, the trade is rejected rather than guessed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .broker import PlannedOrder
from .config import Settings
from .decide import Decision

SYMBOL_RE = re.compile(r"^[A-Z][A-Z.]{0,9}$")


@dataclass
class RiskResult:
    approved: list[PlannedOrder] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)  # {"trade": ..., "why": ...}
    blocked_reason: str | None = None   # set when no trading at all is allowed
    buys_blocked_reason: str | None = None


def _floor(x: float, places: int) -> float:
    m = 10 ** places
    return math.floor(x * m) / m


def account_gate(snapshot: dict, settings: Settings, start_equity: float | None,
                 halted: bool) -> tuple[str | None, str | None, bool]:
    """Returns (block_all_reason, block_buys_reason, newly_halted)."""
    a = snapshot["account"]
    equity, last_equity = a.get("equity") or 0.0, a.get("last_equity") or 0.0

    if halted:
        return "bot is halted (drawdown limit hit earlier); run with --reset-halt to resume", None, False
    if a.get("trading_blocked") or a.get("account_blocked") or a.get("trade_suspended_by_user"):
        return "Alpaca reports trading is blocked on this account", None, False
    if str(a.get("status", "")).upper() not in ("ACTIVE", "ACCOUNTSTATUS.ACTIVE"):
        return f"account status is {a.get('status')!r}, not ACTIVE", None, False
    if equity <= 0:
        return "account equity is missing or zero", None, False
    if start_equity and equity < start_equity * (1 - settings.max_drawdown_pct):
        return (
            f"equity ${equity:,.2f} is more than {settings.max_drawdown_pct:.0%} below the "
            f"starting ${start_equity:,.2f}; halting",
            None,
            True,
        )
    if last_equity > 0 and equity < last_equity * (1 - settings.daily_loss_limit_pct):
        return None, (
            f"equity is down more than {settings.daily_loss_limit_pct:.0%} since yesterday's "
            f"close; no buys today (sells still allowed)"
        ), False
    return None, None, False


def apply_limits(
    decision: Decision,
    snapshot: dict,
    features: dict[str, dict],
    assets: dict[str, dict],
    settings: Settings,
    *,
    start_equity: float | None,
    halted: bool,
    run_id: str,
) -> tuple[RiskResult, bool]:
    """Turn Claude's proposals into approved orders. Returns (result, newly_halted)."""
    res = RiskResult()
    block_all, block_buys, newly_halted = account_gate(snapshot, settings, start_equity, halted)
    res.blocked_reason, res.buys_blocked_reason = block_all, block_buys

    def reject(trade, why: str) -> None:
        res.rejected.append({"trade": trade.model_dump() if hasattr(trade, "model_dump") else trade,
                             "why": why})

    if block_all:
        for t in decision.trades:
            reject(t, block_all)
        return res, newly_halted

    a = snapshot["account"]
    equity = a["equity"]
    cash_left = max(0.0, a.get("cash") or 0.0)  # cash only: never trade on margin
    long_positions = {p["symbol"]: p for p in snapshot["positions"] if p.get("side", "long") == "long"}
    short_symbols = {p["symbol"] for p in snapshot["positions"] if p.get("side") == "short"}
    invested = sum(p["market_value"] for p in long_positions.values())
    open_order_symbols = {o["symbol"] for o in snapshot["open_orders"]}
    watch = set(settings.watchlist)
    seen: set[str] = set()

    # Sells first (they reduce risk), then buys; each group in Claude's order.
    trades = [t for t in decision.trades if t.action == "sell"] + \
             [t for t in decision.trades if t.action == "buy"]

    for t in trades:
        sym = (t.symbol or "").strip().upper()
        if len(res.approved) >= settings.max_orders_per_run:
            reject(t, f"already at {settings.max_orders_per_run} orders this run")
            continue
        if not SYMBOL_RE.match(sym) or sym not in watch:
            reject(t, "symbol is not in the watchlist")
            continue
        if sym in seen:
            reject(t, "more than one trade proposed for this symbol; kept the first")
            continue
        seen.add(sym)
        if sym in open_order_symbols:
            reject(t, "an order for this symbol is already open")
            continue
        if sym in short_symbols:
            reject(t, "account holds a short position here; the bot does not touch shorts")
            continue
        dollars = t.dollars
        if not isinstance(dollars, (int, float)) or not math.isfinite(dollars) or dollars <= 0:
            reject(t, "dollar amount is not a positive number")
            continue
        price = (features.get(sym) or {}).get("price")
        if not price or not math.isfinite(price) or price <= 0:
            reject(t, "no usable price")
            continue
        asset = assets.get(sym) or {}
        if not asset.get("tradable"):
            reject(t, "Alpaca says this asset is not tradable")
            continue

        if t.action == "sell":
            pos = long_positions.get(sym)
            available = (pos or {}).get("qty_available", (pos or {}).get("qty", 0.0)) or 0.0
            if not pos or available <= 0:
                reject(t, "not held (or all shares are tied up in open orders); no shorting")
                continue
            held_value = available * price
            if dollars >= 0.98 * held_value:
                qty = available  # full exit: sell exactly what is held
            else:
                qty = dollars / price
                if not asset.get("fractionable"):
                    qty = math.floor(qty)
                qty = min(_floor(qty, 9), available)
            if qty <= 0:
                reject(t, "sell amount rounds to zero shares")
                continue
            res.approved.append(PlannedOrder(
                symbol=sym, side="sell", qty=qty, est_dollars=qty * price, reason=t.reason,
                client_order_id=f"{run_id}-{len(res.approved) + 1}"[:48],
            ))
            continue

        # ---- buys
        if block_buys:
            reject(t, block_buys)
            continue
        caps = {
            "single-order cap": settings.max_order_dollars,
            "per-position cap": settings.max_position_pct * equity
                                - (long_positions.get(sym, {}).get("market_value") or 0.0),
            "total-invested cap": settings.max_invested_pct * equity - invested,
            "available cash": cash_left,
        }
        allowed = min(dollars, *caps.values())
        binding = min(caps, key=caps.get) if allowed < dollars else None
        if allowed < settings.min_order_dollars:
            reject(t, f"no room under the {binding or 'limits'} (allowed ${max(allowed, 0):,.2f})")
            continue
        if asset.get("fractionable"):
            notional = _floor(allowed, 2)
            qty = None
            cost = notional
        else:
            whole = math.floor(allowed / price)
            if whole < 1:
                reject(t, "not fractionable and one share costs more than the room left")
                continue
            notional, qty, cost = None, float(whole), whole * price
        reason = t.reason if binding is None else f"{t.reason} [shrunk to fit the {binding}]"
        res.approved.append(PlannedOrder(
            symbol=sym, side="buy", notional=notional, qty=qty, est_dollars=cost, reason=reason,
            client_order_id=f"{run_id}-{len(res.approved) + 1}"[:48],
        ))
        cash_left -= cost
        invested += cost
        if sym in long_positions:
            long_positions[sym] = {**long_positions[sym],
                                   "market_value": long_positions[sym]["market_value"] + cost}
        else:
            long_positions[sym] = {"symbol": sym, "market_value": cost, "qty": 0.0}

    return res, newly_halted
