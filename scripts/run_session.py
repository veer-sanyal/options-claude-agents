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
Until then they FAIL CLOSED — an unwired sizing/trigger tool returns a breach,
zero allowable size, or an error rather than a permissive default, so a missing
engine blocks rather than green-lights. Arm them only after wiring by setting
OPTIONS_ENGINE_CONNECTED=1.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import NoReturn

import anthropic

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = PROJECT_ROOT / "rubrics" / "analysis-rubric.md"


# --------------------------------------------------------------------------- #
# Deterministic custom tools — handled host-side. These are the hard-gate
# enforcers (regime, triggers, sizing, behavioral metrics) and they MUST stay
# out of the model. Until they are wired to options-engine they FAIL CLOSED: a
# money system must never let a missing engine rubber-stamp a trade, so an
# unwired tool returns a breach / zero allowable size / an error rather than a
# permissive default. Replace each stub body with a real options-engine call AND
# set OPTIONS_ENGINE_CONNECTED=1 to arm them. Names must match the agent YAML.
# --------------------------------------------------------------------------- #
ENGINE_CONNECTED = os.environ.get("OPTIONS_ENGINE_CONNECTED", "").strip().lower() in (
    "1", "true", "yes", "on",
)


def _unwired(tool: str) -> NoReturn:
    raise NotImplementedError(
        f"{tool}: OPTIONS_ENGINE_CONNECTED is set but the handler still has its stub "
        f"body — wire it to options-engine before arming the engine flag."
    )


def classify_regime(args: dict) -> dict:
    if not ENGINE_CONNECTED:
        # Fail closed: regime is unknown, not benign. The model must not assume a
        # tradeable regime (the regime gate cannot be satisfied) while offline.
        return {"ticker": args["ticker"],
                "error": "options_engine_not_connected",
                "message": "Regime unavailable — engine offline. The regime gate cannot "
                           "be verified; do not open or hold new short calls on regime grounds.",
                "_fail_closed": True}
    _unwired("classify_regime")  # TODO: options_engine.regime.detector.classify(args["ticker"])


def check_position_triggers(args: dict) -> dict:
    if not ENGINE_CONNECTED:
        # Fail closed: emit a blocking trigger instead of "no triggers", so the
        # watcher cannot read silence as "safe to hold / overwrite".
        return {"position_id": args["position_id"],
                "triggers": [{
                    "type": "engine_offline",
                    "action": "block",
                    "message": "Triggers unavailable — engine offline. Cannot verify "
                               "delta/DTE/assignment/event-window gates; treat as "
                               "unmanageable and do not recommend a new overwrite.",
                }],
                "_fail_closed": True}
    _unwired("check_position_triggers")  # TODO: options_engine.portfolio.triggers.evaluate(...)


def size_position(args: dict) -> dict:
    if not ENGINE_CONNECTED:
        # Fail closed: zero allowable size + a breach. Now any non-zero sizing in a
        # recommendation contradicts the tool result, so the rubric's hard gate fires.
        return {"ticker": args["ticker"],
                "max_notional_usd": 0,
                "breaches": ["options_engine_not_connected: sizing engine offline; max "
                             "allowable size is 0 until it is wired."],
                "_fail_closed": True}
    _unwired("size_position")  # TODO: options_engine.portfolio.sizing.max_size(...)


def pattern_metrics(args: dict) -> dict:
    if not ENGINE_CONNECTED:
        # Fail closed: no metrics rather than empty metrics (which read as "no drift").
        return {"lookback_days": args["lookback_days"],
                "error": "options_engine_not_connected",
                "message": "Behavioral metrics unavailable — engine offline. Do not claim "
                           "'no drift'; state that metrics could not be computed.",
                "_fail_closed": True}
    _unwired("pattern_metrics")  # TODO: options_engine.portfolio.patterns / metrics


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


def memory_store_id() -> str:
    """Return the persisted MEMORY_STORE_ID, or fail closed.

    We deliberately do NOT create a store here. Creating one per run silently
    resets portfolio state and the drift log every time — which defeats the whole
    review loop. Store creation + seeding lives in scripts/init_memory.py (run by
    setup.sh), which writes MEMORY_STORE_ID into .ids.env.
    """
    sid = os.environ.get("MEMORY_STORE_ID")
    if not sid:
        sys.exit(
            "missing MEMORY_STORE_ID — run scripts/init_memory.py (setup.sh does this) "
            "and `source .ids.env`. Refusing to spin up a throwaway store that would "
            "reset portfolio state and the drift log on every run."
        )
    return sid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", action="store_true",
                    help="grade-and-revise against the analysis rubric")
    ap.add_argument("--message", default="Run today's portfolio review and produce the action brief.")
    args = ap.parse_args()

    client = anthropic.Anthropic()
    store_id = memory_store_id()

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
