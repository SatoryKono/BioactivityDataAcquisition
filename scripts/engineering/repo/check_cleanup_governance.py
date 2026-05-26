#!/usr/bin/env python3
"""Guard active docs and scripts against unsafe broad cleanup instructions."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

CONFIG_PATH = Path("configs/quality/broad_cleanup_guardrails.yaml")
SCAN_ROOTS: tuple[str, ...] = (
    ".github",
    "docs",
    "scripts",
    "README.md",
    "Makefile",
    "pyproject.toml",
)
SKIPPED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".venv-docs",
        ".venv-win",
        ".venv-win-corrupt",
        "data",
        "docs/99-archive",
        "docs/reports",
        "reports",
        "tests/fixtures",
        "venv",
    }
)
SCANNED_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".py", ".sh", ".ps1", ".yml", ".yaml", ".toml", ".txt"}
)

FORBIDDEN_LITERAL_PATTERNS: tuple[str, ...] = (
    "git clean -fdx",
    "git clean -xdf",
    "git clean -dfx",
    "git clean -fxd",
)
FORBIDDEN_REGEX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\brm\s+-rf\s+(?:\.?/)?"
        r"(?:data|reports|docs/reports|docs/99-archive|tests/fixtures)"
        r"(?:/|\s|$)"
    ),
)


@dataclass(frozen=True)
class BroadCleanupViolation:
    path: str
    line_number: int
    pattern: str
    line: str


def _discover_repo_root(start: Path) -> Path:
    current = start.resolve()
    search_root = current if current.is_dir() else current.parent
    for candidate in (search_root, *search_root.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"Could not locate repository root from {start}")


def _load_yaml_object(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a YAML object")
    return payload


def _load_allowed_examples(repo_root: Path) -> dict[str, tuple[str, ...]]:
    payload = _load_yaml_object(repo_root / CONFIG_PATH)
    entries = payload.get("allowed_broad_cleanup_examples")
    if not isinstance(entries, list):
        raise RuntimeError("allowed_broad_cleanup_examples must be a list")

    allowed: dict[str, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("allowed broad cleanup entries must be objects")
        path = entry.get("path")
        patterns = entry.get("patterns")
        if not isinstance(path, str) or not path:
            raise RuntimeError("allowed broad cleanup entry path must be non-empty")
        if not isinstance(patterns, list) or not patterns:
            raise RuntimeError(f"{path}: patterns must be a non-empty list")
        allowed[path] = [pattern for pattern in patterns if isinstance(pattern, str)]
        if len(allowed[path]) != len(patterns):
            raise RuntimeError(f"{path}: patterns must be strings")
    return {path: tuple(patterns) for path, patterns in allowed.items()}


def _is_skipped_dir(relative_path: Path) -> bool:
    text = relative_path.as_posix()
    return any(
        text == skipped or text.startswith(f"{skipped}/") for skipped in SKIPPED_DIRS
    )


def _is_scanned_file(candidate: Path, *, repo_root: Path) -> bool:
    relative = candidate.relative_to(repo_root)
    if _is_skipped_dir(relative) or _is_skipped_dir(relative.parent):
        return False
    try:
        if candidate.is_dir():
            return False
    except OSError:
        return False
    return candidate.suffix in SCANNED_SUFFIXES


def _scanned_files_for_root(path: Path, *, repo_root: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path]
    return [
        candidate
        for candidate in path.rglob("*")
        if _is_scanned_file(candidate, repo_root=repo_root)
    ]


def _iter_scanned_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        files.extend(_scanned_files_for_root(repo_root / root, repo_root=repo_root))
    return sorted(files)


def _allowed_on_line(
    *,
    relative_path: str,
    line: str,
    allowed_examples: dict[str, tuple[str, ...]],
) -> bool:
    return any(pattern in line for pattern in allowed_examples.get(relative_path, ()))


def _line_literal_violation(line: str) -> str | None:
    return next(
        (pattern for pattern in FORBIDDEN_LITERAL_PATTERNS if pattern in line), None
    )


def _line_regex_violation(line: str) -> str | None:
    for pattern in FORBIDDEN_REGEX_PATTERNS:
        if pattern.search(line):
            return pattern.pattern
    return None


def _line_violation(
    *,
    relative_path: str,
    line_number: int,
    line: str,
    allowed_examples: dict[str, tuple[str, ...]],
) -> BroadCleanupViolation | None:
    if _allowed_on_line(
        relative_path=relative_path,
        line=line,
        allowed_examples=allowed_examples,
    ):
        return None
    pattern = _line_literal_violation(line) or _line_regex_violation(line)
    if pattern is None:
        return None
    return BroadCleanupViolation(
        path=relative_path,
        line_number=line_number,
        pattern=pattern,
        line=line.strip(),
    )


def _file_broad_cleanup_violations(
    file_path: Path,
    *,
    repo_root: Path,
    allowed_examples: dict[str, tuple[str, ...]],
) -> list[BroadCleanupViolation]:
    relative_path = file_path.relative_to(repo_root).as_posix()
    violations: list[BroadCleanupViolation] = []
    for line_number, line in enumerate(
        file_path.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        violation = _line_violation(
            relative_path=relative_path,
            line_number=line_number,
            line=line,
            allowed_examples=allowed_examples,
        )
        if violation is not None:
            violations.append(violation)
    return violations


def collect_broad_cleanup_violations(repo_root: Path) -> list[BroadCleanupViolation]:
    allowed_examples = _load_allowed_examples(repo_root)
    violations: list[BroadCleanupViolation] = []
    for file_path in _iter_scanned_files(repo_root):
        violations.extend(
            _file_broad_cleanup_violations(
                file_path,
                repo_root=repo_root,
                allowed_examples=allowed_examples,
            )
        )
    return violations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check active docs/scripts for unsafe broad cleanup guidance.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Path inside the repository to inspect",
    )
    return parser.parse_args()


def _load_violations_from_args(args: argparse.Namespace) -> list[BroadCleanupViolation]:
    repo_root = _discover_repo_root(args.path)
    return collect_broad_cleanup_violations(repo_root)


def _report_broad_cleanup_violations(violations: list[BroadCleanupViolation]) -> int:
    if not violations:
        sys.stdout.write("OK: cleanup governance guardrails passed.\n")
        return 0
    sys.stderr.write("ERROR: broad cleanup instructions are not allowed:\n")
    for violation in violations:
        sys.stderr.write(
            f"  - {violation.path}:{violation.line_number}: "
            f"{violation.pattern} :: {violation.line}\n"
        )
    return 1


def main() -> int:
    args = parse_args()
    try:
        violations = _load_violations_from_args(args)
    except (OSError, RuntimeError, yaml.YAMLError) as exc:
        sys.stderr.write(f"ERROR: cleanup governance check failed: {exc}\n")
        return 2
    return _report_broad_cleanup_violations(violations)


if __name__ == "__main__":
    raise SystemExit(main())
