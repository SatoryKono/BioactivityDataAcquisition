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


def extract_docs_version(content: str) -> str:
    match = re.search(r"\*\*v(\d+\.\d+\.\d+)\*\*", content)
    if match is None:
        raise VersionCheckError(
            "Could not find Current Version in docs/00-project/index.md"
        )
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
    docs_version = extract_docs_version(DOC_INDEX_PATH.read_text(encoding="utf-8"))
    changelog_version = extract_latest_changelog_version(
        CHANGELOG_PATH.read_text(encoding="utf-8")
    )

    versions: dict[str, str] = {
        "pyproject.toml": pyproject_version,
        "src/bioetl/__init__.py": init_version,
        "docs/00-project/index.md": docs_version,
        "CHANGELOG.md (latest release)": changelog_version,
    }

    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        details = "\n".join(f"- {name}: {value}" for name, value in versions.items())
        sys.stderr.write("Version mismatch detected:\n" + details + "\n")
        return 1

    resolved_version = unique_versions.pop()
    sys.stdout.write(f"Version consistency check passed: {resolved_version}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
