#!/usr/bin/env python3
"""Validate consolidated agent profiles in docs mirror.

Scope: docs/00-project/ai/agents/snapshots/collected/.claude/agents
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

AGENTS_DIR = Path("docs/00-project/ai/agents/snapshots/collected/.claude/agents")
SKIP = {"README.md", "ORCHESTRATION.md"}
BANNED_SUFFIXES = ("-pro", "-master", "-expert")


@dataclass
class Finding:
    file: str
    message: str


def parse_frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not match:
        return None
    frontmatter: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate consolidated agent profiles in docs mirror."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Enable strict checks for canonical specialist templates "
            "(Boundary note + Operating modes)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    findings: list[Finding] = []

    if not AGENTS_DIR.exists():
        print(f"ERROR: directory not found: {AGENTS_DIR}")
        return 2

    files = sorted(p for p in AGENTS_DIR.glob("*.md") if p.name not in SKIP)
    names = {p.stem for p in files}

    alias_count = 0
    canonical_count = 0

    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        frontmatter = parse_frontmatter(text)
        if frontmatter is None:
            findings.append(Finding(path.name, "missing frontmatter"))
            continue

        name = frontmatter.get("name", "")
        if name != path.stem:
            findings.append(
                Finding(
                    path.name,
                    f"frontmatter name mismatch: {name!r} != {path.stem!r}",
                )
            )

        if path.stem.endswith(BANNED_SUFFIXES):
            findings.append(
                Finding(
                    path.name,
                    "banned suffix in filename (-pro/-master/-expert)",
                )
            )

        is_alias = "deprecated alias profile" in text.lower()
        if is_alias:
            alias_count += 1
            cp = re.search(
                r"Canonical profile:\s*\[([^\]]+)\]\(([^)]+)\)",
                text,
            )
            if not cp:
                findings.append(Finding(path.name, "missing canonical profile link"))
            else:
                target = cp.group(2).strip()
                target_path = (path.parent / target).resolve()
                if not target_path.exists():
                    findings.append(
                        Finding(path.name, f"canonical target not found: {target}")
                    )

            if not re.search(r"Planned removal date:\s*\d{4}-\d{2}-\d{2}\.", text):
                findings.append(Finding(path.name, "missing planned removal date"))
        else:
            canonical_count += 1
            if args.strict and path.stem.startswith("sp-"):
                if "Boundary note (" not in text:
                    findings.append(Finding(path.name, "missing Boundary note section"))
                if "Operating modes:" not in text:
                    findings.append(
                        Finding(path.name, "missing Operating modes section")
                    )

        # Basic naming policy check for specialist profiles
        if path.stem.startswith("sp-") and path.stem not in names:
            findings.append(Finding(path.name, "unexpected missing stem in file set"))

    mode = "strict" if args.strict else "default"
    print(f"mode={mode}")
    print(f"checked_files={len(files)}")
    print(f"canonical_profiles={canonical_count}")
    print(f"alias_profiles={alias_count}")
    print(f"findings={len(findings)}")

    for finding in findings:
        print(f"- {finding.file}: {finding.message}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
