#!/usr/bin/env python3
"""Lightweight consistency check for project version metadata."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYPROJECT_PATH = ROOT / "pyproject.toml"
INIT_PATH = ROOT / "src/bioetl/__init__.py"
DOC_INDEX_PATH = ROOT / "docs/00-project/index.md"
RULES_PATH = ROOT / "docs/00-project/RULES.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


class VersionCheckError(ValueError):
    """Raised when a version field cannot be parsed or mismatches."""


def extract_pyproject_version(content: str) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match is None:
        raise VersionCheckError("Could not find version in pyproject.toml")
    return match.group(1)


def extract_init_version(content: str) -> str:
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match is None:
        raise VersionCheckError("Could not find __version__ in src/bioetl/__init__.py")
    return match.group(1)


def extract_docs_governance_version(content: str) -> str:
    """Extract the RULES governance baseline advertised by the docs index."""
    match = re.search(
        r"^## Current Version\s+^\*\*v(\d+\.\d+\.\d+)\*\*"
        r"\s+\(governance baseline",
        content,
        re.MULTILINE,
    )
    if match is None:
        raise VersionCheckError(
            "Could not find governance baseline in docs/00-project/index.md"
        )
    return match.group(1)


def extract_rules_version(content: str) -> str:
    """Extract the governance version from the canonical RULES header."""
    match = re.search(r"^Version:\s*(\d+\.\d+\.\d+)\s*$", content, re.MULTILINE)
    if match is None:
        raise VersionCheckError("Could not find Version header in RULES.md")
    return match.group(1)


def extract_latest_changelog_version(content: str) -> str:
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\] - ", content, re.MULTILINE)
    if match is None:
        raise VersionCheckError("Could not find latest release header in CHANGELOG.md")
    return match.group(1)


def main() -> int:
    pyproject_version = extract_pyproject_version(
        PYPROJECT_PATH.read_text(encoding="utf-8")
    )
    init_version = extract_init_version(INIT_PATH.read_text(encoding="utf-8"))
    docs_governance_version = extract_docs_governance_version(
        DOC_INDEX_PATH.read_text(encoding="utf-8")
    )
    rules_version = extract_rules_version(RULES_PATH.read_text(encoding="utf-8"))
    changelog_version = extract_latest_changelog_version(
        CHANGELOG_PATH.read_text(encoding="utf-8")
    )

    release_versions: dict[str, str] = {
        "pyproject.toml": pyproject_version,
        "src/bioetl/__init__.py": init_version,
        "CHANGELOG.md (latest release)": changelog_version,
    }

    unique_release_versions = set(release_versions.values())
    if len(unique_release_versions) != 1:
        details = "\n".join(
            f"- {name}: {value}" for name, value in release_versions.items()
        )
        sys.stderr.write("Release version mismatch detected:\n" + details + "\n")
        return 1

    if docs_governance_version != rules_version:
        sys.stderr.write(
            "Governance version mismatch detected:\n"
            f"- docs/00-project/index.md: {docs_governance_version}\n"
            f"- docs/00-project/RULES.md: {rules_version}\n"
        )
        return 1

    resolved_release_version = unique_release_versions.pop()
    sys.stdout.write(
        "Version consistency check passed: "
        f"release={resolved_release_version}, governance={rules_version}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
