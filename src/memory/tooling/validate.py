"""Validate the baseline project-memory scaffold."""

from __future__ import annotations

import argparse

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
    return parser


def _format_issue(issue: ValidationIssue) -> dict[str, str]:
    return {"path": issue.path, "message": issue.message}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    issues = validate_memory_scaffold()

    if args.json:
        {
            "ok": not issues,
            "issues": [_format_issue(issue) for issue in issues],
        }
    elif issues:
        for _issue in issues:
            pass
    else:
        pass

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
