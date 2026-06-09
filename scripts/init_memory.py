#!/usr/bin/env python3
"""Setup (control plane): create — or reuse — the portfolio memory store and seed
its initial state, then print MEMORY_STORE_ID.

This runs from setup.sh, which captures the id into .ids.env so every run reuses
the same store. Without a persisted id, run_session.py would have to create a new
store each run — silently resetting portfolio state and the drift log and
defeating the whole review loop. run_session.py therefore refuses to create one
and fails closed if MEMORY_STORE_ID is unset.

Idempotent:
  - reuses MEMORY_STORE_ID if already exported (creates one otherwise);
  - seeds every file under memory-seed/ that is not already present, and never
    clobbers a memory that already exists (a path conflict is left untouched so
    live state survives re-runs).

Usage:
    python scripts/init_memory.py            # human-readable -> MEMORY_STORE_ID=...
    export MEMORY_STORE_ID=$(python scripts/init_memory.py --quiet)
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

import anthropic

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED_DIR = PROJECT_ROOT / "memory-seed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true",
                        help="print only the bare store id (for $(...) capture)")
    args = parser.parse_args()

    client = anthropic.Anthropic()

    store_id = os.environ.get("MEMORY_STORE_ID")
    if store_id:
        if not args.quiet:
            print(f"# reusing existing memory store {store_id}", file=sys.stderr)
    else:
        store = client.beta.memory_stores.create(
            name="options-portfolio-state",
            description=(
                "Open positions, cost basis, per-name notes, and the behavioral "
                "drift log. Read before acting; write updates back as you learn."
            ),
        )
        store_id = store.id
        if not args.quiet:
            print(f"# created memory store {store_id}", file=sys.stderr)

    # Seed initial state. memories.create is keyed by path and returns 409 if the
    # path is already occupied — we treat that as "already seeded" and move on so
    # we never overwrite live portfolio state on a re-run.
    if SEED_DIR.is_dir():
        for f in sorted(SEED_DIR.rglob("*")):
            if not f.is_file():
                continue
            rel = "/" + f.relative_to(SEED_DIR).as_posix()
            try:
                client.beta.memory_stores.memories.create(
                    store_id, path=rel, content=f.read_text()
                )
                if not args.quiet:
                    print(f"# seeded {rel}", file=sys.stderr)
            except anthropic.APIStatusError as e:
                if getattr(e, "status_code", None) == 409:
                    if not args.quiet:
                        print(f"# skip {rel} (already present)", file=sys.stderr)
                else:
                    raise

    if args.quiet:
        print(store_id)
    else:
        print(f"MEMORY_STORE_ID={store_id}")


if __name__ == "__main__":
    main()
