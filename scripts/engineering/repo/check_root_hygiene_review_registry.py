#!/usr/bin/env python3
"""Validate root-hygiene remediation review registry."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

import yaml

ROOT_HYGIENE_REVIEW_REGISTRY: Final[Path] = Path(
    "configs/quality/root_hygiene_review_registry.yaml"
)
STRUCTURE_CATALOG: Final[Path] = Path("configs/quality/repo_structure_catalog.yaml")
ALLOWED_CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {
        "blocked_cleanup_zone",
        "owner_decision_required",
        "review_required",
        "security_review_required",
    }
)
ALLOWED_LIVE_STATES: Final[frozenset[str]] = frozenset(
    {
        "absent_from_root_baseline",
        "present_approved_root_surface",
        "present_blocked_cleanup_zone",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_yaml_object(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def _validate_baseline(payload: dict[str, object]) -> list[str]:
    issues: list[str] = []
    baseline = payload.get("current_live_root_baseline")
    if not isinstance(baseline, dict):
        return ["current_live_root_baseline must be an object"]
    if baseline.get("tracked_root_audit_status") != "pass":
        issues.append("tracked_root_audit_status must be 'pass'")
    if baseline.get("strict_untracked_root_audit_status") != "pass":
        issues.append("strict_untracked_root_audit_status must be 'pass'")
    command = str(baseline.get("verification_command", ""))
    if "audit_root_cleanliness.py --strict-untracked" not in command:
        issues.append(
            "verification_command must reference audit_root_cleanliness.py --strict-untracked"
        )
    return issues


def _validate_review_lanes(
    payload: dict[str, object],
    *,
    repo_root: Path,
) -> list[str]:
    issues: list[str] = []
    lanes = payload.get("review_lanes")
    if not isinstance(lanes, list) or not lanes:
        return ["review_lanes must be a non-empty list"]

    seen_lane_ids: set[str] = set()
    seen_paths: set[str] = set()
    for lane in lanes:
        lane_id = _validate_review_lane_object(
            lane,
            issues=issues,
            seen_lane_ids=seen_lane_ids,
        )
        if lane_id is None or not isinstance(lane, dict):
            continue
        _validate_review_lane_candidates(
            lane,
            lane_id=lane_id,
            repo_root=repo_root,
            seen_paths=seen_paths,
            issues=issues,
        )
    return issues


def _validate_review_lane_object(
    lane: object,
    *,
    issues: list[str],
    seen_lane_ids: set[str],
) -> str | None:
    if not isinstance(lane, dict):
        issues.append("Each review lane must be an object")
        return None

    lane_id = lane.get("lane_id")
    if not isinstance(lane_id, str) or not lane_id:
        issues.append("Each review lane must define a non-empty lane_id")
        return None
    if lane_id in seen_lane_ids:
        issues.append(f"Duplicate lane_id: {lane_id}")
    seen_lane_ids.add(lane_id)

    classification = lane.get("classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        issues.append(f"Lane {lane_id} has unsupported classification: {classification}")

    verification = lane.get("verification")
    if not isinstance(verification, list) or not verification:
        issues.append(f"Lane {lane_id} must declare verification commands")

    return lane_id


def _validate_review_lane_candidates(
    lane: dict[str, object],
    *,
    lane_id: str,
    repo_root: Path,
    seen_paths: set[str],
    issues: list[str],
) -> None:
    candidates = lane.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        issues.append(f"Lane {lane_id} must contain at least one candidate")
        return

    for candidate in candidates:
        _validate_review_lane_candidate(
            candidate,
            lane_id=lane_id,
            repo_root=repo_root,
            seen_paths=seen_paths,
            issues=issues,
        )


def _validate_review_lane_candidate(
    candidate: object,
    *,
    lane_id: str,
    repo_root: Path,
    seen_paths: set[str],
    issues: list[str],
) -> None:
    if not isinstance(candidate, dict):
        issues.append(f"Lane {lane_id} contains a non-object candidate")
        return

    path = candidate.get("path")
    if not isinstance(path, str) or not path:
        issues.append(f"Lane {lane_id} contains candidate without path")
        return
    if path in seen_paths:
        issues.append(f"Duplicate candidate path: {path}")
    seen_paths.add(path)

    live_state = candidate.get("current_live_state")
    if live_state not in ALLOWED_LIVE_STATES:
        issues.append(f"{path}: unsupported current_live_state {live_state}")
        return

    _validate_candidate_live_state(path, live_state=live_state, repo_root=repo_root, issues=issues)
    _validate_candidate_canonical_path(path, candidate, repo_root=repo_root, issues=issues)


def _validate_candidate_live_state(
    path: str,
    *,
    live_state: object,
    repo_root: Path,
    issues: list[str],
) -> None:
    abs_path = repo_root / path
    if live_state == "absent_from_root_baseline" and abs_path.exists():
        issues.append(f"{path}: marked absent_from_root_baseline but path exists")
    if live_state != "absent_from_root_baseline" and not abs_path.exists():
        issues.append(f"{path}: marked present but path is missing")


def _validate_candidate_canonical_path(
    path: str,
    candidate: dict[str, object],
    *,
    repo_root: Path,
    issues: list[str],
) -> None:
    canonical_path = candidate.get("canonical_path")
    if isinstance(canonical_path, str) and canonical_path:
        if not (repo_root / canonical_path).exists():
            issues.append(f"{path}: canonical_path does not exist: {canonical_path}")


def _validate_blocked_lane_against_catalog(
    payload: dict[str, object], catalog: dict[str, object]
) -> list[str]:
    blocked_candidates, lane_issues = _blocked_lane_candidates(payload)
    if lane_issues:
        return lane_issues
    catalog_zones, catalog_issues = _catalog_blocked_cleanup_zones(catalog)
    if catalog_issues:
        return catalog_issues

    issues = _blocked_lane_path_issues(blocked_candidates, catalog_zones)
    issues.extend(_blocked_lane_runbook_issues(blocked_candidates, catalog_zones))
    return issues


def _blocked_lane_candidates(
    payload: dict[str, object],
) -> tuple[list[object], list[str]]:
    lanes = payload.get("review_lanes")
    if not isinstance(lanes, list):
        return [], ["review_lanes must be a list"]
    blocked_lane = _find_retention_sensitive_lane(lanes)
    if blocked_lane is None:
        return [], ["Missing review lane: retention_sensitive_boundaries"]
    blocked_candidates = blocked_lane.get("candidates")
    if not isinstance(blocked_candidates, list):
        return [], ["retention_sensitive_boundaries candidates must be a list"]
    return blocked_candidates, []


def _catalog_blocked_cleanup_zones(
    catalog: dict[str, object],
) -> tuple[list[object], list[str]]:
    catalog_zones = catalog.get("blocked_cleanup_zones")
    if not isinstance(catalog_zones, list):
        return [], ["blocked_cleanup_zones must be a list in repo_structure_catalog"]
    return catalog_zones, []


def _blocked_lane_path_issues(
    blocked_candidates: list[object],
    catalog_zones: list[object],
) -> list[str]:
    if _blocked_lane_paths(blocked_candidates) == _catalog_blocked_paths(catalog_zones):
        return []
    return [
        "retention_sensitive_boundaries candidates must match "
        "configs/quality/repo_structure_catalog.yaml blocked_cleanup_zones"
    ]


def _find_retention_sensitive_lane(
    lanes: list[object],
) -> dict[str, object] | None:
    blocked_lane = next(
        (
            lane
            for lane in lanes
            if isinstance(lane, dict)
            and lane.get("lane_id") == "retention_sensitive_boundaries"
        ),
        None,
    )
    return blocked_lane if isinstance(blocked_lane, dict) else None


def _blocked_lane_paths(blocked_candidates: list[object]) -> set[str]:
    return {
        candidate["path"]
        for candidate in blocked_candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }


def _catalog_blocked_paths(catalog_zones: list[object]) -> set[str]:
    return {
        zone["path"]
        for zone in catalog_zones
        if isinstance(zone, dict) and isinstance(zone.get("path"), str)
    }


def _blocked_lane_runbook_issues(
    blocked_candidates: list[object],
    catalog_zones: list[object],
) -> list[str]:
    issues: list[str] = []
    catalog_runbooks = {
        zone["path"]: zone.get("cleanup_runbook")
        for zone in catalog_zones
        if isinstance(zone, dict) and isinstance(zone.get("path"), str)
    }
    for candidate in blocked_candidates:
        if not isinstance(candidate, dict):
            continue
        path = candidate.get("path")
        if not isinstance(path, str) or path not in catalog_runbooks:
            continue
        if candidate.get("cleanup_runbook") != catalog_runbooks[path]:
            issues.append(
                f"{path}: cleanup_runbook mismatch with repo_structure_catalog"
            )
    return issues


def main() -> int:
    repo_root = _project_root()
    registry_path = repo_root / ROOT_HYGIENE_REVIEW_REGISTRY
    catalog_path = repo_root / STRUCTURE_CATALOG

    try:
        payload = _load_yaml_object(registry_path)
        catalog = _load_yaml_object(catalog_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"[FAIL] Root hygiene review registry validation failed: {exc}")
        return 1

    issues: list[str] = []
    issues.extend(_validate_baseline(payload))
    issues.extend(_validate_review_lanes(payload, repo_root=repo_root))
    issues.extend(_validate_blocked_lane_against_catalog(payload, catalog))

    if issues:
        print(f"[FAIL] Root hygiene review registry validation failed: {registry_path}")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print(f"[OK] Root hygiene review registry is valid: {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
