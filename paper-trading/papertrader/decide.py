"""Asking Claude for trade proposals.

Claude only proposes. Every proposal then goes through papertrader/risk.py,
which can shrink or reject it. Claude never sends an order itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from anthropic import transform_schema
from pydantic import BaseModel, Field, ValidationError

from .config import PROJECT_DIR, Settings

STRATEGY_FILE = PROJECT_DIR / "strategy.md"


class ProposedTrade(BaseModel):
    symbol: str = Field(description="Ticker from the watchlist, e.g. MSFT")
    action: Literal["buy", "sell"]
    dollars: float = Field(description="Dollar amount to buy, or dollar value to sell")
    reason: str = Field(description="One or two sentences naming the numbers behind the trade")


class Decision(BaseModel):
    market_view: str = Field(description="Two or three sentences on what the numbers show today")
    trades: list[ProposedTrade] = Field(description="Proposed trades; an empty list means do nothing")
    notes: str = Field(description="Anything skipped and why, or an empty string")


@dataclass
class DecisionResult:
    decision: Decision
    meta: dict = field(default_factory=dict)  # model, stop reason, token usage, errors


EMPTY = Decision(market_view="", trades=[], notes="")
DECISION_SCHEMA = transform_schema(Decision)

OUTPUT_RULES = """
You are the decision step of a paper-trading bot (fake money, Alpaca paper account).
Follow the strategy above exactly. Separate code enforces hard limits on size,
cash and losses after you answer, so propose what the strategy calls for and do
not try to work around limits.

Rules for your answer:
- Propose trades only for symbols in the watchlist.
- "dollars" is the dollar amount for the trade. For a full exit, use the
  position's current market value.
- Never propose selling a symbol that is not currently held.
- An empty trades list is a good answer when nothing meets the rules.
""".strip()


def build_prompt(settings: Settings, snapshot: dict, features: dict[str, dict],
                 strategy_text: str) -> tuple[str, str]:
    equity = snapshot["account"]["equity"] or 0.0
    positions = []
    for p in snapshot["positions"]:
        positions.append({
            **p,
            "pct_of_equity": round(p["market_value"] / equity, 4) if equity else None,
        })
    context = {
        "account": snapshot["account"],
        "market_open": snapshot["clock"]["is_open"],
        "positions": positions,
        "open_orders": snapshot["open_orders"],
        "recent_orders": snapshot["recent_orders"],
        "watchlist_features": features,
        "hard_limits_enforced_by_code": {
            "max_position_pct_of_equity": settings.max_position_pct,
            "max_invested_pct_of_equity": settings.max_invested_pct,
            "max_single_buy_dollars": settings.max_order_dollars,
            "max_orders_per_run": settings.max_orders_per_run,
        },
    }
    system = f"{strategy_text.strip()}\n\n---\n\n{OUTPUT_RULES}"
    user = (
        "Today's account and market data (JSON). Fractions are not percents: "
        "0.05 means 5%.\n\n" + json.dumps(context, indent=1, default=str)
        + "\n\nPropose today's trades under the strategy."
    )
    return system, user


class ClaudeDecider:
    def __init__(self, settings: Settings, strategy_file: Path = STRATEGY_FILE):
        import anthropic

        self.settings = settings
        self.strategy_text = strategy_file.read_text()
        # Reads ANTHROPIC_API_KEY from the environment.
        self.client = anthropic.Anthropic()

    def decide(self, snapshot: dict, features: dict[str, dict]) -> DecisionResult:
        import anthropic

        system, user = build_prompt(self.settings, snapshot, features, self.strategy_text)
        meta: dict = {"model": self.settings.model, "effort": self.settings.effort}
        try:
            response = self.client.beta.messages.create(
                model=self.settings.model,
                max_tokens=16000,
                # If a safety classifier declines, retry on a fallback model server-side.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={
                    "effort": self.settings.effort,
                    # Structured output: the answer must match the Decision schema.
                    "format": {"type": "json_schema", "schema": DECISION_SCHEMA},
                },
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as e:
            # Fail closed: no decision means no trades.
            meta["error"] = f"{type(e).__name__}: {e}"
            return DecisionResult(EMPTY, meta)

        meta["served_by"] = response.model
        meta["stop_reason"] = response.stop_reason
        usage = response.usage
        meta["usage"] = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            meta["error"] = f"refusal: {getattr(details, 'category', None)}"
            return DecisionResult(EMPTY, meta)
        if response.stop_reason == "max_tokens":
            meta["error"] = "answer was cut off (max_tokens); not trading on a partial answer"
            return DecisionResult(EMPTY, meta)
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        try:
            parsed = Decision.model_validate_json(text)
        except ValidationError as e:
            meta["error"] = f"could not read Claude's answer: {e.error_count()} schema error(s)"
            return DecisionResult(EMPTY, meta)
        return DecisionResult(parsed, meta)


class ScriptedDecider:
    """Stand-in for Claude in --mock runs and tests."""

    def __init__(self, decision: Decision | None = None):
        self.decision = decision

    def decide(self, snapshot: dict, features: dict[str, dict]) -> DecisionResult:
        if self.decision is not None:
            return DecisionResult(self.decision, {"model": "scripted"})
        # Default script: buy the strongest uptrending names at 6% of equity.
        equity = snapshot["account"]["equity"]
        held = {p["symbol"] for p in snapshot["positions"]}
        picks = sorted(
            (s for s, f in features.items()
             if f.get("above_sma50") and f.get("sma20_above_sma50") and (f.get("return_63d") or 0) > 0
             and s not in held),
            key=lambda s: features[s].get("return_63d") or 0,
            reverse=True,
        )[:3]
        trades = [ProposedTrade(symbol=s, action="buy", dollars=round(0.06 * equity, 2),
                                reason="scripted mock decision") for s in picks]
        return DecisionResult(
            Decision(market_view="mock run", trades=trades, notes=""),
            {"model": "scripted"},
        )
