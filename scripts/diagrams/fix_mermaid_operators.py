#!/usr/bin/env python3
"""Validate/fix Mermaid thick-arrow operators in class/sequence diagrams.

This codemod targets parse-fragile operators in:
- classDiagram
- sequenceDiagram

Rewrites:
- ``==>``  -> ``-->``
- ``==>>`` -> ``-->>``

Usage:
    python scripts/diagrams/fix_mermaid_operators.py --check
    python scripts/diagrams/fix_mermaid_operators.py --fix
    python scripts/diagrams/fix_mermaid_operators.py --fix --dry-run
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
for bootstrap_path in (REPO_ROOT, SCRIPT_DIR):
    bootstrap_path_str = str(bootstrap_path)
    if bootstrap_path_str not in sys.path:
        sys.path.insert(0, bootstrap_path_str)

try:
    from .diagram_paths import DIAGRAM_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import DIAGRAM_ROOT

SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
TARGET_DIAGRAM_TYPES = {"classdiagram", "sequencediagram"}
DEFAULT_SCOPE = DIAGRAM_ROOT


@dataclass(frozen=True)
class OperatorIssue:
    """A single invalid operator occurrence."""

    line_no: int
    operator: str
    line: str


@dataclass
class FileCheckResult:
    """Operator validation result for one file."""

    path: Path
    diagram_type: str | None
    issues: list[OperatorIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ValidatedRepoPath:
    """Repository-scoped path validated before filesystem access."""

    resolved_path: Path

    @property
    def repo_relative_path(self) -> Path:
        return self.resolved_path.relative_to(_repo_root().resolve())


def _repo_root() -> Path:
    return REPO_ROOT


def _ensure_repo_path(path: Path) -> Path:
    root = _repo_root().resolve()
    resolved_path = path.resolve()
    if root != resolved_path and root not in resolved_path.parents:
        raise ValueError(f"refusing to process path outside {root}: {resolved_path}")
    return resolved_path


def _repo_relative_path(path: Path) -> Path:
    safe_path = _ensure_repo_path(path)
    return safe_path.relative_to(_repo_root().resolve())


def _normalize_repo_relative_path(path: Path) -> Path:
    """Normalize and validate a repository-relative path."""
    if path.is_absolute():
        raise ValueError(f"expected repository-relative path, got absolute path: {path}")

    normalized_parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"refusing to process parent traversal path: {path}")
        normalized_parts.append(part)

    if not normalized_parts:
        raise ValueError("refusing to process empty repository-relative path")
    return Path(*normalized_parts)


def _repo_path(relative_path: Path) -> Path:
    safe_relative_path = _normalize_repo_relative_path(relative_path)
    return _repo_root().joinpath(*safe_relative_path.parts)


def _resolve_repo_file_path(path: Path) -> ValidatedRepoPath:
    if path.is_absolute():
        return ValidatedRepoPath(_ensure_repo_path(path))
    return ValidatedRepoPath(_ensure_repo_path(_repo_path(path)))


def _read_validated_repo_text(path: ValidatedRepoPath) -> str:
    return path.resolved_path.read_text(encoding="utf-8")


def _write_validated_repo_text(path: ValidatedRepoPath, content: str) -> None:
    """Write content only to a previously validated repository path."""
    if path.resolved_path.is_dir():
        raise ValueError(f"refusing to write to directory path: {path.resolved_path}")
    path.resolved_path.write_text(content, encoding="utf-8")


def _display_path(path: Path) -> str:
    root = _repo_root()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def detect_diagram_type(lines: list[str]) -> str | None:
    """Return the Mermaid diagram type of a file, if detectable."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("%%"):
            continue
        lower = stripped.lower()
        if lower.startswith("classdiagram"):
            return "classdiagram"
        if lower.startswith("sequencediagram"):
            return "sequencediagram"
        return None
    return None


def _iter_source_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = _resolve_repo_file_path(raw)
        resolved_path = path.resolved_path
        if resolved_path.is_file():
            if resolved_path.suffix in SUPPORTED_SUFFIXES:
                files.append(path.repo_relative_path)
            continue
        if resolved_path.is_dir():
            for suffix in SUPPORTED_SUFFIXES:
                files.extend(
                    _repo_relative_path(candidate)
                    for candidate in resolved_path.rglob(f"*{suffix}")
                )
    return sorted(set(files))


def _collect_issues(lines: list[str]) -> list[OperatorIssue]:
    issues: list[OperatorIssue] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("%%"):
            continue
        count_thick_response = line.count("==>>")
        if count_thick_response > 0:
            for _ in range(count_thick_response):
                issues.append(
                    OperatorIssue(line_no=idx, operator="==>>", line=line.rstrip())
                )

        # Exclude already-counted ==>> chunks from ==> detection.
        count_thick_link = line.replace("==>>", "").count("==>")
        if count_thick_link > 0:
            for _ in range(count_thick_link):
                issues.append(
                    OperatorIssue(line_no=idx, operator="==>", line=line.rstrip())
                )
    return issues


def check_file(path: Path) -> FileCheckResult:
    """Validate one Mermaid file for unsupported operators in target types."""
    safe_path = _resolve_repo_file_path(path)
    lines = _read_validated_repo_text(safe_path).splitlines()
    diagram_type = detect_diagram_type(lines)
    if diagram_type not in TARGET_DIAGRAM_TYPES:
        return FileCheckResult(path=safe_path.resolved_path, diagram_type=diagram_type)
    return FileCheckResult(
        path=safe_path.resolved_path,
        diagram_type=diagram_type,
        issues=_collect_issues(lines),
    )


def fix_file(path: Path, *, dry_run: bool) -> int:
    """Rewrite a Mermaid file in-place and return replacement count."""
    safe_path = _resolve_repo_file_path(path)
    lines = _read_validated_repo_text(safe_path).splitlines()
    if detect_diagram_type(lines) not in TARGET_DIAGRAM_TYPES:
        return 0

    replaced = 0
    fixed_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("%%"):
            fixed_lines.append(line)
            continue
        replaced += line.count("==>>")
        replaced += line.replace("==>>", "").count("==>")
        fixed_lines.append(line.replace("==>>", "-->>").replace("==>", "-->"))

    if replaced > 0 and not dry_run:
        _write_validated_repo_text(safe_path, "\n".join(fixed_lines) + "\n")

    return replaced


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check/fix Mermaid thick-arrow operators in classDiagram and "
            "sequenceDiagram files."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCOPE],
        help="Files or directories to process (default: docs/02-architecture/diagrams)",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--check",
        action="store_true",
        help="Report invalid operators and exit non-zero if any are found (default mode).",
    )
    mode_group.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite invalid operators in-place.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --fix: print planned changes without writing files.",
    )
    return parser


def _checked_targets(results: list[FileCheckResult]) -> list[FileCheckResult]:
    return [
        result for result in results if result.diagram_type in TARGET_DIAGRAM_TYPES
    ]


def _summary_line(**fields: object) -> str:
    return "Summary: " + " ".join(f"{name}={value}" for name, value in fields.items())


def _report_offending_results(offending: list[FileCheckResult]) -> None:
    for result in offending:
        print(f"[INVALID] {_display_path(result.path)}")
        for issue in result.issues:
            print(f"  L{issue.line_no}: {issue.operator} :: {issue.line}")


def _run_check_mode(
    source_files: list[Path],
    checked_targets: list[FileCheckResult],
    offending: list[FileCheckResult],
) -> int:
    _report_offending_results(offending)
    print(
        _summary_line(
            files_scanned=len(source_files),
            target_files=len(checked_targets),
            files_with_issues=len(offending),
            issues=sum(len(result.issues) for result in offending),
        )
    )
    return 1 if offending else 0


def _apply_fixes(
    offending: list[FileCheckResult], *, dry_run: bool
) -> tuple[int, int]:
    changed_files = 0
    replacements = 0
    for result in offending:
        replaced = fix_file(result.path, dry_run=dry_run)
        replacements += replaced
        if replaced <= 0:
            continue
        changed_files += 1
        action = "WOULD FIX" if dry_run else "FIXED"
        print(f"[{action}] {_display_path(result.path)} replacements={replaced}")
    return changed_files, replacements


def _run_fix_mode(
    source_files: list[Path],
    checked_targets: list[FileCheckResult],
    offending: list[FileCheckResult],
    *,
    dry_run: bool,
) -> int:
    changed_files, replacements = _apply_fixes(offending, dry_run=dry_run)
    print(
        _summary_line(
            files_scanned=len(source_files),
            target_files=len(checked_targets),
            files_with_issues=len(offending),
            changed_files=changed_files,
            replacements=replacements,
            dry_run=dry_run,
        )
    )
    if dry_run and offending:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dry_run and not args.fix:
        parser.error("--dry-run can only be used together with --fix")

    check_mode = args.check or not args.fix
    source_files = _iter_source_files(args.paths)
    results = [check_file(path) for path in source_files]
    offending = [result for result in results if result.issues]
    checked_targets = _checked_targets(results)

    if check_mode:
        return _run_check_mode(source_files, checked_targets, offending)

    return _run_fix_mode(
        source_files,
        checked_targets,
        offending,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
