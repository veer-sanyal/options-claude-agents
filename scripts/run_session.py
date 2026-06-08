#!/usr/bin/env python3
"""Runtime (data plane): start a coordinator session, stream it, handle the
deterministic custom tools host-side, and gate order placement.

Setup (agents/env/skill) is one-time and lives in setup.sh + the YAML. This
script is what runs per analysis. Load the IDs first:

    source options-agents/.ids.env   # written by setup.sh
    python options-agents/scripts/run_session.py --outcome

Flags:
    --outcome   grade-and-revise against rubrics/analysis-rubric.md (recommended)
                instead of a single conversational pass.

The custom-tool handlers below are where the deterministic math stays out of the
LLM. Wire each one to options-engine (import it, or call options-api over HTTP).
They ship as stubs so the loop runs end-to-end before you connect the engine.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import anthropic

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = PROJECT_ROOT / "rubrics" / "analysis-rubric.md"


# --------------------------------------------------------------------------- #
# Deterministic custom tools — handled host-side. Replace the stub bodies with
# real calls into options-engine / options-api. Keep the math here, not in the
# model. Names must match the custom tools declared in the agent YAML.
# --------------------------------------------------------------------------- #
def classify_regime(args: dict) -> dict:
    # TODO: options_engine.regime.detector.classify(args["ticker"])
    return {"ticker": args["ticker"], "regime": "sideways", "trend_strength": 0.0, "iv_rank": None,
            "_stub": True}


def check_position_triggers(args: dict) -> dict:
    # TODO: options_engine.portfolio.triggers.evaluate(args["position_id"])
    return {"position_id": args["position_id"], "triggers": [], "_stub": True}


def size_position(args: dict) -> dict:
    # TODO: options_engine.portfolio.sizing.max_size(...)
    return {"ticker": args["ticker"], "max_notional_usd": args["notional_usd"],
            "breaches": [], "_stub": True}


def pattern_metrics(args: dict) -> dict:
    # TODO: options_engine.portfolio.patterns / metrics over args["lookback_days"]
    return {"lookback_days": args["lookback_days"], "metrics": {}, "_stub": True}


HANDLERS = {
    "classify_regime": classify_regime,
    "check_position_triggers": check_position_triggers,
    "size_position": size_position,
    "pattern_metrics": pattern_metrics,
}


def env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"missing env {name} — did you `source options-agents/.ids.env`?")
    return val


def ensure_memory_store(client: anthropic.Anthropic) -> str:
    """Reuse MEMORY_STORE_ID if set, else create one. Persist the id yourself."""
    existing = os.environ.get("MEMORY_STORE_ID")
    if existing:
        return existing
    store = client.beta.memory_stores.create(
        name="options-portfolio-state",
        description="Open positions, cost basis, per-name notes, and the behavioral drift log.",
    )
    print(f"created memory store {store.id} — add MEMORY_STORE_ID={store.id} to .ids.env to reuse")
    return store.id


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", action="store_true",
                    help="grade-and-revise against the analysis rubric")
    ap.add_argument("--message", default="Run today's portfolio review and produce the action brief.")
    args = ap.parse_args()

    client = anthropic.Anthropic()
    store_id = ensure_memory_store(client)

    session = client.beta.sessions.create(
        agent=env("COORDINATOR_ID"),               # latest version
        environment_id=env("ENV_ID"),
        title="Options portfolio review",
        vault_ids=[v for v in [os.environ.get("BROKERAGE_VAULT_ID")] if v],  # MCP creds
        resources=[{
            "type": "memory_store",
            "memory_store_id": store_id,
            "access": "read_write",
            "instructions": "Portfolio state and the drift log. Read before acting; write updates back.",
        }],
    )
    print(f"session {session.id}")
    print(f"watch: https://platform.claude.com/workspaces/default/sessions/{session.id}")

    # Stream-first, then send the kickoff.
    stream = client.beta.sessions.events.stream(session_id=session.id)

    if args.outcome:
        kickoff = {
            "type": "user.define_outcome",
            "description": args.message,
            "rubric": {"type": "text", "content": RUBRIC.read_text()},
            "max_iterations": 4,
        }
    else:
        kickoff = {"type": "user.message", "content": [{"type": "text", "text": args.message}]}
    client.beta.sessions.events.send(session_id=session.id, events=[kickoff])

    for event in stream:
        etype = event.type

        if etype == "agent.message":
            for block in getattr(event, "content", []) or []:
                if getattr(block, "type", None) == "text":
                    print(block.text, end="", flush=True)

        elif etype == "agent.custom_tool_use":
            handler = HANDLERS.get(event.name)
            result = handler(event.input) if handler else {"error": f"unknown tool {event.name}"}
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{
                    "type": "user.custom_tool_result",
                    "custom_tool_use_id": event.id,
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "is_error": "error" in result,
                }],
            )

        elif etype == "agent.mcp_tool_use" and getattr(event, "evaluated_permission", None) == "ask":
            # Order placement (always_ask). Human-in-the-loop confirmation.
            print(f"\n[CONFIRM] {event.name} input={json.dumps(event.input)}")
            ok = input("allow this order? [y/N] ").strip().lower() == "y"
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{
                    "type": "user.tool_confirmation",
                    "tool_use_id": event.id,
                    "result": "allow" if ok else "deny",
                    **({} if ok else {"deny_message": "Human declined the order."}),
                }],
            )

        elif etype == "session.status_terminated":
            break
        elif etype == "session.status_idle":
            if getattr(event.stop_reason, "type", None) == "requires_action":
                continue          # waiting on a tool result / confirmation we just sent
            break                 # end_turn or retries_exhausted

    print()


if __name__ == "__main__":
    main()
