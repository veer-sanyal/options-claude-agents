# options-claude-agents

A Claude **Managed Agents** implementation of the tech covered-call / LEAP workflow —
the hosted, versioned counterpart to the `options-worker` multi-agent system in the
[`options`](https://github.com/veer-sanyal/options) platform.

It applies the strategy framework from `deep-research-report.md` using four managed-agents
primitives, each chosen by what kind of thing the content is:

| Content | Primitive | Why |
|---|---|---|
| The methodology / workflow / rules | **Skill** (`skills/tech-options-framework`) | Stable reference knowledge, one source of truth, progressive disclosure. Beats hand-distilling the doc into prompt strings. |
| Portfolio state (positions, notes, drift log) | **Memory store** | Mutable; persists across sessions. |
| The math (Greeks, windows, sizing, metrics) | **Custom tools** → `options-engine` | Deterministic. Kept out of the LLM. |
| What "a correct analysis" looks like | **Outcome rubric** (`rubrics/analysis-rubric.md`) | Grade-and-revise loop against §5–§7. |

A coordinator agent delegates to five subagents (Position Watcher, Catalyst Monitor,
Qualitative Researcher, Strategy Structurer, Pattern Reviewer) — mirroring the existing
worker agents — and produces one ranked action brief per run. **It never places trades
without explicit human confirmation** (order tools are gated `always_ask`).

## Layout

```
skills/tech-options-framework/   SKILL.md + references/ (generated from the report)
agents/                          coordinator + 5 subagent YAML definitions
environments/                    cloud environment (limited networking)
rubrics/analysis-rubric.md       Outcome rubric (§5–§7)
scripts/build_skill.py           regenerate skill references from the report
scripts/upload_skill.py          one-time: upload the skill, print SKILL_ID (Skills API)
scripts/create_vault.py          one-time: vault the brokerage MCP credential, print BROKERAGE_VAULT_ID
scripts/setup.sh                 one-time: create env + agents (ant CLI)
scripts/run_session.py           per-run: start session, stream, handle tools (SDK)
deep-research-report.md          canonical strategy source (the skill is built from it)
```

## Setup

**1. Build the skill from the report** (and re-run whenever the report changes):

```bash
python scripts/build_skill.py
```

**2. Upload the skill** to your workspace via the Skills API (`POST /v1/skills` +
`/versions`, beta header `skills-2025-10-02`) and capture the returned `skill_id`:

```bash
export SKILL_ID=$(python scripts/upload_skill.py --quiet)   # re-run with SKILL_ID set to add a version
```

**3. Create the brokerage credential vault** (optional — skip to start read-only).
The agent declares the MCP server URL but carries no auth; credentials live in a
vault that `run_session.py` attaches per session:

```bash
export BROKERAGE_MCP_URL=https://...                        # your TradeStation MCP endpoint
export BROKERAGE_MCP_ACCESS_TOKEN=...                       # + refresh vars for auto-refresh; see the script
export BROKERAGE_VAULT_ID=$(python scripts/create_vault.py --quiet)
```

**4. Create the agents + environment:**

```bash
# SKILL_ID and BROKERAGE_MCP_URL from steps 2-3 must be exported
./scripts/setup.sh                        # writes .ids.env
```

**5. Run an analysis:**

```bash
source .ids.env
python scripts/run_session.py --outcome   # grade-and-revise against the rubric
```

## Wiring the deterministic tools

`scripts/run_session.py` ships the custom-tool handlers (`classify_regime`,
`check_position_triggers`, `size_position`, `pattern_metrics`) as **stubs** so the loop
runs before the engine is connected. Replace each stub body with a call into
`options-engine` (import it) or `options-api` (HTTP). This is the deliberate split: the
model decides *what* to check; the engine computes the numbers.

## Brokerage & safety notes

- **TradeStation** has a documented REST API, so an MCP wrapper is clean. **Robinhood**
  has no official API (community MCP servers wrap unofficial endpoints — 2FA/ToS/breakage
  risk); prefer TradeStation for anything that matters.
- MCP credentials go in a **vault** (`BROKERAGE_VAULT_ID`), never inline or in prompts.
- Position/quote reads are auto-allowed; **order placement is gated `always_ask`** and
  surfaces a confirmation prompt in `run_session.py`. Start read-only; add gated orders
  only once you trust the loop.

## Relationship to `options`

This repo is the agent/skill/rubric layer. The heavy lifting — Greeks, regime detection,
sizing, pattern metrics, market data — stays in `options/options-engine`, surfaced here as
custom tools. Keep `deep-research-report.md` in sync between the two (or treat the
`options` repo's copy as upstream and vendor it here).
