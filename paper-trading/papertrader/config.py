"""Settings. Edit the defaults here, or override any of them with an environment
variable of the same name (in your shell or in paper-trading/.env).

Percentages are fractions: 0.10 means 10%.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]  # .../paper-trading

DEFAULT_WATCHLIST = (
    "AAPL,MSFT,NVDA,GOOGL,AMZN,META,AVGO,AMD,CRM,ORCL,ADBE,NOW,SPY,QQQ"
)


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw not in (None, "") else default


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    # What the bot may trade. Anything Claude proposes outside this list is rejected.
    watchlist: tuple[str, ...]

    # Hard limits, enforced by code (papertrader/risk.py), not by Claude.
    max_position_pct: float     # one stock can be at most this share of equity
    max_invested_pct: float     # all stocks together at most this share of equity
    max_order_dollars: float    # biggest single buy
    max_orders_per_run: int     # most orders sent in one run
    daily_loss_limit_pct: float # if equity is down this much since yesterday's close: no buys today
    max_drawdown_pct: float     # if equity falls this far below the starting equity: halt everything
    min_order_dollars: float    # Alpaca's fractional minimum is $1

    # Claude settings.
    model: str
    effort: str

    # Where logs and state live.
    log_dir: Path = field(default=PROJECT_DIR / "logs")
    state_dir: Path = field(default=PROJECT_DIR / "state")


def load_settings() -> Settings:
    watchlist = tuple(
        s.strip().upper()
        for s in os.environ.get("WATCHLIST", DEFAULT_WATCHLIST).split(",")
        if s.strip()
    )
    settings = Settings(
        watchlist=watchlist,
        max_position_pct=_float("MAX_POSITION_PCT", 0.10),
        max_invested_pct=_float("MAX_INVESTED_PCT", 0.80),
        max_order_dollars=_float("MAX_ORDER_DOLLARS", 5000.0),
        max_orders_per_run=_int("MAX_ORDERS_PER_RUN", 5),
        daily_loss_limit_pct=_float("DAILY_LOSS_LIMIT_PCT", 0.03),
        max_drawdown_pct=_float("MAX_DRAWDOWN_PCT", 0.15),
        min_order_dollars=_float("MIN_ORDER_DOLLARS", 1.0),
        model=os.environ.get("CLAUDE_MODEL", "claude-opus-5-5"),
        effort=os.environ.get("CLAUDE_EFFORT", "high"),
    )
    validate(settings)
    return settings


def validate(s: Settings) -> None:
    """Fail fast on settings that would make the limits meaningless."""
    problems = []
    for name in ("max_position_pct", "max_invested_pct", "max_order_dollars",
                 "daily_loss_limit_pct", "max_drawdown_pct", "min_order_dollars"):
        if not math.isfinite(getattr(s, name)):
            problems.append(f"{name.upper()} must be a normal number (got {getattr(s, name)})")
    if problems:
        raise ValueError("Bad settings: " + "; ".join(problems))
    if not s.watchlist:
        problems.append("WATCHLIST is empty")
    for name in ("max_position_pct", "max_invested_pct", "daily_loss_limit_pct", "max_drawdown_pct"):
        v = getattr(s, name)
        if not (0 < v <= 1):
            problems.append(f"{name.upper()} must be between 0 and 1 (got {v})")
    if s.max_position_pct > s.max_invested_pct:
        problems.append("MAX_POSITION_PCT cannot be larger than MAX_INVESTED_PCT")
    if s.max_order_dollars <= 0:
        problems.append("MAX_ORDER_DOLLARS must be positive")
    if s.max_orders_per_run < 0:
        problems.append("MAX_ORDERS_PER_RUN cannot be negative")
    if s.min_order_dollars < 1:
        problems.append("MIN_ORDER_DOLLARS must be at least 1 (Alpaca's fractional minimum)")
    if s.effort not in ("low", "medium", "high", "xhigh", "max"):
        problems.append("CLAUDE_EFFORT must be one of low, medium, high, xhigh, max")
    if problems:
        raise ValueError("Bad settings: " + "; ".join(problems))
