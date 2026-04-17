#!/usr/bin/env python3
"""Validate tracked data/ files against allowlist and size limits."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class DataRule:
    pattern: str
    max_bytes: int | None
    category: str


MIB: int = 1024 * 1024
RULES: tuple[DataRule, ...] = (
    DataRule(pattern="data/input/*.csv", max_bytes=30 * MIB, category="input-fixture"),
    DataRule(
        pattern="data/input/**/*.csv", max_bytes=30 * MIB, category="input-fixture"
    ),
    DataRule(
        pattern="data/input/reference/**/*.csv",
        max_bytes=5 * MIB,
        category="reference-fixture",
    ),
    DataRule(
        pattern="data/fixtures/**/*.csv", max_bytes=10 * MIB, category="test-fixture"
    ),
    DataRule(
        pattern="data/fixtures/**/*.json", max_bytes=10 * MIB, category="test-fixture"
    ),
    DataRule(
        pattern="data/fixtures/**/*.jsonl", max_bytes=10 * MIB, category="test-fixture"
    ),
    DataRule(
        pattern="data/golden/**/*.csv", max_bytes=20 * MIB, category="golden-data"
    ),
    DataRule(
        pattern="data/golden/**/*.json", max_bytes=20 * MIB, category="golden-data"
    ),
    DataRule(
        pattern="data/golden/**/*.jsonl", max_bytes=20 * MIB, category="golden-data"
    ),
    DataRule(pattern="data/**/.gitkeep", max_bytes=1024, category="directory-marker"),
    DataRule(pattern="data/**/*.md", max_bytes=1 * MIB, category="documentation"),
)


def _iter_tracked_data_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(  # nosec B603
        ["git", "ls-files", "-z", "data"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=False,
    )
    tracked_paths = completed.stdout.decode("utf-8", errors="replace").split("\0")
    files: list[Path] = []
    for raw_path in tracked_paths:
        if not raw_path:
            continue
        path = repo_root / raw_path
        if path.is_file():
            files.append(path)
    return sorted(files)


def _match_rule(relative_path: PurePosixPath) -> DataRule | None:
    for rule in RULES:
        if relative_path.match(rule.pattern):
            return rule
    return None


def validate_data_dir(repo_root: Path) -> int:
    violations: list[str] = []
    validated_count = 0

    try:
        tracked_files = _iter_tracked_data_files(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"❌ Failed to collect tracked data files: {exc}\n")
        return 2

    for file_path in tracked_files:
        relative = PurePosixPath(file_path.relative_to(repo_root).as_posix())
        rule = _match_rule(relative)
        if rule is None:
            violations.append(f"{relative}: no allowlist rule")
            continue

        size_bytes = file_path.stat().st_size
        if rule.max_bytes is not None and size_bytes > rule.max_bytes:
            violations.append(
                f"{relative}: {size_bytes} bytes exceeds limit {rule.max_bytes} ({rule.category})"
            )
            continue

        validated_count += 1

    if violations:
        sys.stderr.write("❌ data/ policy validation failed:\n")
        for violation in violations:
            sys.stderr.write(f"  - {violation}\n")
        sys.stderr.write(
            "\nMove temporary/heavy local artifacts to data/local/ or tmp/ and keep only allowlisted data in Git.\n"
        )
        return 1

    sys.stdout.write(
        f"✅ data/ policy validation passed ({validated_count} tracked files checked).\n"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return validate_data_dir(args.repo_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
