"""Asking Claude for trade proposals.

Claude only proposes. Every proposal then goes through papertrader/risk.py,
which can shrink or reject it. Claude never sends an order itself.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import PROJECT_DIR, Settings

STRATEGY_FILE = PROJECT_DIR / "strategy.md"


class ProposedTrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(description="Ticker from the watchlist, e.g. MSFT")
    action: Literal["buy", "sell"]
    dollars: float = Field(description="Dollar amount to buy, or dollar value to sell")
    reason: str = Field(description="One or two sentences naming the numbers behind the trade")


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_view: str = Field(description="Two or three sentences on what the numbers show today")
    trades: list[ProposedTrade] = Field(description="Proposed trades; an empty list means do nothing")
    notes: str = Field(description="Anything skipped and why, or an empty string")


@dataclass
class DecisionResult:
    decision: Decision
    meta: dict = field(default_factory=dict)  # model, stop reason, token usage, errors


EMPTY = Decision(market_view="", trades=[], notes="")
DECISION_SCHEMA = Decision.model_json_schema()

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


# Secrets the Claude Code call never needs. The Anthropic ones are removed so the
# call runs on your Claude subscription: in print mode Claude Code always uses
# ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN when one is set, which would bill an
# API account instead.
CHILD_ENV_DROP = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ALPACA_API_KEY",
                  "ALPACA_SECRET_KEY", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY")

# Where Claude Code usually lives, for runs (like cron) whose PATH is minimal.
CLAUDE_BIN_CANDIDATES = (
    "~/.local/bin/claude",
    "~/.claude/local/claude",
    "/opt/homebrew/bin/claude",
    "/usr/local/bin/claude",
)


def find_claude(configured: str | None = None) -> str | None:
    """Path to the claude CLI, or None if it can't be found."""
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    found = shutil.which("claude")
    if found:
        return found
    for c in CLAUDE_BIN_CANDIDATES:
        path = Path(c).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def child_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in CHILD_ENV_DROP}


def _tail(text: str | bytes | None, n: int = 500) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    return (text or "").strip()[-n:]


class ClaudeDecider:
    """Asks Claude through Claude Code (the `claude` CLI) in print mode, so the
    call runs on your logged-in Claude subscription. No API key is involved.

    Claude Code runs with every tool switched off, your CLAUDE.md files, hooks,
    plugins and MCP servers ignored (--safe-mode), in an empty temporary folder.
    It can only read the prompt and answer in the Decision JSON shape.
    """

    def __init__(self, settings: Settings, strategy_file: Path = STRATEGY_FILE,
                 run=subprocess.run):
        self.settings = settings
        self.strategy_text = strategy_file.read_text()
        self.claude_bin = find_claude(settings.claude_bin)
        self._run = run

    def command(self, system: str) -> list[str]:
        return [
            self.claude_bin or "claude",
            "-p",                                  # print mode: one answer, then exit
            "--output-format", "json",
            "--json-schema", json.dumps(DECISION_SCHEMA),
            "--model", self.settings.model,
            "--effort", self.settings.effort,
            "--system-prompt", system,             # replaces Claude Code's coding prompt
            "--tools", "",                         # no tools at all: no files, no shell, no web
            "--safe-mode",                         # ignore CLAUDE.md, hooks, plugins, MCP, memory
            "--strict-mcp-config",
            "--max-turns", "5",
            "--no-session-persistence",
        ]

    def decide(self, snapshot: dict, features: dict[str, dict]) -> DecisionResult:
        system, user = build_prompt(self.settings, snapshot, features, self.strategy_text)
        meta: dict = {"via": "claude-code", "model": self.settings.model,
                      "effort": self.settings.effort}
        if not self.claude_bin:
            meta["error"] = ("Claude Code (the claude command) was not found; install it, or "
                             "set CLAUDE_BIN in .env to its full path")
            return DecisionResult(EMPTY, meta)

        try:
            with tempfile.TemporaryDirectory(prefix="papertrader-claude-") as tmp:
                proc = self._run(
                    self.command(system),
                    input=user,          # the data goes in on stdin, not as an argument
                    capture_output=True,
                    text=True,
                    cwd=tmp,             # empty folder: no project files or CLAUDE.md nearby
                    env=child_env(),
                    timeout=self.settings.claude_timeout_s,
                )
        except subprocess.TimeoutExpired:
            meta["error"] = f"Claude Code took longer than {self.settings.claude_timeout_s}s"
            return DecisionResult(EMPTY, meta)
        except OSError as e:
            meta["error"] = f"could not start Claude Code: {e}"
            return DecisionResult(EMPTY, meta)

        # Fail closed: anything other than a clean, schema-checked answer means no trades.
        try:
            out = json.loads(proc.stdout or "")
        except json.JSONDecodeError:
            out = None
        if not isinstance(out, dict):
            meta["error"] = (f"Claude Code exited {proc.returncode} without a readable result: "
                             f"{_tail(proc.stderr) or _tail(proc.stdout)}")
            return DecisionResult(EMPTY, meta)

        usage = out.get("usage") or {}
        meta.update({
            "served_by": list((out.get("modelUsage") or {}).keys()),
            "subtype": out.get("subtype"),
            "stop_reason": out.get("stop_reason"),
            "num_turns": out.get("num_turns"),
            "duration_ms": out.get("duration_ms"),
            "usage": {"input_tokens": usage.get("input_tokens"),
                      "output_tokens": usage.get("output_tokens")},
        })
        if (proc.returncode != 0 or out.get("type") != "result" or out.get("is_error")
                or out.get("subtype") != "success"):
            detail = out.get("result") if isinstance(out.get("result"), str) else ""
            meta["error"] = (f"Claude Code did not succeed (exit {proc.returncode}, "
                             f"{out.get('subtype')}): {_tail(detail) or _tail(proc.stderr)}")
            return DecisionResult(EMPTY, meta)
        structured = out.get("structured_output")
        if not isinstance(structured, dict):
            meta["error"] = "Claude Code returned no structured answer"
            return DecisionResult(EMPTY, meta)
        try:
            parsed = Decision.model_validate(structured)
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
