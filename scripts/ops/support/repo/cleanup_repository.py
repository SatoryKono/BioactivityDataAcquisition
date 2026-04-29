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
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

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

COVERAGE_FILE_NAME = ".coverage"
COVERAGE_GLOB_PATTERN = ".coverage.*"
COVERAGE_XML_NAME = "coverage.xml"

SAFE_LOCAL_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".benchmarks",
        ".coverage-sharded",
        ".eggs",
        ".hypothesis",
        ".ipynb_checkpoints",
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
SAFE_LOCAL_DIR_SUFFIXES: frozenset[str] = frozenset({".egg-info"})
EXACT_TEMP_FILE_NAMES: frozenset[str] = frozenset(
    {
        "full_log.txt",
        "project_rules_failures.txt",
    }
)
FINAL_REPORT_PREFIX = "final_report"
FINAL_REPORT_SUFFIX = ".txt"
VENV_SEGMENTS: frozenset[str] = frozenset(
    {
        ".venv",
        ".venv-docs",
        ".venv-win",
        ".venv-win-corrupt",
        "venv",
    }
)
PRUNED_WALK_DIRS: frozenset[str] = frozenset(VENV_SEGMENTS | {".git", ".worktrees", ".rollback"})
SAFE_LOCAL_FILE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})
DEFAULT_DETAIL_LIMIT = 25
ROOT_HYGIENE_REVIEW_REGISTRY = Path("configs/quality/root_hygiene_review_registry.yaml")
REVIEW_REFERENCE_SEARCH_PATHS: tuple[str, ...] = (
    ".github",
    "docs",
    "scripts",
    "tests",
    "configs",
    "README.md",
    "Makefile",
    "pyproject.toml",
    "package.json",
    ".gitignore",
    ".dockerignore",
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


@dataclass(frozen=True)
class ReviewLaneEvidence:
    lane_id: str
    classification: str
    path: Path
    current_live_state: str
    canonical_path: Path | None
    action_if_reintroduced: str | None
    exists: bool
    tracked: bool
    has_history: bool
    canonical_exists: bool
    cmp_status: str | None
    reference_hits: int
    review_status: str

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


def _load_yaml_object(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def _is_safe_local_dir_name(name: str) -> bool:
    return name in SAFE_LOCAL_DIR_NAMES or name.endswith(tuple(SAFE_LOCAL_DIR_SUFFIXES))


def _run_git(repo_root: Path, *git_args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # nosec
        ["git", "-C", str(repo_root), *git_args],
        check=True,
        capture_output=True,
        text=False,
    )


def _git_path_has_history(repo_root: Path, path: Path) -> bool:
    try:
        completed = _run_git(repo_root, "log", "--format=%H", "-n", "1", "--", path.as_posix())
    except subprocess.CalledProcessError:
        return False
    return bool(completed.stdout.strip())


def _tracked_paths(repo_root: Path) -> list[str]:
    completed = _run_git(repo_root, "ls-files", "-z")
    return [
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    ]


def _tracked_path_set(repo_root: Path) -> set[str]:
    return set(_tracked_paths(repo_root))


def _local_status_paths(repo_root: Path) -> list[str] | None:
    try:
        completed = _run_git(
            repo_root,
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--directory",
            "-z",
        )
    except subprocess.CalledProcessError:
        return None
    return [
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    ]


def _is_venv_path(path: Path) -> bool:
    return bool(VENV_SEGMENTS.intersection(path.parts))


def _count_reference_hits(repo_root: Path, path: Path) -> int:
    filename = path.name
    path_pattern = re.escape(path.as_posix())
    filename_pattern = re.escape(filename)
    pattern = rf"{path_pattern}|{filename_pattern}"
    try:
        completed = subprocess.run(  # nosec
            ["rg", "-n", "-S", "-e", pattern, *REVIEW_REFERENCE_SEARCH_PATHS],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return 0
    if completed.returncode not in {0, 1}:
        return 0
    return 0 if not completed.stdout else len(completed.stdout.splitlines())


def _cmp_status(repo_root: Path, path: Path, canonical_path: Path | None) -> str | None:
    if canonical_path is None:
        return None
    left = repo_root / path
    right = repo_root / canonical_path
    if not left.exists() or not right.exists():
        return None
    if left.is_file() and right.is_file():
        return "match" if left.read_bytes() == right.read_bytes() else "diff"
    return "not_applicable"


def _is_blocked_path(path: Path, repo_root: Path, blocked_paths: frozenset[str]) -> bool:
    return is_within_blocked_cleanup_zone(path.relative_to(repo_root), blocked_paths)


def _prune_walk_dirs(
    repo_root: Path,
    base: Path,
    dirnames: list[str],
    *,
    blocked_paths: frozenset[str],
    prune_safe_local_dirs: bool,
) -> None:
    kept: list[str] = []
    for name in dirnames:
        if name in PRUNED_WALK_DIRS:
            continue
        child = base / name
        if _is_venv_path(child):
            continue
        if _is_blocked_path(child, repo_root, blocked_paths):
            continue
        if prune_safe_local_dirs and name in SAFE_LOCAL_DIR_NAMES:
            continue
        kept.append(name)
    dirnames[:] = kept


def _local_cache_dir_candidate(path: Path) -> CleanupCandidate:
    return CleanupCandidate(
        path=path,
        category="local_cache_dir",
        tracked=False,
        apply_allowed=True,
        reason="exact local artifact family outside blocked cleanup zones",
    )


def _safe_local_dir_candidate(
    path: Path,
    *,
    repo_root: Path,
    blocked_paths: frozenset[str],
) -> CleanupCandidate | None:
    if _is_blocked_path(path, repo_root, blocked_paths):
        return None
    return _local_cache_dir_candidate(path.relative_to(repo_root))


def _discover_local_dir_candidates_in_base(
    *,
    repo_root: Path,
    base: Path,
    dirnames: list[str],
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for name in dirnames:
        if not _is_safe_local_dir_name(name):
            continue
        candidate = _safe_local_dir_candidate(
            base / name,
            repo_root=repo_root,
            blocked_paths=blocked_paths,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _iter_local_dir_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
    status_paths: list[str] | None = None,
) -> list[CleanupCandidate]:
    if status_paths is not None:
        return _iter_local_dir_candidates_from_status_paths(
            status_paths,
            blocked_paths=blocked_paths,
        )
    candidates: list[CleanupCandidate] = []
    for dirpath, dirnames, _filenames in os.walk(repo_root):
        base = Path(dirpath)
        if _is_venv_path(base):
            dirnames[:] = []
            continue
        candidates.extend(
            _discover_local_dir_candidates_in_base(
                repo_root=repo_root,
                base=base,
                dirnames=dirnames,
                blocked_paths=blocked_paths,
            )
        )
        _prune_walk_dirs(
            repo_root,
            base,
            dirnames,
            blocked_paths=blocked_paths,
            prune_safe_local_dirs=False,
        )
    return candidates


def _local_file_category(filename: str) -> str | None:
    if filename in {COVERAGE_FILE_NAME, COVERAGE_XML_NAME}:
        return "coverage"
    if filename.startswith(f"{COVERAGE_FILE_NAME}."):
        return "coverage"
    if Path(filename).suffix in SAFE_LOCAL_FILE_SUFFIXES:
        return "compiled"
    if filename.endswith((".log", ".tmp")):
        return "logs_temp"
    if filename in EXACT_TEMP_FILE_NAMES:
        return "logs_temp"
    if filename.startswith(FINAL_REPORT_PREFIX) and filename.endswith(FINAL_REPORT_SUFFIX):
        return "logs_temp"
    return None


def _local_file_candidate(
    path: Path,
    *,
    repo_root: Path,
    blocked_paths: frozenset[str],
) -> CleanupCandidate | None:
    if _is_blocked_path(path, repo_root, blocked_paths):
        return None
    category = _local_file_category(path.name)
    if category is None:
        return None
    return CleanupCandidate(
        path=path.relative_to(repo_root),
        category=category,
        tracked=False,
        apply_allowed=True,
        reason="exact local artifact file outside blocked cleanup zones",
    )


def _iter_local_file_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
    status_paths: list[str] | None = None,
) -> list[CleanupCandidate]:
    if status_paths is not None:
        return _iter_local_file_candidates_from_status_paths(
            status_paths,
            blocked_paths=blocked_paths,
        )
    candidates: list[CleanupCandidate] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        base = Path(dirpath)
        if _is_venv_path(base):
            dirnames[:] = []
            continue
        _prune_walk_dirs(
            repo_root,
            base,
            dirnames,
            blocked_paths=blocked_paths,
            prune_safe_local_dirs=True,
        )
        for filename in filenames:
            path = base / filename
            candidate = _local_file_candidate(
                path,
                repo_root=repo_root,
                blocked_paths=blocked_paths,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _iter_local_dir_candidates_from_status_paths(
    status_paths: list[str],
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    seen: set[Path] = set()
    for raw_path in status_paths:
        normalized = Path(raw_path.rstrip("/"))
        if _is_venv_path(normalized):
            continue
        for index, segment in enumerate(normalized.parts):
            if not _is_safe_local_dir_name(segment):
                continue
            candidate_path = Path(*normalized.parts[: index + 1])
            if candidate_path in seen:
                continue
            if is_within_blocked_cleanup_zone(candidate_path, blocked_paths):
                continue
            seen.add(candidate_path)
            candidates.append(_local_cache_dir_candidate(candidate_path))
    return candidates


def _iter_local_file_candidates_from_status_paths(
    status_paths: list[str],
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for raw_path in status_paths:
        normalized = Path(raw_path.rstrip("/"))
        if _is_venv_path(normalized) or raw_path.endswith("/"):
            continue
        category = _local_file_category(normalized.name)
        if category is None:
            continue
        if is_within_blocked_cleanup_zone(normalized, blocked_paths):
            continue
        candidates.append(
            CleanupCandidate(
                path=normalized,
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


def _load_root_review_registry(repo_root: Path) -> dict[str, object]:
    return _load_yaml_object(repo_root / ROOT_HYGIENE_REVIEW_REGISTRY)


def _review_status_for_evidence(
    *,
    classification: str,
    current_live_state: str,
    exists: bool,
    tracked: bool,
    cmp_status: str | None,
    reference_hits: int,
) -> str:
    if current_live_state == "absent_from_root_baseline" and not exists:
        return "absent_baseline_ok"
    if current_live_state != "absent_from_root_baseline" and not exists:
        return "registry_drift"
    if classification == "blocked_cleanup_zone":
        return "blocked_cleanup_retained"
    if exists and not tracked:
        return "present_untracked_surface"
    if classification == "owner_decision_required":
        return "present_owner_decision_required"
    if cmp_status == "match":
        return "present_cmp_match"
    if reference_hits == 0:
        return "present_no_callers"
    return "present_unreviewed"


def _review_evidence_from_candidate(
    repo_root: Path,
    tracked_paths: set[str],
    *,
    lane_id: str,
    classification: str,
    candidate: dict[str, object],
) -> ReviewLaneEvidence | None:
    raw_path = candidate.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None

    path = Path(raw_path)
    canonical_raw = candidate.get("canonical_path")
    canonical_path = (
        Path(canonical_raw)
        if isinstance(canonical_raw, str) and canonical_raw
        else None
    )
    exists = (repo_root / path).exists()
    tracked = path.as_posix() in tracked_paths
    cmp_status = _cmp_status(repo_root, path, canonical_path) if exists else None
    reference_hits = _count_reference_hits(repo_root, path) if exists else 0

    return ReviewLaneEvidence(
        lane_id=lane_id,
        classification=classification,
        path=path,
        current_live_state=str(candidate.get("current_live_state", "")),
        canonical_path=canonical_path,
        action_if_reintroduced=(
            str(candidate.get("action_if_reintroduced"))
            if candidate.get("action_if_reintroduced") is not None
            else None
        ),
        exists=exists,
        tracked=tracked,
        has_history=_git_path_has_history(repo_root, path),
        canonical_exists=bool(canonical_path and (repo_root / canonical_path).exists()),
        cmp_status=cmp_status,
        reference_hits=reference_hits,
        review_status=_review_status_for_evidence(
            classification=classification,
            current_live_state=str(candidate.get("current_live_state", "")),
            exists=exists,
            tracked=tracked,
            cmp_status=cmp_status,
            reference_hits=reference_hits,
        ),
    )


def collect_root_review_evidence(repo_root: Path) -> list[ReviewLaneEvidence]:
    payload = _load_root_review_registry(repo_root)
    lanes = payload.get("review_lanes")
    if not isinstance(lanes, list):
        return []

    tracked_paths = _tracked_path_set(repo_root)
    evidence: list[ReviewLaneEvidence] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("lane_id", ""))
        classification = str(lane.get("classification", ""))
        candidates = lane.get("candidates")
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            row = _review_evidence_from_candidate(
                repo_root,
                tracked_paths,
                lane_id=lane_id,
                classification=classification,
                candidate=candidate,
            )
            if row is not None:
                evidence.append(row)
    return sorted(evidence, key=lambda item: (item.lane_id, item.rel_path))


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
    status_paths = _local_status_paths(repo_root)

    if include_cache:
        candidates.extend(
            _iter_local_dir_candidates(
                repo_root,
                blocked_paths=policy.blocked_cleanup_paths,
                status_paths=status_paths,
            )
        )
    if include_temp:
        candidates.extend(
            _iter_local_file_candidates(
                repo_root,
                blocked_paths=policy.blocked_cleanup_paths,
                status_paths=status_paths,
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
            if not target.exists():
                continue
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                if target.exists():
                    raise OSError(f"directory still exists after cleanup: {candidate.rel_path}")
            elif target.exists():
                target.unlink()
            deleted.append(candidate)
        except OSError as exc:
            errors.append(f"{candidate.rel_path}: {exc}")
    return deleted, errors


def _log_candidates(
    candidates: list[CleanupCandidate],
    *,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> None:
    if not candidates:
        logger.info("No cleanup candidates found.")
        return

    categories: dict[str, list[CleanupCandidate]] = {}
    for candidate in candidates:
        categories.setdefault(candidate.category, []).append(candidate)

    for category in sorted(categories):
        category_candidates = categories[category]
        logger.info("## %s (%d)", category.upper(), len(category_candidates))
        visible_candidates = category_candidates[:detail_limit]
        for candidate in visible_candidates:
            mode = "apply" if candidate.apply_allowed else "review"
            logger.info("  [%s] %s", mode, candidate.rel_path)
            logger.info("      %s", candidate.reason)
        hidden_count = len(category_candidates) - len(visible_candidates)
        if hidden_count > 0:
            logger.info("  ... %d additional candidate(s) omitted", hidden_count)
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


def _log_review_lane_evidence(
    evidence_rows: list[ReviewLaneEvidence],
    *,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> None:
    if not evidence_rows:
        return

    lanes: dict[str, list[ReviewLaneEvidence]] = {}
    for row in evidence_rows:
        lanes.setdefault(row.lane_id, []).append(row)

    logger.info("## ROOT REVIEW EVIDENCE")
    for lane_id in sorted(lanes):
        rows = lanes[lane_id]
        visible_rows = rows[:detail_limit]
        classification = rows[0].classification if rows else "unknown"
        logger.info("### %s (%s, %d)", lane_id, classification, len(rows))
        for row in visible_rows:
            logger.info(
                "  [%s] %s | exists=%s tracked=%s history=%s refs=%d canonical=%s cmp=%s",
                row.review_status,
                row.rel_path,
                str(row.exists).lower(),
                str(row.tracked).lower(),
                str(row.has_history).lower(),
                row.reference_hits,
                str(row.canonical_exists).lower(),
                row.cmp_status or "n/a",
            )
            if row.action_if_reintroduced:
                logger.info("      action: %s", row.action_if_reintroduced)
        hidden_count = len(rows) - len(visible_rows)
        if hidden_count > 0:
            logger.info("  ... %d additional review row(s) omitted", hidden_count)
        logger.info("")


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
        help="Skip compiled/coverage/log/temp local file candidates",
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
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=DEFAULT_DETAIL_LIMIT,
        help="Maximum number of detailed entries to print per category",
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
    _log_candidates(candidates, detail_limit=max(args.detail_limit, 0))
    if args.root:
        _log_review_lane_evidence(
            collect_root_review_evidence(repo_root),
            detail_limit=max(args.detail_limit, 0),
        )

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
