#!/usr/bin/env python3
"""Validate the first line of a commit message against BioETL policy."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CONVENTIONAL_HEADER_RE = re.compile(
    r"(?:feat|fix|refactor|docs|test|chore|perf|ci|build|style|revert)"
    r"(?:\([a-z0-9._/-]+\))?!?: [^\r\n]+"
)
MERGE_OR_REVERT_RE = re.compile(r"(?:Merge|Revert)[^\r\n]*")
MAX_CONVENTIONAL_HEADER_LENGTH = 100


def _read_header(commit_msg_path: Path) -> str:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    # Commit-msg hooks may pass .git/COMMIT_EDITMSG under the repo root.
    commit_msg_path = resolve_output_path(commit_msg_path, root=REPO_ROOT)
    lines = commit_msg_path.read_text(encoding="utf-8").splitlines()
    return lines[0] if lines else ""


def validate_commit_message_header(header: str) -> str | None:
    """Return an error message when the header violates policy."""
    if not header:
        return "Commit message is empty."

    if MERGE_OR_REVERT_RE.fullmatch(header):
        return None

    if len(header) > MAX_CONVENTIONAL_HEADER_LENGTH:
        return (
            "Conventional Commit header exceeds 100 characters: "
            f"{len(header)} > {MAX_CONVENTIONAL_HEADER_LENGTH}."
        )

    if CONVENTIONAL_HEADER_RE.fullmatch(header):
        return None

    return (
        "Commit message header must follow Conventional Commits "
        "(for example: `feat(hooks): install commit-msg hook`)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit_msg_path", type=Path)
    args = parser.parse_args(argv)

    header = _read_header(args.commit_msg_path)
    error = validate_commit_message_header(header)
    if error is None:
        return 0

    sys.stderr.write(f"{error}\nOffending header: {header!r}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
