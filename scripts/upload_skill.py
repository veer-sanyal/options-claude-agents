#!/usr/bin/env python3
"""Setup (control plane): upload the tech-options-framework skill to your
workspace via the Skills API, and print the resulting SKILL_ID.

setup.sh requires SKILL_ID to already exist — this is the step that creates it.
Run build_skill.py first so skills/tech-options-framework/ is current, then:

    python scripts/upload_skill.py                 # first time -> creates a new skill
    eval "$(python scripts/upload_skill.py)"       # capture SKILL_ID into the shell
    export SKILL_ID=$(python scripts/upload_skill.py --quiet)

Re-uploading after the report changes (creates a new VERSION of the same skill,
preserving history) — pass the existing id:

    SKILL_ID=skill_... python scripts/upload_skill.py

Auth resolves the same way the SDK/CLI do (ANTHROPIC_API_KEY or `ant auth login`).
The beta header skills-2025-10-02 is set by the SDK automatically.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

import anthropic
from anthropic.lib import files_from_dir

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_DIR = PROJECT_ROOT / "skills" / "tech-options-framework"
DISPLAY_TITLE = "Tech Options Framework"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true",
                        help="print only the bare skill id (for $(...) capture)")
    args = parser.parse_args()

    if not (SKILL_DIR / "SKILL.md").is_file():
        sys.exit(f"SKILL.md not found under {SKILL_DIR} — run build_skill.py first.")

    client = anthropic.Anthropic()
    files = files_from_dir(str(SKILL_DIR))  # uploads with paths relative to SKILL_DIR

    existing = os.environ.get("SKILL_ID")
    if existing:
        # New version of an existing skill — keeps the version history intact.
        version = client.beta.skills.versions.create(skill_id=existing, files=files)
        skill_id, ver = existing, getattr(version, "version", None) or getattr(version, "id", "")
    else:
        skill = client.beta.skills.create(display_title=DISPLAY_TITLE, files=files)
        skill_id, ver = skill.id, getattr(skill, "latest_version", "")

    if args.quiet:
        print(skill_id)
    else:
        if ver and not existing:
            print(f"# created skill {skill_id} (version {ver})", file=sys.stderr)
        elif ver:
            print(f"# added version {ver} to {skill_id}", file=sys.stderr)
        print(f"SKILL_ID={skill_id}")


if __name__ == "__main__":
    main()
