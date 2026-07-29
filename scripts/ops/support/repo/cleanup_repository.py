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
import fnmatch
import json
import logging
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.engineering.repo import audit_root_cleanliness as root_cleanliness
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
CLEANUP_REPOSITORY_TOOL = "scripts/ops/support/repo/cleanup_repository.py"
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
PRUNED_WALK_DIRS: frozenset[str] = frozenset(
    VENV_SEGMENTS | {".git", ".worktrees", ".rollback"}
)
SAFE_LOCAL_FILE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})
DEFAULT_DETAIL_LIMIT = 25
ROOT_HYGIENE_REVIEW_REGISTRY = Path("configs/quality/root_hygiene_review_registry.yaml")
REPLAY_SAFE_CLEANUP_INVENTORY = Path(
    "configs/quality/replay_safe_cleanup_inventory.yaml"
)
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
REPORTS_WORKSPACE = Path("reports")
REPORTS_LOCAL_PRUNE_DIRS: tuple[Path, ...] = (
    Path("reports/Codex"),
    Path("reports/tmp"),
)
REPORTS_RETAINED_DIRS: tuple[Path, ...] = (
    Path("reports/logs"),
    Path("reports/observability"),
    Path("reports/quality"),
    Path("reports/test-swarm"),
)
REPORTS_RETAINED_FILES: tuple[Path, ...] = (Path("reports/README.md"),)
REPORTS_ROOT_PRUNE_PATTERNS: tuple[str, ...] = (
    "*_merged.md",
    "tmp_module_dependency_map.*",
)
REPORTS_RETAINED_DIR_TRANSIENT_PATTERNS: tuple[str, ...] = (
    "_tmp_*",
    "architecture_debt_execution_plan_*.json",
    "contract-registry-dq-diagnostics.json",
    "duplication-baseline.json",
    "duplication-baseline.md",
    "pretest_guardrails_*.json",
    "tasks_architecture_metric_exemptions_*.json",
    "test-runs",
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
    owner: str | None
    retention_class: str | None
    retention_action: str | None
    cleanup_policy: str | None
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


@dataclass(frozen=True)
class RootPolicyMismatch:
    path: Path
    mismatch_type: str
    tracked: bool

    @property
    def rel_path(self) -> str:
        return self.path.as_posix()


@dataclass(frozen=True)
class ReportsWorkspaceEvidence:
    path: Path
    classification: str
    tracked: bool
    exists: bool
    has_history: bool
    reference_hits: int
    generator: str | None
    commit_policy: str | None
    reason: str
    retention_entry_id: str | None = None
    retention_owner: str | None = None
    retention_ttl_days: int | None = None
    age_days: int | None = None
    ttl_expired: bool | None = None

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
        completed = _run_git(
            repo_root, "log", "--format=%H", "-n", "1", "--", path.as_posix()
        )
    except subprocess.CalledProcessError:
        return False
    return bool(completed.stdout.strip())


@cache
def _tracked_paths(repo_root: Path) -> list[str]:
    completed = _run_git(repo_root, "ls-files", "-z")
    return [
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    ]


@cache
def _tracked_path_set(repo_root: Path) -> set[str]:
    return set(_tracked_paths(repo_root))


@cache
def _tracked_ancestor_dirs(repo_root: Path) -> set[str]:
    ancestors: set[str] = set()
    for tracked_path in _tracked_paths(repo_root):
        parts = tracked_path.split("/")
        if len(parts) <= 1:
            continue
        current: list[str] = []
        for segment in parts[:-1]:
            current.append(segment)
            ancestors.add("/".join(current))
    return ancestors


def _path_is_tracked_or_has_tracked_descendants(
    path: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str] | None = None,
) -> bool:
    path_text = path.as_posix().rstrip("/")
    if path_text in tracked_paths:
        return True
    if tracked_ancestor_dirs is not None:
        return path_text in tracked_ancestor_dirs
    descendant_prefix = f"{path_text}/"
    return any(
        tracked_path.startswith(descendant_prefix) for tracked_path in tracked_paths
    )


@cache
def _local_status_paths(repo_root: Path) -> list[str] | None:
    try:
        completed = subprocess.run(  # nosec
            [
                "git",
                "-C",
                str(repo_root),
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--directory",
                "-z",
            ],
            check=True,
            capture_output=True,
            text=False,
            timeout=2,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return [
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    ]


def _is_venv_path(path: Path) -> bool:
    return bool(VENV_SEGMENTS.intersection(path.parts))


@cache
def _count_reference_hits(repo_root: Path, path: Path) -> int:
    absolute_path = repo_root / path
    if absolute_path.is_dir():
        return 0
    path_text = path.as_posix()
    for lane in _load_root_review_registry(repo_root).get("review_lanes", []):
        if not isinstance(lane, dict):
            continue
        for candidate in lane.get("candidates", []):
            if (
                isinstance(candidate, dict)
                and str(candidate.get("path") or "") == path_text
            ):
                return 1
    return 0


def _history_signal_for_path(
    repo_root: Path,
    path: Path,
    *,
    tracked: bool,
    exists: bool,
) -> bool:
    if tracked:
        return True
    absolute_path = repo_root / path
    if not exists or absolute_path.is_dir():
        return False
    return _git_path_has_history(repo_root, path)


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


def _is_blocked_path(
    path: Path, repo_root: Path, blocked_paths: frozenset[str]
) -> bool:
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


def _iter_root_local_dir_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for child in repo_root.iterdir():
        if not child.is_dir():
            continue
        if _is_venv_path(child.relative_to(repo_root)):
            continue
        if not _is_safe_local_dir_name(child.name):
            continue
        candidate = _safe_local_dir_candidate(
            child,
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
    if filename.startswith(FINAL_REPORT_PREFIX) and filename.endswith(
        FINAL_REPORT_SUFFIX
    ):
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


def _iter_root_local_file_candidates(
    repo_root: Path,
    *,
    blocked_paths: frozenset[str],
) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for child in repo_root.iterdir():
        if not child.is_file():
            continue
        candidate = _local_file_candidate(
            child,
            repo_root=repo_root,
            blocked_paths=blocked_paths,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


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


@cache
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
    if classification == "owner_decision_resolved":
        return "present_owner_decision_resolved"
    if classification == "owner_decision_required":
        return "present_owner_decision_required"
    if cmp_status == "match":
        return "present_cmp_match"
    if reference_hits == 0:
        return "present_no_callers"
    return "present_unreviewed"


def _optional_str(value: object) -> str | None:
    """Coerce a present scalar metadata field to str; keep None for missing."""
    if value is None:
        return None
    return str(value)


def _candidate_or_lane_str(
    candidate: dict[str, object],
    lane_metadata: dict[str, object],
    field_name: str,
) -> str | None:
    """Prefer candidate metadata, then lane metadata, for optional string fields."""
    if candidate.get(field_name) is not None:
        return str(candidate.get(field_name))
    if lane_metadata.get(field_name) is not None:
        return str(lane_metadata.get(field_name))
    return None


def _canonical_path_from_candidate(
    candidate: dict[str, object],
) -> Path | None:
    canonical_raw = candidate.get("canonical_path")
    if isinstance(canonical_raw, str) and canonical_raw:
        return Path(canonical_raw)
    return None


def _local_review_probes(
    repo_root: Path,
    path: Path,
    canonical_path: Path | None,
    *,
    exists: bool,
    tracked: bool,
    current_live_state: str,
) -> tuple[str | None, int, bool]:
    """Return (cmp_status, reference_hits, has_history) for one review path."""
    skip_local_review_probes = (
        exists
        and not tracked
        and current_live_state == "present_local_only_root_surface"
    )
    if skip_local_review_probes or not exists:
        return None, 0, False
    cmp_status = _cmp_status(repo_root, path, canonical_path)
    reference_hits = _count_reference_hits(repo_root, path)
    has_history = _history_signal_for_path(
        repo_root,
        path,
        tracked=tracked,
        exists=exists,
    )
    return cmp_status, reference_hits, has_history


def _review_evidence_from_candidate(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    lane_id: str,
    classification: str,
    lane_metadata: dict[str, object],
    candidate: dict[str, object],
) -> ReviewLaneEvidence | None:
    raw_path = candidate.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None

    path = Path(raw_path)
    canonical_path = _canonical_path_from_candidate(candidate)
    current_live_state = str(candidate.get("current_live_state", ""))
    exists = (repo_root / path).exists()
    tracked = _path_is_tracked_or_has_tracked_descendants(
        path, tracked_paths, tracked_ancestor_dirs
    )
    cmp_status, reference_hits, has_history = _local_review_probes(
        repo_root,
        path,
        canonical_path,
        exists=exists,
        tracked=tracked,
        current_live_state=current_live_state,
    )

    return ReviewLaneEvidence(
        lane_id=lane_id,
        classification=classification,
        path=path,
        current_live_state=current_live_state,
        canonical_path=canonical_path,
        action_if_reintroduced=_optional_str(candidate.get("action_if_reintroduced")),
        owner=_candidate_or_lane_str(candidate, lane_metadata, "owner"),
        retention_class=_candidate_or_lane_str(
            candidate, lane_metadata, "retention_class"
        ),
        retention_action=_candidate_or_lane_str(
            candidate, lane_metadata, "retention_action"
        ),
        cleanup_policy=_candidate_or_lane_str(
            candidate, lane_metadata, "cleanup_policy"
        ),
        exists=exists,
        tracked=tracked,
        has_history=has_history,
        canonical_exists=bool(canonical_path and (repo_root / canonical_path).exists()),
        cmp_status=cmp_status,
        reference_hits=reference_hits,
        review_status=_review_status_for_evidence(
            classification=classification,
            current_live_state=current_live_state,
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
    tracked_ancestor_dirs = _tracked_ancestor_dirs(repo_root)
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
                tracked_ancestor_dirs,
                lane_id=lane_id,
                classification=classification,
                lane_metadata=lane,
                candidate=candidate,
            )
            if row is not None:
                evidence.append(row)
    return sorted(evidence, key=lambda item: (item.lane_id, item.rel_path))


def collect_root_policy_mismatches(repo_root: Path) -> list[RootPolicyMismatch]:
    tracked_paths = _tracked_paths(repo_root)
    allowed_root_files = root_cleanliness._load_allowed_root_files(repo_root)
    structure_catalog = root_cleanliness._load_structure_catalog(repo_root)
    allowed_root_dirs = root_cleanliness._approved_root_directories(structure_catalog)
    tracked_root_files, tracked_root_dirs = (
        root_cleanliness._collect_tracked_root_entries(tracked_paths)
    )
    mismatches: list[RootPolicyMismatch] = []
    mismatch_specs = (
        (
            "unexpected_tracked_root_file",
            sorted(tracked_root_files - allowed_root_files),
            True,
        ),
        (
            "unexpected_tracked_root_dir",
            sorted(tracked_root_dirs - allowed_root_dirs),
            True,
        ),
    )
    for mismatch_type, raw_paths, tracked in mismatch_specs:
        assert isinstance(raw_paths, list)
        for raw_path in raw_paths:
            mismatches.append(
                RootPolicyMismatch(
                    path=Path(str(raw_path)),
                    mismatch_type=mismatch_type,
                    tracked=tracked,
                )
            )
    return sorted(mismatches, key=lambda item: (item.mismatch_type, item.rel_path))


@cache
def _load_generated_artifact_routes(repo_root: Path) -> list[dict[str, object]]:
    routing_path = repo_root / "configs" / "quality" / "generated_artifact_routing.yaml"
    if not routing_path.exists():
        return []
    payload = _load_yaml_object(routing_path)
    routes = payload.get("routes")
    if not isinstance(routes, list):
        return []
    return [route for route in routes if isinstance(route, dict)]


@cache
def _load_replay_safe_cleanup_entries(repo_root: Path) -> list[dict[str, object]]:
    inventory_path = repo_root / REPLAY_SAFE_CLEANUP_INVENTORY
    if not inventory_path.exists():
        return []
    payload = _load_yaml_object(inventory_path)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _reports_registered_route_metadata(
    repo_root: Path,
) -> dict[str, tuple[str | None, str | None]]:
    metadata: dict[str, tuple[str | None, str | None]] = {}
    for route in _load_generated_artifact_routes(repo_root):
        generator = route.get("generator")
        commit_policy = route.get("commit_policy")
        outputs = route.get("outputs")
        if not isinstance(outputs, list):
            continue
        for output in outputs:
            if not isinstance(output, str) or not output.startswith("reports/"):
                continue
            metadata[output.rstrip("/")] = (
                str(generator) if isinstance(generator, str) else None,
                str(commit_policy) if isinstance(commit_policy, str) else None,
            )
    return metadata


def _reports_retention_metadata(
    repo_root: Path,
) -> dict[str, tuple[str, str | None, int | None]]:
    metadata: dict[str, tuple[str, str | None, int | None]] = {}
    for entry in _load_replay_safe_cleanup_entries(repo_root):
        path = entry.get("path")
        if not isinstance(path, str) or not path.startswith("reports/quality/"):
            continue
        metadata[path] = (
            str(entry.get("id", "")) or path,
            str(entry.get("owner")) if isinstance(entry.get("owner"), str) else None,
            int(entry["ttl_days"]) if isinstance(entry.get("ttl_days"), int) else None,
        )
    return metadata


def _iter_reports_root_prune_candidates(repo_root: Path) -> set[Path]:
    candidates: set[Path] = set()
    for pattern in REPORTS_ROOT_PRUNE_PATTERNS:
        for match in (repo_root / REPORTS_WORKSPACE).glob(pattern):
            if match.is_file():
                candidates.add(match.relative_to(repo_root))
    return candidates


def _iter_reports_retained_dir_transient_candidates(repo_root: Path) -> set[Path]:
    candidates: set[Path] = set()
    for retained_dir in REPORTS_RETAINED_DIRS:
        root = repo_root / retained_dir
        if not root.exists():
            continue
        for pattern in REPORTS_RETAINED_DIR_TRANSIENT_PATTERNS:
            for match in root.glob(pattern):
                candidates.add(match.relative_to(repo_root))
    return candidates


def _is_reports_retained_dir_transient_path(path: Path) -> bool:
    path_text = path.as_posix()
    inside_retained_dir = any(
        path_text.startswith(f"{retained_dir.as_posix()}/")
        for retained_dir in REPORTS_RETAINED_DIRS
    )
    return inside_retained_dir and any(
        fnmatch.fnmatch(path.name, pattern)
        for pattern in REPORTS_RETAINED_DIR_TRANSIENT_PATTERNS
    )


_PRETEST_GUARDRAILS_TIMESTAMP_RE = re.compile(
    r"^pretest_guardrails_(\d{8})_(\d{6})\.json$"
)


def _reports_quality_embedded_timestamp(path: Path) -> datetime | None:
    match = _PRETEST_GUARDRAILS_TIMESTAMP_RE.match(path.name)
    if match is None:
        return None
    date_part, time_part = match.groups()
    try:
        return datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S").replace(
            tzinfo=UTC
        )
    except ValueError:
        return None


def _artifact_timestamp(path: Path) -> datetime | None:
    embedded = _reports_quality_embedded_timestamp(path)
    if embedded is not None:
        return embedded
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _artifact_age_days(path: Path, *, now: datetime) -> int | None:
    timestamp = _artifact_timestamp(path)
    if timestamp is None or timestamp > now:
        return None
    # Retention TTLs are calendar-day policies; avoid hour-of-day drift across
    # platforms and CI runners by comparing date boundaries rather than
    # full 24-hour intervals.
    return (now.date() - timestamp.date()).days


def _ttl_report_row_classification(
    *,
    tracked: bool,
    exists: bool,
    age_days: int | None,
    retention_ttl_days: int | None,
) -> tuple[str, bool | None]:
    if retention_ttl_days is None or not exists:
        return ("REVIEW_REQUIRED" if tracked else "PRUNE_CANDIDATE", None)
    expired = age_days is not None and age_days > retention_ttl_days
    if tracked:
        return ("REVIEW_REQUIRED", expired)
    return ("PRUNE_CANDIDATE" if expired else "RETAIN", expired)


def _iter_reports_top_level_uncurated_surfaces(repo_root: Path) -> set[Path]:
    reports_root = repo_root / REPORTS_WORKSPACE
    if not reports_root.exists():
        return set()
    retained = set(REPORTS_RETAINED_FILES) | set(REPORTS_RETAINED_DIRS)
    local_prune = set(REPORTS_LOCAL_PRUNE_DIRS)
    return {
        child.relative_to(repo_root)
        for child in reports_root.iterdir()
        if child.relative_to(repo_root) not in retained
        and child.relative_to(repo_root) not in local_prune
    }


def _reports_workspace_row(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    path: Path,
    classification: str,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    reason: str,
) -> ReportsWorkspaceEvidence:
    rel_path = path.as_posix()
    generator, commit_policy = route_metadata.get(rel_path, (None, None))
    retention_entry_id = None
    retention_owner = None
    retention_ttl_days = None
    for pattern, values in retention_metadata.items():
        if fnmatch.fnmatch(rel_path, pattern):
            retention_entry_id, retention_owner, retention_ttl_days = values
            break
    exists = (repo_root / path).exists()
    tracked = _path_is_tracked_or_has_tracked_descendants(
        path, tracked_paths, tracked_ancestor_dirs
    )
    skip_local_review_probes = (
        exists
        and not tracked
        and (
            classification == "PRUNE_CANDIDATE"
            or _is_reports_retained_dir_transient_path(path)
        )
    )
    age_days = (
        _artifact_age_days(repo_root / path, now=datetime.now(tz=UTC))
        if exists
        else None
    )
    return ReportsWorkspaceEvidence(
        path=path,
        classification=classification,
        tracked=tracked,
        exists=exists,
        has_history=False if skip_local_review_probes else tracked,
        reference_hits=0,
        generator=generator,
        commit_policy=commit_policy,
        retention_entry_id=retention_entry_id,
        retention_owner=retention_owner,
        retention_ttl_days=retention_ttl_days,
        age_days=age_days,
        ttl_expired=_ttl_expired_flag(
            retention_ttl_days=retention_ttl_days, age_days=age_days
        ),
        reason=reason,
    )


def _ttl_expired_flag(
    *, retention_ttl_days: int | None, age_days: int | None
) -> bool | None:
    if retention_ttl_days is None:
        return None
    return age_days is not None and age_days > retention_ttl_days


def _path_present_or_tracked(
    repo_root: Path,
    path: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
) -> bool:
    return (repo_root / path).exists() or _path_is_tracked_or_has_tracked_descendants(
        path, tracked_paths, tracked_ancestor_dirs
    )


def _tracked_or_prune_classification(tracked: bool) -> str:
    if tracked:
        return "REVIEW_REQUIRED"
    return "PRUNE_CANDIDATE"


def _transient_ttl_reason(*, tracked: bool, ttl_expired: bool | None) -> str:
    if tracked:
        ttl_state = "exceeds" if ttl_expired else "is still within"
        return (
            "tracked transient artifact inside retained reports surface "
            f"{ttl_state} its TTL and requires manual review before prune"
        )
    if ttl_expired:
        return (
            "transient retained-surface artifact exceeds its TTL and "
            "is a bounded local prune candidate"
        )
    return (
        "transient retained-surface artifact is still within its "
        "TTL window and should be retained"
    )


def _collect_retained_report_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path in REPORTS_RETAINED_FILES:
        if not _path_present_or_tracked(
            repo_root, path, tracked_paths, tracked_ancestor_dirs
        ):
            continue
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification="RETAIN",
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason="canonical reports workspace guide must remain present",
        )
    for path in REPORTS_RETAINED_DIRS:
        if not _path_present_or_tracked(
            repo_root, path, tracked_paths, tracked_ancestor_dirs
        ):
            continue
        if path == Path("reports/logs"):
            reason = "runtime log sink documented in active operator guidance"
        else:
            reason = "governed reports workspace surface retained by docs or tracked evidence"
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification="RETAIN",
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=reason,
        )


def _collect_local_prune_dir_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path in REPORTS_LOCAL_PRUNE_DIRS:
        if not (repo_root / path).exists():
            continue
        tracked = _path_is_tracked_or_has_tracked_descendants(
            path, tracked_paths, tracked_ancestor_dirs
        )
        if tracked:
            reason = "tracked reports subtree requires manual review before prune"
        else:
            reason = "local model/tmp reports are exact-path prune candidates"
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification=_tracked_or_prune_classification(tracked),
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=reason,
        )


def _collect_registered_route_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path_text in route_metadata:
        path = Path(path_text)
        if not (repo_root / path).exists():
            continue
        if path in REPORTS_RETAINED_FILES or path in REPORTS_RETAINED_DIRS:
            continue
        tracked = _path_is_tracked_or_has_tracked_descendants(
            path, tracked_paths, tracked_ancestor_dirs
        )
        if tracked:
            reason = (
                "registered working report exists as tracked output and needs "
                "explicit retention review"
            )
        else:
            reason = (
                "registered working report exists only locally and may be pruned "
                "after review"
            )
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification=_tracked_or_prune_classification(tracked),
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=reason,
        )


def _collect_root_prune_report_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path in _iter_reports_root_prune_candidates(repo_root):
        if path.as_posix() in rows:
            continue
        tracked = _path_is_tracked_or_has_tracked_descendants(
            path, tracked_paths, tracked_ancestor_dirs
        )
        if tracked:
            reason = "tracked root report requires explicit owner review"
        else:
            reason = "untracked root report matches approved local prune pattern"
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification=_tracked_or_prune_classification(tracked),
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=reason,
        )


def _collect_transient_retained_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path in _iter_reports_retained_dir_transient_candidates(repo_root):
        if path.as_posix() in rows:
            continue
        tracked = _path_is_tracked_or_has_tracked_descendants(
            path, tracked_paths, tracked_ancestor_dirs
        )
        candidate_row = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification="PRUNE_CANDIDATE",
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason="transient retained-surface artifact candidate",
        )
        classification, ttl_expired = _ttl_report_row_classification(
            tracked=tracked,
            exists=candidate_row.exists,
            age_days=candidate_row.age_days,
            retention_ttl_days=candidate_row.retention_ttl_days,
        )
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification=classification,
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=_transient_ttl_reason(tracked=tracked, ttl_expired=ttl_expired),
        )


def _collect_uncurated_surface_rows(
    repo_root: Path,
    tracked_paths: set[str],
    tracked_ancestor_dirs: set[str],
    *,
    route_metadata: dict[str, tuple[str | None, str | None]],
    retention_metadata: dict[str, tuple[str, str | None, int | None]],
    rows: dict[str, ReportsWorkspaceEvidence],
) -> None:
    for path in _iter_reports_top_level_uncurated_surfaces(repo_root):
        if path.as_posix() in rows:
            continue
        tracked = _path_is_tracked_or_has_tracked_descendants(
            path, tracked_paths, tracked_ancestor_dirs
        )
        if tracked:
            reason = (
                "tracked reports workspace surface sits outside retained "
                "families and needs explicit retention review"
            )
        else:
            reason = (
                "non-curated top-level reports workspace surface is a "
                "local prune candidate"
            )
        rows[path.as_posix()] = _reports_workspace_row(
            repo_root,
            tracked_paths,
            tracked_ancestor_dirs,
            path=path,
            classification=_tracked_or_prune_classification(tracked),
            route_metadata=route_metadata,
            retention_metadata=retention_metadata,
            reason=reason,
        )


def collect_reports_workspace_evidence(
    repo_root: Path,
) -> list[ReportsWorkspaceEvidence]:
    tracked_paths = _tracked_path_set(repo_root)
    tracked_ancestor_dirs = _tracked_ancestor_dirs(repo_root)
    route_metadata = _reports_registered_route_metadata(repo_root)
    retention_metadata = _reports_retention_metadata(repo_root)
    rows: dict[str, ReportsWorkspaceEvidence] = {}
    collector_kwargs = {
        "route_metadata": route_metadata,
        "retention_metadata": retention_metadata,
        "rows": rows,
    }
    _collect_retained_report_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    _collect_local_prune_dir_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    _collect_registered_route_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    _collect_root_prune_report_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    _collect_transient_retained_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    _collect_uncurated_surface_rows(
        repo_root, tracked_paths, tracked_ancestor_dirs, **collector_kwargs
    )
    return sorted(rows.values(), key=lambda item: (item.classification, item.rel_path))


def _dedupe_candidates(candidates: list[CleanupCandidate]) -> list[CleanupCandidate]:
    deduped: dict[tuple[str, str], CleanupCandidate] = {}
    for candidate in candidates:
        deduped[(candidate.category, candidate.rel_path)] = candidate
    return sorted(
        deduped.values(), key=lambda candidate: (candidate.rel_path, candidate.category)
    )


def _candidate_classification(candidate: CleanupCandidate) -> str:
    return "SAFE" if candidate.apply_allowed else "REVIEW_REQUIRED"


def _review_evidence_classification(row: ReviewLaneEvidence) -> str:
    if row.classification == "blocked_cleanup_zone":
        return "BLOCKED"
    if row.classification == "security_review_required":
        return "SECURITY_REVIEW_REQUIRED"
    return "REVIEW_REQUIRED"


def _summarize_classifications(
    *,
    candidates: list[CleanupCandidate],
    review_evidence: list[ReviewLaneEvidence],
) -> dict[str, int]:
    summary = {
        "SAFE": 0,
        "REVIEW_REQUIRED": 0,
        "SECURITY_REVIEW_REQUIRED": 0,
        "BLOCKED": 0,
    }
    for candidate in candidates:
        summary[_candidate_classification(candidate)] += 1
    for row in review_evidence:
        summary[_review_evidence_classification(row)] += 1
    return summary


def _summarize_root_review(
    *,
    mismatches: list[RootPolicyMismatch],
    review_evidence: list[ReviewLaneEvidence],
) -> dict[str, int]:
    return {
        "ROOT_POLICY_MISMATCH": len(mismatches),
        "REVIEW_REQUIRED": sum(
            1
            for row in review_evidence
            if _review_evidence_classification(row) == "REVIEW_REQUIRED"
        ),
        "SECURITY_REVIEW_REQUIRED": sum(
            1
            for row in review_evidence
            if _review_evidence_classification(row) == "SECURITY_REVIEW_REQUIRED"
        ),
        "BLOCKED": sum(
            1
            for row in review_evidence
            if _review_evidence_classification(row) == "BLOCKED"
        ),
    }


def _summarize_reports_workspace(
    reports_evidence: list[ReportsWorkspaceEvidence],
) -> dict[str, int]:
    summary = {"PRUNE_CANDIDATE": 0, "RETAIN": 0, "REVIEW_REQUIRED": 0}
    for row in reports_evidence:
        summary[row.classification] += 1
    return summary


def build_cleanup_classification_report(
    repo_root: Path,
    *,
    candidates: list[CleanupCandidate],
    review_evidence: list[ReviewLaneEvidence],
    mode: str = "dry-run",
) -> dict[str, object]:
    """Build a deterministic machine-readable cleanup classification report."""
    return {
        "schema_version": 1,
        "tool": CLEANUP_REPOSITORY_TOOL,
        "mode": mode,
        "repository_root": repo_root.as_posix(),
        "safety_contract": {
            "non_destructive_dry_run": mode == "dry-run",
            "exact_candidates_only": True,
            "blocked_cleanup_zones_respected": True,
            "secret_env_files_excluded": True,
        },
        "summary": _summarize_classifications(
            candidates=candidates,
            review_evidence=review_evidence,
        ),
        "cleanup_candidates": [
            {
                "path": candidate.rel_path,
                "category": candidate.category,
                "classification": _candidate_classification(candidate),
                "tracked": candidate.tracked,
                "apply_allowed": candidate.apply_allowed,
                "reason": candidate.reason,
            }
            for candidate in candidates
        ],
        "root_review_evidence": [
            {
                "lane_id": row.lane_id,
                "path": row.rel_path,
                "classification": _review_evidence_classification(row),
                "registry_classification": row.classification,
                "current_live_state": row.current_live_state,
                "review_status": row.review_status,
                "exists": row.exists,
                "tracked": row.tracked,
                "has_history": row.has_history,
                "canonical_path": (
                    row.canonical_path.as_posix()
                    if row.canonical_path is not None
                    else None
                ),
                "canonical_exists": row.canonical_exists,
                "cmp_status": row.cmp_status,
                "reference_hits": row.reference_hits,
                "action_if_reintroduced": row.action_if_reintroduced,
                "owner": row.owner,
                "retention_class": row.retention_class,
                "retention_action": row.retention_action,
                "cleanup_policy": row.cleanup_policy,
            }
            for row in review_evidence
        ],
    }


def build_root_review_evidence_report(
    repo_root: Path,
    *,
    mismatches: list[RootPolicyMismatch],
    review_evidence: list[ReviewLaneEvidence],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": CLEANUP_REPOSITORY_TOOL,
        "repository_root": repo_root.as_posix(),
        "summary": _summarize_root_review(
            mismatches=mismatches,
            review_evidence=review_evidence,
        ),
        "root_policy_mismatches": [
            {
                "path": mismatch.rel_path,
                "mismatch_type": mismatch.mismatch_type,
                "tracked": mismatch.tracked,
            }
            for mismatch in mismatches
        ],
        "root_review_evidence": [
            {
                "lane_id": row.lane_id,
                "path": row.rel_path,
                "classification": _review_evidence_classification(row),
                "registry_classification": row.classification,
                "current_live_state": row.current_live_state,
                "review_status": row.review_status,
                "exists": row.exists,
                "tracked": row.tracked,
                "has_history": row.has_history,
                "canonical_path": (
                    row.canonical_path.as_posix()
                    if row.canonical_path is not None
                    else None
                ),
                "canonical_exists": row.canonical_exists,
                "cmp_status": row.cmp_status,
                "reference_hits": row.reference_hits,
                "action_if_reintroduced": row.action_if_reintroduced,
                "owner": row.owner,
                "retention_class": row.retention_class,
                "retention_action": row.retention_action,
                "cleanup_policy": row.cleanup_policy,
            }
            for row in review_evidence
        ],
    }


def build_reports_workspace_review_report(
    repo_root: Path,
    *,
    reports_evidence: list[ReportsWorkspaceEvidence],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": CLEANUP_REPOSITORY_TOOL,
        "repository_root": repo_root.as_posix(),
        "summary": _summarize_reports_workspace(reports_evidence),
        "reports_workspace_evidence": [
            {
                "path": row.rel_path,
                "classification": row.classification,
                "tracked": row.tracked,
                "exists": row.exists,
                "has_history": row.has_history,
                "reference_hits": row.reference_hits,
                "generator": row.generator,
                "commit_policy": row.commit_policy,
                "retention_entry_id": row.retention_entry_id,
                "retention_owner": row.retention_owner,
                "retention_ttl_days": row.retention_ttl_days,
                "age_days": row.age_days,
                "ttl_expired": row.ttl_expired,
                "reason": row.reason,
            }
            for row in reports_evidence
        ],
    }


def write_cleanup_classification_report(
    repo_root: Path,
    report_path: Path,
    report: dict[str, object],
) -> Path:
    target = report_path if report_path.is_absolute() else repo_root / report_path
    target.parent.mkdir(parents=True, exist_ok=True)
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    target = resolve_output_path(target, root=REPO_ROOT)
    target.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def collect_cleanup_candidates(
    repo_root: Path,
    *,
    include_cache: bool = True,
    include_temp: bool = True,
    include_root_review: bool = True,
    root_only_local_scan: bool = False,
) -> list[CleanupCandidate]:
    policy = load_root_governance_policy(repo_root)
    candidates: list[CleanupCandidate] = []
    status_paths = None if root_only_local_scan else _local_status_paths(repo_root)

    if include_cache:
        if root_only_local_scan:
            candidates.extend(
                _iter_root_local_dir_candidates(
                    repo_root,
                    blocked_paths=policy.blocked_cleanup_paths,
                )
            )
        else:
            candidates.extend(
                _iter_local_dir_candidates(
                    repo_root,
                    blocked_paths=policy.blocked_cleanup_paths,
                    status_paths=status_paths,
                )
            )
    if include_temp:
        if root_only_local_scan:
            candidates.extend(
                _iter_root_local_file_candidates(
                    repo_root,
                    blocked_paths=policy.blocked_cleanup_paths,
                )
            )
        else:
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
                    raise OSError(
                        f"directory still exists after cleanup: {candidate.rel_path}"
                    )
            elif target.exists():
                target.unlink()
            deleted.append(candidate)
        except OSError as exc:
            errors.append(f"{candidate.rel_path}: {exc}")
    return deleted, errors


def _apply_reports_workspace_prune(
    repo_root: Path,
    reports_evidence: list[ReportsWorkspaceEvidence],
) -> tuple[list[str], list[str]]:
    deleted: list[str] = []
    errors: list[str] = []
    for row in reports_evidence:
        if row.classification != "PRUNE_CANDIDATE" or row.tracked:
            continue
        target = repo_root / row.path
        if not target.exists():
            continue
        try:
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                if target.exists():
                    raise OSError(
                        f"directory still exists after cleanup: {row.rel_path}"
                    )
            else:
                target.unlink()
            deleted.append(row.rel_path)
        except OSError as exc:
            errors.append(f"{row.rel_path}: {exc}")
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


def _log_root_policy_mismatches(
    mismatches: list[RootPolicyMismatch],
    *,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> None:
    if not mismatches:
        return
    logger.info("## ROOT POLICY MISMATCHES (%d)", len(mismatches))
    visible_rows = mismatches[:detail_limit]
    for row in visible_rows:
        logger.info(
            "  [%s] %s",
            row.mismatch_type,
            row.rel_path,
        )
    hidden_count = len(mismatches) - len(visible_rows)
    if hidden_count > 0:
        logger.info("  ... %d additional mismatch row(s) omitted", hidden_count)
    logger.info("")


def _format_optional_scalar(value: object) -> str:
    return str(value) if value is not None else "n/a"


def _log_one_reports_workspace_row(row: ReportsWorkspaceEvidence) -> None:
    logger.info(
        (
            "  %s | exists=%s tracked=%s history=%s refs=%d route=%s "
            "policy=%s ttl=%s age_days=%s ttl_expired=%s owner=%s"
        ),
        row.rel_path,
        str(row.exists).lower(),
        str(row.tracked).lower(),
        str(row.has_history).lower(),
        row.reference_hits,
        row.generator or "n/a",
        row.commit_policy or "n/a",
        _format_optional_scalar(row.retention_ttl_days),
        _format_optional_scalar(row.age_days),
        str(row.ttl_expired).lower() if row.ttl_expired is not None else "n/a",
        row.retention_owner or "n/a",
    )
    logger.info("      %s", row.reason)


def _log_reports_workspace_evidence(
    rows: list[ReportsWorkspaceEvidence],
    *,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> None:
    if not rows:
        return

    groups: dict[str, list[ReportsWorkspaceEvidence]] = {}
    for row in rows:
        groups.setdefault(row.classification, []).append(row)

    logger.info("## REPORTS WORKSPACE EVIDENCE")
    for classification in sorted(groups):
        evidence_rows = groups[classification]
        visible_rows = evidence_rows[:detail_limit]
        logger.info("### %s (%d)", classification, len(evidence_rows))
        for row in visible_rows:
            _log_one_reports_workspace_row(row)
        hidden_count = len(evidence_rows) - len(visible_rows)
        if hidden_count > 0:
            logger.info("  ... %d additional reports row(s) omitted", hidden_count)
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
        "--apply-reports-prune",
        action="store_true",
        help="Delete only exact untracked reports workspace prune candidates",
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
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write a machine-readable cleanup classification report to this path",
    )
    parser.add_argument(
        "--report-root-review-json",
        type=Path,
        help="Write root-policy mismatches and review-lane evidence to this path",
    )
    parser.add_argument(
        "--report-reports-workspace-json",
        type=Path,
        help="Write reports workspace inventory/classification evidence to this path",
    )
    return parser.parse_args()


def _classification_mode(args: argparse.Namespace) -> str:
    if args.apply:
        return "apply"
    if args.apply_reports_prune:
        return "apply-reports-prune"
    return "dry-run"


def _log_root_and_reports_evidence(
    *,
    args: argparse.Namespace,
    root_policy_mismatches: list[object],
    review_evidence: list[object],
    reports_evidence: object,
) -> None:
    detail_limit = max(args.detail_limit, 0)
    if args.root:
        _log_root_policy_mismatches(
            root_policy_mismatches, detail_limit=detail_limit
        )
        _log_review_lane_evidence(review_evidence, detail_limit=detail_limit)
    _log_reports_workspace_evidence(reports_evidence, detail_limit=detail_limit)


def main() -> int:
    args = parse_args()
    repo_root = _discover_repo_root(args.path)
    if args.dry_run and (args.apply or args.apply_reports_prune):
        logger.error("Use --dry-run without apply modes.")
        return 2

    root_hygiene_fast_local_scan = (
        args.dry_run
        and not args.apply
        and not args.apply_reports_prune
        and args.detail_limit == 0
    )

    candidates = collect_cleanup_candidates(
        repo_root,
        include_cache=args.cache,
        include_temp=args.temp,
        include_root_review=args.root,
        root_only_local_scan=root_hygiene_fast_local_scan,
    )
    _log_candidates(candidates, detail_limit=max(args.detail_limit, 0))
    review_evidence = collect_root_review_evidence(repo_root) if args.root else []
    root_policy_mismatches = (
        collect_root_policy_mismatches(repo_root) if args.root else []
    )
    reports_evidence = collect_reports_workspace_evidence(repo_root)
    _log_root_and_reports_evidence(
        args=args,
        root_policy_mismatches=root_policy_mismatches,
        review_evidence=review_evidence,
        reports_evidence=reports_evidence,
    )
    if args.report_json is not None:
        report_path = write_cleanup_classification_report(
            repo_root,
            args.report_json,
            build_cleanup_classification_report(
                repo_root,
                candidates=candidates,
                review_evidence=review_evidence,
                mode=_classification_mode(args),
            ),
        )
        logger.info("Wrote cleanup classification report: %s", report_path)
    if args.report_root_review_json is not None:
        report_path = write_cleanup_classification_report(
            repo_root,
            args.report_root_review_json,
            build_root_review_evidence_report(
                repo_root,
                mismatches=root_policy_mismatches,
                review_evidence=review_evidence,
            ),
        )
        logger.info("Wrote root review evidence report: %s", report_path)
    if args.report_reports_workspace_json is not None:
        report_path = write_cleanup_classification_report(
            repo_root,
            args.report_reports_workspace_json,
            build_reports_workspace_review_report(
                repo_root,
                reports_evidence=reports_evidence,
            ),
        )
        logger.info("Wrote reports workspace review report: %s", report_path)

    apply_errors: list[str] = []
    deleted_reports: list[str] = []
    if args.apply_reports_prune:
        deleted_reports, reports_errors = _apply_reports_workspace_prune(
            repo_root,
            reports_evidence,
        )
        apply_errors.extend(reports_errors)
        logger.info(
            "Deleted reports workspace prune candidates: %d", len(deleted_reports)
        )

    if not args.apply:
        return 1 if apply_errors else 0

    deleted, errors = _apply_local_candidates(repo_root, candidates)
    skipped_review = [
        candidate for candidate in candidates if not candidate.apply_allowed
    ]
    _log_apply_summary(
        deleted=deleted,
        skipped_review=skipped_review,
        errors=errors + apply_errors,
    )
    return 1 if errors or apply_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
