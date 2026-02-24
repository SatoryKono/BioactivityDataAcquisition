#!/usr/bin/env python3
"""Validate that docs/00-project/index.md Current Version matches pyproject.toml."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
DOC_INDEX_PATH = REPO_ROOT / "docs" / "00-project" / "index.md"
VERSION_PATTERN = re.compile(
    r"\*\*v(?P<version>\d+\.\d+\.\d+)\*\*\s*\((?P<date>\d{4}-\d{2}-\d{2})\)"
)


def get_pyproject_version(pyproject_path: Path) -> str:
    """Read project version from pyproject.toml."""
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def get_docs_version(doc_index_path: Path) -> tuple[str, str]:
    """Extract current version and release date from docs/00-project/index.md."""
    content = doc_index_path.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(content)
    if match is None:
        raise ValueError(
            "Could not find Current Version entry in docs/00-project/index.md. "
            "Expected format: **vX.Y.Z** (YYYY-MM-DD)."
        )
    return match.group("version"), match.group("date")


def main() -> int:
    """Run version consistency check."""
    pyproject_version = get_pyproject_version(PYPROJECT_PATH)
    docs_version, release_date = get_docs_version(DOC_INDEX_PATH)

    if pyproject_version != docs_version:
        sys.stderr.write(
            "Version mismatch:\n"
            f"  pyproject.toml: {pyproject_version}\n"
            f"  docs/00-project/index.md: {docs_version} ({release_date})\n"
        )
        return 1

    sys.stdout.write(
        "Version sync OK: "
        f"pyproject.toml and docs/00-project/index.md are both {pyproject_version} "
        f"(release date: {release_date}).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
