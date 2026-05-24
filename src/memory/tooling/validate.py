"""Validate the baseline project-memory scaffold."""

from __future__ import annotations

import argparse
import json
from typing import Any

from memory.validation import ValidationIssue, validate_memory_scaffold


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate project-memory scaffold files and contracts."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit validation results as JSON.",
    )
    parser.add_argument(
        "--include-working-tree-junk",
        action="store_true",
        help="Also fail on untracked Python cache files below src/memory.",
    )
    parser.add_argument(
        "--include-all-episodic-notes",
        action="store_true",
        help="Validate the full episodic note history instead of the bounded fast-path scan.",
    )
    return parser


def _format_issue(issue: ValidationIssue) -> dict[str, str]:
    return {"path": issue.path, "message": issue.message}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    issues = validate_memory_scaffold(
        include_working_tree_junk=args.include_working_tree_junk,
        include_all_episodic_notes=args.include_all_episodic_notes,
    )

    if args.json:
        payload: dict[str, Any] = {
            "ok": not issues,
            "issues": [_format_issue(issue) for issue in issues],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif issues:
        print("Memory scaffold validation failed:")
        for issue in issues:
            print(f"- {issue.path}: {issue.message}")
    else:
        print("Memory scaffold validation passed.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
