#!/usr/bin/env python3
"""lint_config_paths.py - Validate canonical config path references.

Ensures that configuration files and documentation use the canonical
directory names for DQ and filter configs:

  - dq_config_file must reference `quality/` (not legacy `dq/`)
  - filter_config_file must reference `filters/` (not legacy `filter/`)

Legacy paths `../../dq/` and `../../filter/` were renamed to
`../../quality/` and `../../filters/` respectively.

Usage:
    # Check all config and doc files (default)
    python scripts/lint_config_paths.py

    # Check specific path
    python scripts/lint_config_paths.py configs/

    # Exit code: 0 = clean, 1 = violations found

Pre-commit hook integration:
    See .pre-commit-config.yaml `lint-config-paths` hook.

References:
    - ADR-027: DQ Rules Externalization
    - ADR-028: Filter Rules Externalization
    - ADR-029: Convention-based Path Resolution
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Patterns that indicate legacy (incorrect) paths.
# Each tuple: (regex-free substring to detect, canonical replacement, description)
LEGACY_PATTERNS: list[tuple[str, str, str]] = [
    ("../../dq/", "../../quality/", "Legacy DQ path: use 'quality' instead of 'dq'"),
    (
        "../../filter/",
        "../../filters/",
        "Legacy filter path: use 'filters' instead of 'filter'",
    ),
]

# Directories to skip entirely
SKIP_DIRS = frozenset(
    {
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        "99-archive",
    }
)

# File extensions to scan
SCAN_EXTENSIONS = frozenset(
    {".yaml", ".yml", ".json", ".py", ".md", ".csv", ".rst", ".toml"}
)


def _should_skip(path: Path) -> bool:
    """Return True if path should be excluded from scanning."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def _scan_file(filepath: Path) -> list[tuple[int, str, str, str]]:
    """Scan a single file for legacy config path references.

    Returns list of (line_number, line_content, legacy_pattern, canonical).
    """
    hits: list[tuple[int, str, str, str]] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits

    for line_no, line in enumerate(text.splitlines(), start=1):
        for legacy, canonical, _desc in LEGACY_PATTERNS:
            if legacy in line:
                hits.append((line_no, line.rstrip(), legacy, canonical))
    return hits


def _safe_is_file(path: Path) -> bool:
    """Return False when filesystem metadata cannot be read for a path."""
    try:
        return path.is_file()
    except OSError:
        return False


def scan_tree(root: Path) -> dict[Path, list[tuple[int, str, str, str]]]:
    """Walk the tree under *root* and collect all violations."""
    results: dict[Path, list[tuple[int, str, str, str]]] = {}

    if _safe_is_file(root):
        hits = _scan_file(root)
        if hits:
            results[root] = hits
        return results

    for path in sorted(root.rglob("*")):
        if not _safe_is_file(path):
            continue
        if _should_skip(path):
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        hits = _scan_file(path)
        if hits:
            results[path] = hits

    return results


def _print_report(
    results: dict[Path, list[tuple[int, str, str, str]]],
) -> int:
    """Print human-readable report and return total violation count."""
    total = 0
    for filepath in sorted(results):
        hits = results[filepath]
        total += len(hits)
        rel = filepath.relative_to(PROJECT_ROOT)
        for line_no, line_content, legacy, canonical in hits:
            print(f"{rel}:{line_no}: {legacy!r} -> {canonical!r}")
            print(f"  | {line_content[:120]}")
    if total:
        print(f"\n{total} legacy config path reference(s) found.")
        print(
            "Replace '../../dq/' with '../../quality/' and '../../filter/' with '../../filters/'."
        )
    else:
        print("No legacy config path references found.")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint config files for legacy dq/filter path references.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[
            PROJECT_ROOT / "configs",
            PROJECT_ROOT / "src",
            PROJECT_ROOT / "docs",
        ],
        help="Paths to scan (default: configs/ src/ docs/)",
    )
    args = parser.parse_args()

    all_results: dict[Path, list[tuple[int, str, str, str]]] = {}
    for p in args.paths:
        target = p if p.is_absolute() else PROJECT_ROOT / p
        if not target.exists():
            print(f"Warning: {target} does not exist, skipping.", file=sys.stderr)
            continue
        all_results.update(scan_tree(target))

    total = _print_report(all_results)
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
