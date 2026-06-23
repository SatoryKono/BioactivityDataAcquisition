# ruff: noqa: T201
#!/usr/bin/env python3
"""Validate specialist agent profiles in the docs mirror.

Scope: docs/00-project/ai/agents/agents/sp-*.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

AGENTS_DIR = Path("docs/00-project/ai/agents/agents")
BANNED_SUFFIXES = ("-pro", "-master", "-expert")


@dataclass
class Finding:
    file: str
    message: str


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end_index = next(
            idx for idx, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        return None
    frontmatter: dict[str, str] = {}
    for line in lines[1:end_index]:
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


def _check_frontmatter_name(
    path: Path,
    frontmatter: dict[str, str],
) -> list[Finding]:
    """Validate frontmatter name consistency with filename."""
    name = frontmatter.get("name", "")
    if name == path.stem:
        return []
    return [
        Finding(
            path.name,
            f"frontmatter name mismatch: {name!r} != {path.stem!r}",
        )
    ]


def _check_alias_profile(path: Path, text: str) -> list[Finding]:
    """Validate deprecated alias profile metadata."""
    findings: list[Finding] = []
    canonical_profile = re.search(
        r"Canonical profile:\s*\[([^\]]+)\]\(([^)]+)\)",
        text,
    )
    if not canonical_profile:
        findings.append(Finding(path.name, "missing canonical profile link"))
    else:
        target = canonical_profile.group(2).strip()
        target_path = (path.parent / target).resolve()
        if not target_path.exists():
            findings.append(Finding(path.name, f"canonical target not found: {target}"))
    if not re.search(r"Planned removal date:\s*\d{4}-\d{2}-\d{2}\.", text):
        findings.append(Finding(path.name, "missing planned removal date"))
    return findings


def _check_canonical_profile(path: Path, text: str, *, strict: bool) -> list[Finding]:
    """Validate canonical profile sections in strict mode."""
    if not strict or not path.stem.startswith("sp-"):
        return []
    findings: list[Finding] = []
    if "Boundary note (" not in text:
        findings.append(Finding(path.name, "missing Boundary note section"))
    if "Operating modes:" not in text:
        findings.append(Finding(path.name, "missing Operating modes section"))
    return findings


def _analyze_agent_file(path: Path, *, strict: bool) -> tuple[list[Finding], bool]:
    """Analyze a single agent profile file and return findings plus alias flag."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        return [Finding(path.name, "missing frontmatter")], False

    findings: list[Finding] = []
    findings.extend(_check_frontmatter_name(path, frontmatter))
    if path.stem.endswith(BANNED_SUFFIXES):
        findings.append(
            Finding(
                path.name,
                "banned suffix in filename (-pro/-master/-expert)",
            )
        )
    is_alias = "deprecated alias profile" in text.lower()
    if is_alias:
        findings.extend(_check_alias_profile(path, text))
    else:
        findings.extend(_check_canonical_profile(path, text, strict=strict))
    return findings, is_alias


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    findings: list[Finding] = []

    if not AGENTS_DIR.exists():
        print(f"ERROR: directory not found: {AGENTS_DIR}")
        return 2

    files = sorted(AGENTS_DIR.glob("sp-*.md"))

    alias_count = 0
    canonical_count = 0

    for path in files:
        path_findings, is_alias = _analyze_agent_file(path, strict=args.strict)
        findings.extend(path_findings)
        if is_alias:
            alias_count += 1
        else:
            canonical_count += 1

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
