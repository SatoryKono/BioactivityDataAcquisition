#!/usr/bin/env python3
"""Operator command for reviewed root-local clutter cleanup.

The command intentionally operates on exact root candidates from
configs/quality/root_hygiene_review_registry.yaml. It does not perform a
recursive repository cleanup and it never targets secret-bearing env files or
retention-sensitive zones.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.engineering.repo._root_governance import (
    is_within_blocked_cleanup_zone,
    load_root_governance_policy,
)

ROOT_HYGIENE_REVIEW_REGISTRY = Path("configs/quality/root_hygiene_review_registry.yaml")
SAFE_ROOT_LOCAL_PATHS: frozenset[str] = frozenset(
    {
        ".benchmarks",
        ".coverage",
        ".coverage-sharded-current-main",
        ".hypothesis",
        ".import_linter_cache",
        ".pytest_cache",
        ".ruff_cache",
        "test-output",
        "tmp",
    }
)
VENV_ROOT_LOCAL_PATHS: frozenset[str] = frozenset(
    {".venv", ".venv-docs", ".venv-win", ".venv-win-corrupt"}
)
DEPENDENCY_ROOT_LOCAL_PATHS: frozenset[str] = frozenset({"node_modules", ".npm-cache"})
LOG_ROOT_LOCAL_PATHS: frozenset[str] = frozenset({"logs"})
SECURITY_ROOT_PATHS: frozenset[str] = frozenset({".env", ".env.local", "new.env"})
ALLOWED_LANES: frozenset[str] = frozenset(
    {
        "local_runtime_root_dirs",
        "root_transient_helpers_and_outputs",
    }
)


@dataclass(frozen=True)
class RootLocalCleanupCandidate:
    """Exact root-local clutter candidate approved by root review registry."""

    path: Path
    lane_id: str
    category: str
    reason: str

    @property
    def rel_path(self) -> str:
        return self.path.as_posix()


def _project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path(__file__).resolve().parents[3]


def _load_yaml_object(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a YAML object")
    return payload


def _registry_candidates(repo_root: Path) -> list[tuple[str, dict[str, Any]]]:
    payload = _load_yaml_object(repo_root / ROOT_HYGIENE_REVIEW_REGISTRY)
    lanes = payload.get("review_lanes")
    if not isinstance(lanes, list):
        raise RuntimeError("root hygiene registry must define review_lanes")

    rows: list[tuple[str, dict[str, Any]]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = lane.get("lane_id")
        candidates = lane.get("candidates")
        if not isinstance(lane_id, str) or not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if isinstance(candidate, dict):
                rows.append((lane_id, candidate))
    return rows


def _tracked_paths(repo_root: Path) -> frozenset[str]:
    try:
        completed = subprocess.run(  # nosec
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError):
        return frozenset()
    return frozenset(
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    )


def _path_is_tracked(path: str, tracked_paths: frozenset[str]) -> bool:
    return path in tracked_paths or any(
        tracked_path.startswith(f"{path}/") for tracked_path in tracked_paths
    )


def _allowed_cleanup_paths(
    *,
    include_venv: bool,
    include_dependency_trees: bool,
    include_logs: bool,
) -> frozenset[str]:
    allowed = set(SAFE_ROOT_LOCAL_PATHS)
    if include_venv:
        allowed.update(VENV_ROOT_LOCAL_PATHS)
    if include_dependency_trees:
        allowed.update(DEPENDENCY_ROOT_LOCAL_PATHS)
    if include_logs:
        allowed.update(LOG_ROOT_LOCAL_PATHS)
    return frozenset(allowed)


def collect_root_local_cleanup_candidates(
    repo_root: Path,
    *,
    include_venv: bool = False,
    include_dependency_trees: bool = False,
    include_logs: bool = False,
    only_paths: frozenset[str] = frozenset(),
) -> list[RootLocalCleanupCandidate]:
    """Return exact reviewed root-local cleanup candidates that exist now."""

    policy = load_root_governance_policy(repo_root)
    tracked_paths = _tracked_paths(repo_root)
    allowed_paths = _allowed_cleanup_paths(
        include_venv=include_venv,
        include_dependency_trees=include_dependency_trees,
        include_logs=include_logs,
    )
    selected_paths = only_paths or allowed_paths
    candidates: list[RootLocalCleanupCandidate] = []

    for lane_id, row in _registry_candidates(repo_root):
        raw_path = row.get("path")
        live_state = row.get("current_live_state")
        if lane_id not in ALLOWED_LANES or not isinstance(raw_path, str):
            continue
        if raw_path not in selected_paths or raw_path not in allowed_paths:
            continue
        if raw_path in SECURITY_ROOT_PATHS or "/" in raw_path:
            continue
        if live_state != "present_local_only_root_surface":
            continue
        if is_within_blocked_cleanup_zone(raw_path, policy.blocked_cleanup_paths):
            continue
        if _path_is_tracked(raw_path, tracked_paths):
            continue

        absolute_path = repo_root / raw_path
        if not absolute_path.exists() and not absolute_path.is_symlink():
            continue
        candidates.append(
            RootLocalCleanupCandidate(
                path=Path(raw_path),
                lane_id=lane_id,
                category=_candidate_category(raw_path),
                reason=str(row.get("action_if_reintroduced", "")),
            )
        )

    return sorted(candidates, key=lambda candidate: candidate.rel_path)


def _candidate_category(path: str) -> str:
    if path in VENV_ROOT_LOCAL_PATHS:
        return "local_virtualenv"
    if path in DEPENDENCY_ROOT_LOCAL_PATHS:
        return "local_dependency_tree"
    if path in LOG_ROOT_LOCAL_PATHS:
        return "local_logs"
    if path.startswith(".coverage"):
        return "coverage"
    if path in {"test-output", "tmp"}:
        return "test_or_temp_output"
    return "local_cache"


def _delete_candidate(repo_root: Path, candidate: RootLocalCleanupCandidate) -> None:
    target = repo_root / candidate.path
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    if target.is_dir():
        shutil.rmtree(target)


def _report_rows(candidates: list[RootLocalCleanupCandidate]) -> list[dict[str, str]]:
    return [
        {
            "path": candidate.rel_path,
            "lane_id": candidate.lane_id,
            "category": candidate.category,
            "reason": candidate.reason,
        }
        for candidate in candidates
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="Delete listed paths")
    parser.add_argument(
        "--include-venv",
        action="store_true",
        help="Include reviewed local virtualenv roots",
    )
    parser.add_argument(
        "--include-dependency-trees",
        action="store_true",
        help="Include reviewed local dependency/cache trees such as node_modules",
    )
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Include reviewed root logs/ local-only surface",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Limit cleanup to an exact reviewed root-local path",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = _project_root()
    candidates = collect_root_local_cleanup_candidates(
        repo_root,
        include_venv=args.include_venv,
        include_dependency_trees=args.include_dependency_trees,
        include_logs=args.include_logs,
        only_paths=frozenset(args.path),
    )

    deleted: list[str] = []
    if args.apply:
        for candidate in candidates:
            _delete_candidate(repo_root, candidate)
            deleted.append(candidate.rel_path)

    payload = {
        "schema_version": 1,
        "mode": "apply" if args.apply else "dry-run",
        "repository_root": repo_root.as_posix(),
        "candidate_count": len(candidates),
        "deleted": deleted,
        "candidates": _report_rows(candidates),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(f"Root-local cleanup mode: {payload['mode']}")
    if not candidates:
        print("No reviewed root-local cleanup candidates found.")
        return 0
    for row in payload["candidates"]:
        print(f"- {row['path']} ({row['category']}, {row['lane_id']})")
    if not args.apply:
        print("Dry-run only. Re-run with --apply to delete these exact paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
