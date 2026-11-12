"""Small persistent state: the starting equity (for the drawdown limit) and the halt flag."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class State:
    def __init__(self, state_dir: Path):
        self.path = state_dir / "state.json"
        self.data: dict = {}
        if self.path.exists():
            # A corrupt state file stops the bot instead of silently resetting the limits.
            self.data = json.loads(self.path.read_text())

    @property
    def start_equity(self) -> float | None:
        return self.data.get("start_equity")

    @property
    def halted(self) -> bool:
        return bool(self.data.get("halted"))

    def ensure_start_equity(self, equity: float) -> None:
        if not self.data.get("start_equity") and equity > 0:
            self.data["start_equity"] = equity
            self.data["started_at"] = datetime.now(timezone.utc).isoformat()

    def halt(self, reason: str) -> None:
        self.data["halted"] = True
        self.data["halt_reason"] = reason
        self.data["halted_at"] = datetime.now(timezone.utc).isoformat()

    def reset_halt(self, new_start_equity: float | None = None) -> None:
        self.data["halted"] = False
        self.data.pop("halt_reason", None)
        if new_start_equity:
            self.data["start_equity"] = new_start_equity
            self.data["started_at"] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)
