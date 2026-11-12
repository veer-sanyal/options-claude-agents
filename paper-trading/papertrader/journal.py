"""The decision log: one JSON line per run in logs/runs.jsonl, plus a readable
summary of the latest run in logs/latest.md."""

from __future__ import annotations

import json
from pathlib import Path


def append_run(log_dir: Path, record: dict) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "runs.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    (log_dir / "latest.md").write_text(render_markdown(record))
    return path


def render_markdown(r: dict) -> str:
    a = r.get("account") or {}
    lines = [
        f"# Run {r.get('run_id')} ({r.get('mode')})",
        "",
        f"- Time: {r.get('time')}",
        f"- Equity: ${a.get('equity', 0):,.2f} (yesterday's close ${a.get('last_equity', 0):,.2f})",
        f"- Cash: ${a.get('cash', 0):,.2f}",
        f"- Market open: {r.get('market_open')}",
    ]
    if r.get("start_equity"):
        lines.append(f"- Since start: {a.get('equity', 0) / r['start_equity'] - 1:+.2%} "
                     f"(start ${r['start_equity']:,.2f})")
    if r.get("blocked_reason"):
        lines.append(f"- Trading blocked: {r['blocked_reason']}")
    if r.get("buys_blocked_reason"):
        lines.append(f"- Buys blocked: {r['buys_blocked_reason']}")
    if r.get("errors"):
        lines.append(f"- Errors: {'; '.join(r['errors'])}")

    d = r.get("decision") or {}
    lines += ["", "## Claude's view", "", d.get("market_view") or "(none)"]
    if d.get("notes"):
        lines += ["", d["notes"]]

    lines += ["", "## Orders", ""]
    if not r.get("approved"):
        lines.append("None.")
    for o, res in zip(r.get("approved", []), r.get("results", []) or [None] * len(r.get("approved", []))):
        amount = f"${o['notional']:,.2f}" if o.get("notional") else f"{o.get('qty')} sh"
        status = (res or {}).get("status", "not sent")
        lines.append(f"- {o['side'].upper()} {o['symbol']} {amount} -> {status}. {o.get('reason', '')}")

    if r.get("rejected"):
        lines += ["", "## Rejected by the limits", ""]
        for x in r["rejected"]:
            t = x.get("trade") or {}
            lines.append(f"- {str(t.get('action', '')).upper()} {t.get('symbol')} "
                         f"${t.get('dollars', 0):,.2f}: {x.get('why')}")
    return "\n".join(lines) + "\n"


def read_runs(log_dir: Path) -> list[dict]:
    path = log_dir / "runs.jsonl"
    if not path.exists():
        return []
    runs = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return runs
