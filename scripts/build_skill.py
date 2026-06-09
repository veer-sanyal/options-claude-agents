#!/usr/bin/env python3
"""Generate the tech-options-framework skill reference files from the canonical report.

Single source of truth: `deep-research-report.md` at the repo root. The skill's
per-section reference files are build artifacts — never hand-edit them. Edit the
report, re-run this script, and the skill stays in sync. This is the whole point
of packaging the methodology as a skill instead of hand-distilling it into agent
prompt strings (which is how the legacy options-worker does it, and why those
groundings drift from the doc).

Usage:
    python options-agents/scripts/build_skill.py
"""

from __future__ import annotations

import pathlib
import re

def _find_report() -> pathlib.Path:
    """Locate deep-research-report.md by walking up from this script.

    Works whether the project sits at a repo root (standalone) or nested under
    options-agents/ inside the options monorepo.
    """
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "deep-research-report.md"
        if candidate.exists():
            return candidate
    raise SystemExit("deep-research-report.md not found in any parent directory")


REPORT = _find_report()
# References live next to this script's project root (scripts/ -> project root).
REFS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "tech-options-framework" / "references"

# Stable slug per section heading. If you rename a heading in the report, update
# the matching slug here so the agent's cross-references (and the rubric) hold.
SLUGS = {
    "Workflow": "01-workflow",
    "Strategy design": "02-strategy-design",
    "Underlier selection": "03-underlier-selection",
    "Regime adaptation": "04-regime-adaptation",
    "Risk management": "05-risk-management",
    "Execution and review": "06-execution-and-review",
    "Evidence, pitfalls, and portfolio fit": "07-evidence-pitfalls",
}


# Deep-research exports carry citation/entity markup that is invisible noise to a
# human reader but lands verbatim in the skill the model reads. Strip it: ChatGPT
# "cite…turn…" tokens (often wrapped in private-use-area chars U+E200–U+E206),
# entity[...] annotations, and any stray private-use characters.
_CITE_TOKEN_RE = re.compile("\ue200[^\ue201]*\ue201")  # whole \ue200...\ue201 cluster (entity[...] / cite...turn...), separators and all
_ENTITY_RE = re.compile(r"entity\[[^\]]*\]")
_NAV_TOKEN_RE = re.compile(r"(?:cite|navlist|video|image|news)turn\d+\w*")


def clean(text: str) -> str:
    """Remove deep-research export markup so it never reaches the model."""
    text = _CITE_TOKEN_RE.sub("", text)
    text = _ENTITY_RE.sub("", text)
    text = _NAV_TOKEN_RE.sub("", text)
    # Drop any leftover Unicode private-use-area characters.
    text = "".join(ch for ch in text if not (0xE000 <= ord(ch) <= 0xF8FF))
    return text


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return [(heading, body_including_heading), ...] for each `## ` section."""
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    buf: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            if current_heading is not None:
                sections.append((current_heading, "".join(buf)))
            current_heading = m.group(1)
            buf = [line]
        elif current_heading is not None:
            buf.append(line)
    if current_heading is not None:
        sections.append((current_heading, "".join(buf)))
    return sections


def main() -> None:
    if not REPORT.exists():
        raise SystemExit(f"canonical report not found: {REPORT}")
    REFS.mkdir(parents=True, exist_ok=True)

    text = REPORT.read_text()
    written = 0
    seen: set[str] = set()
    for heading, body in split_sections(text):
        slug = SLUGS.get(heading)
        if slug is None:
            print(f"  skip (no slug mapping): {heading!r}")
            continue
        seen.add(heading)
        banner = (
            "<!-- GENERATED FILE — do not edit by hand.\n"
            "     Source: deep-research-report.md  ·  Regenerate: "
            "python options-agents/scripts/build_skill.py -->\n\n"
        )
        (REFS / f"{slug}.md").write_text(banner + clean(body).rstrip() + "\n")
        written += 1
        print(f"  wrote {slug}.md  <-  ## {heading}")

    missing = set(SLUGS) - seen
    if missing:
        print(f"  WARNING: headings in SLUGS not found in report: {sorted(missing)}")
    print(f"done: {written} reference file(s) in {REFS}")


if __name__ == "__main__":
    main()
