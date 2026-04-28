#!/usr/bin/env python3
"""Deterministic repository cleanup for policy-approved local artifact families.

This tool intentionally does **not** perform broad repository cleanup anymore.
It reports tracked policy-violation candidates for manual review and can apply
deletion only for exact local artifact families outside blocked cleanup zones.

Usage:
    python scripts/ops/support/repo/cleanup_repository.py --dry-run
    python scripts/ops/support/repo/cleanup_repository.py --apply
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.engineering.repo._root_governance import (
    is_within_blocked_cleanup_zone,
    load_root_governance_policy,
)
from scripts.engineering.repo.audit_root_cleanliness import (
    _is_forbidden_tracked_artifact,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SAFE_LOCAL_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".benchmarks",
        ".coverage-sharded",
        ".eggs",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".python-user",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
    }
)
SAFE_LOCAL_FILE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("compiled", "*.pyc"),
    ("compiled", "*.pyo"),
    ("coverage", ".coverage"),
    ("coverage", ".coverage.*"),
    ("coverage", "coverage.xml"),
)
VENV_SEGMENTS: frozenset[str] = frozenset(
    {
        ".venv",
        ".venv-docs",
        ".venv-win",
        ".venv-win-corrupt",
        "venv",
    }
)


@dataclass(frozen=True)
class CleanupCandidate:
    path: Path
    category: str
    tracked: bool
    apply_allowed: bool
    reason: str

    @property
    def rel_path(self) -> str:
        return self.path.as_posix()


def _discover_repo_root(start: Path) -> Path:
    current = start.resolve()
    search_root = current if current.is_dir() else current.parent
    for candidate in (search_root, *search_root.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"Could not locate repository root from {start}")


def _run_git(repo_root: Path, *git_args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # nosec
        ["git", "-C", str(repo_root), *git_args],
        check=True,
        capture_output=True,
        text=False,
    )


def _tracked_paths(repo_root: Path) -> list[str]:
    completed = _run_git(repo_root, "ls-files", "-z")
    return [
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    ]


def _is_venv_path(path: Path) -> bool:
    return bool(VENV_SEGMENTS.intersection(path.parts))


def _is_blocked_path(path: Path, repo_root: Path, blocked_paths: frozenset[str]) -> bool:
    return is_within_blocked_cleanup_zone(path.relative_to(repo_root), blocked_paths)


def _iter_local_dir_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for name in SAFE_LOCAL_DIR_NAMES:
        for path in repo_root.rglob(name):
            if not path.is_dir() or _is_venv_path(path):
                continue
            if _is_blocked_path(path, repo_root, blocked_paths):
                continue
            candidates.append(
                CleanupCandidate(
                    path=path.relative_to(repo_root),
                    category="local_cache_dir",
                    tracked=False,
                    apply_allowed=True,
                    reason="exact local artifact family outside blocked cleanup zones",
                )
            )
    return candidates


def _iter_local_file_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for category, pattern in SAFE_LOCAL_FILE_PATTERNS:
        for path in repo_root.rglob(pattern):
            if not path.is_file() or _is_venv_path(path):
                continue
            if _is_blocked_path(path, repo_root, blocked_paths):
                continue
            candidates.append(
                CleanupCandidate(
                    path=path.relative_to(repo_root),
                    category=category,
                    tracked=False,
                    apply_allowed=True,
                    reason="exact local artifact file outside blocked cleanup zones",
                )
            )
    return candidates


def _tracked_policy_candidates(repo_root: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for tracked_path in _tracked_paths(repo_root):
        if not _is_forbidden_tracked_artifact(tracked_path):
            continue
        candidates.append(
            CleanupCandidate(
                path=Path(tracked_path),
                category="tracked_policy_review",
                tracked=True,
                apply_allowed=False,
                reason="tracked generated/runtime artifact requires explicit git review",
            )
        )
    return candidates


def _dedupe_candidates(candidates: list[CleanupCandidate]) -> list[CleanupCandidate]:
    deduped: dict[tuple[str, str], CleanupCandidate] = {}
    for candidate in candidates:
        deduped[(candidate.category, candidate.rel_path)] = candidate
    return sorted(deduped.values(), key=lambda candidate: (candidate.rel_path, candidate.category))


def collect_cleanup_candidates(
    repo_root: Path,
    *,
    include_cache: bool = True,
    include_temp: bool = True,
    include_root_review: bool = True,
) -> list[CleanupCandidate]:
    policy = load_root_governance_policy(repo_root)
    candidates: list[CleanupCandidate] = []

    if include_cache:
        candidates.extend(
            _iter_local_dir_candidates(
                repo_root,
                blocked_paths=policy.blocked_cleanup_paths,
            )
        )
    if include_temp:
        candidates.extend(
            _iter_local_file_candidates(
                repo_root,
                blocked_paths=policy.blocked_cleanup_paths,
            )
        )
    if include_root_review:
        candidates.extend(_tracked_policy_candidates(repo_root))

    return _dedupe_candidates(candidates)


def _apply_local_candidates(
    repo_root: Path,
    candidates: list[CleanupCandidate],
) -> tuple[list[CleanupCandidate], list[str]]:
    deleted: list[CleanupCandidate] = []
    errors: list[str] = []
    for candidate in candidates:
        target = repo_root / candidate.path
        if not candidate.apply_allowed:
            continue
        try:
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            deleted.append(candidate)
        except OSError as exc:
            errors.append(f"{candidate.rel_path}: {exc}")
    return deleted, errors


def _log_candidates(candidates: list[CleanupCandidate]) -> None:
    if not candidates:
        logger.info("No cleanup candidates found.")
        return

    categories: dict[str, list[CleanupCandidate]] = {}
    for candidate in candidates:
        categories.setdefault(candidate.category, []).append(candidate)

    for category in sorted(categories):
        logger.info("## %s (%d)", category.upper(), len(categories[category]))
        for candidate in categories[category]:
            mode = "apply" if candidate.apply_allowed else "review"
            logger.info("  [%s] %s", mode, candidate.rel_path)
            logger.info("      %s", candidate.reason)
        logger.info("")


def _log_apply_summary(
    *,
    deleted: list[CleanupCandidate],
    skipped_review: list[CleanupCandidate],
    errors: list[str],
) -> None:
    logger.info("=" * 70)
    logger.info("Deleted: %d", len(deleted))
    logger.info("Manual review candidates left untouched: %d", len(skipped_review))
    if errors:
        logger.info("Errors: %d", len(errors))
        for error in errors:
            logger.info("  %s", error)
    logger.info("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic BioETL repository cleanup",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the exact candidate set without deleting local artifacts",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete only exact local artifact candidates outside blocked zones",
    )
    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        help="Skip local cache directory candidates",
    )
    parser.add_argument(
        "--no-temp",
        action="store_false",
        dest="temp",
        help="Skip compiled/coverage local file candidates",
    )
    parser.add_argument(
        "--no-root",
        action="store_false",
        dest="root",
        help="Skip tracked policy review candidates",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Path inside the repository to inspect",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = _discover_repo_root(args.path)
    if args.dry_run and args.apply:
        logger.error("Use either --dry-run or --apply, not both.")
        return 2

    candidates = collect_cleanup_candidates(
        repo_root,
        include_cache=args.cache,
        include_temp=args.temp,
        include_root_review=args.root,
    )
    _log_candidates(candidates)

    if not args.apply:
        return 0

    deleted, errors = _apply_local_candidates(repo_root, candidates)
    skipped_review = [candidate for candidate in candidates if not candidate.apply_allowed]
    _log_apply_summary(
        deleted=deleted,
        skipped_review=skipped_review,
        errors=errors,
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
