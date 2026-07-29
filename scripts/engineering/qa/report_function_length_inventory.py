#!/usr/bin/env python3
"""Generate a report-only inventory of functions approaching the length limit.

This utility scans Python source files, reports functions within a configurable
warning band below the hard architecture threshold, and optionally writes JSON
and Markdown artifacts. It never fails because of near-threshold findings; it
only fails on invalid arguments or unreadable output paths.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FunctionLengthEntry:
    """One function found inside the near-threshold warning band."""

    path: str
    symbol: str
    line: int
    length: int


def _iter_python_files(src_root: Path) -> Iterable[Path]:
    """Yield Python source files beneath the requested source root."""
    yield from sorted(
        path for path in src_root.rglob("*.py") if not path.name.startswith("__")
    )


def _scan_near_threshold_functions(
    *,
    src_root: Path,
    warn_threshold: int,
    max_lines: int,
) -> list[FunctionLengthEntry]:
    """Collect functions within the inclusive warning band."""
    results: list[FunctionLengthEntry] = []

    for py_file in _iter_python_files(src_root):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            end_line = node.end_lineno or node.lineno
            func_lines = end_line - node.lineno + 1
            if warn_threshold <= func_lines <= max_lines:
                results.append(
                    FunctionLengthEntry(
                        path=py_file.as_posix(),
                        symbol=node.name,
                        line=node.lineno,
                        length=func_lines,
                    )
                )

    return sorted(
        results,
        key=lambda entry: (-entry.length, entry.path, entry.line, entry.symbol),
    )


def _build_payload(
    *,
    src_root: Path,
    warn_threshold: int,
    max_lines: int,
    entries: list[FunctionLengthEntry],
) -> dict[str, object]:
    """Build a machine-readable payload for the current scan."""
    return {
        "mode": "report-only",
        "src_root": src_root.as_posix(),
        "warn_threshold": warn_threshold,
        "max_lines": max_lines,
        "near_threshold_count": len(entries),
        "entries": [asdict(entry) for entry in entries],
    }


def _render_markdown(
    *,
    src_root: Path,
    warn_threshold: int,
    max_lines: int,
    entries: list[FunctionLengthEntry],
    limit: int,
) -> str:
    """Render a human-readable Markdown summary."""
    lines = [
        "# Function Length Inventory",
        "",
        "- mode: report-only",
        f"- source_root: `{src_root.as_posix()}`",
        f"- warning_band: `{warn_threshold}-{max_lines}` LOC",
        f"- near_threshold_count: `{len(entries)}`",
        "",
    ]

    if not entries:
        lines.extend(
            [
                "No functions currently sit inside the warning band.",
                "",
                "The hard gate remains enforced separately in `tests/architecture/test_code_metrics.py`.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Top Entries",
            "",
        ]
    )
    for entry in entries[:limit]:
        lines.append(
            f"- `{entry.path}:{entry.line}` `{entry.symbol}()` is `{entry.length}` LOC"
        )

    if len(entries) > limit:
        lines.extend(
            [
                "",
                f"Showing top `{limit}` entries out of `{len(entries)}`.",
            ]
        )

    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    """Write UTF-8 text, creating parent directories as needed."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    path = resolve_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        content, encoding="utf-8"
    )  # NOSONAR - confined by resolve_output_path


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src-root",
        type=Path,
        default=Path("src/bioetl"),
        help="Source root to scan (default: src/bioetl)",
    )
    parser.add_argument(
        "--warn-threshold",
        type=int,
        default=80,
        help="Inclusive lower bound for the warning band (default: 80)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=100,
        help="Inclusive upper bound for the warning band (default: 100)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum entries to render in Markdown/stdout (default: 20)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for machine-readable JSON output",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional path for Markdown output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the report-only scan."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.warn_threshold > args.max_lines:
        parser.error("--warn-threshold must be <= --max-lines")

    entries = _scan_near_threshold_functions(
        src_root=args.src_root,
        warn_threshold=args.warn_threshold,
        max_lines=args.max_lines,
    )
    payload = _build_payload(
        src_root=args.src_root,
        warn_threshold=args.warn_threshold,
        max_lines=args.max_lines,
        entries=entries,
    )
    markdown = _render_markdown(
        src_root=args.src_root,
        warn_threshold=args.warn_threshold,
        max_lines=args.max_lines,
        entries=entries,
        limit=args.limit,
    )

    if args.json_out is not None:
        _write_text(args.json_out, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown_out is not None:
        _write_text(args.markdown_out, markdown + "\n")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
