"""Unit tests for root-hygiene review registry validator."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.repo import check_root_hygiene_review_registry as module


pytestmark = pytest.mark.unit

def test_validate_baseline_requires_strict_audit_command() -> None:
    issues = module._validate_baseline(
        {
            "current_live_root_baseline": {
                "tracked_root_audit_status": "pass",
                "strict_untracked_root_audit_status": "pass",
                "verification_command": "python scripts/engineering/repo/audit_root_cleanliness.py",
            }
        }
    )

    assert issues == [
        "verification_command must reference audit_root_cleanliness.py --strict-untracked"
    ]


def test_validate_review_lanes_rejects_present_missing_path(tmp_path: Path) -> None:
    payload = {
        "review_lanes": [
            {
                "lane_id": "lane",
                "classification": "review_required",
                "verification": ["git ls-files foo"],
                "candidates": [
                    {
                        "path": "missing-root-path",
                        "current_live_state": "present_approved_root_surface",
                        "canonical_path": None,
                    }
                ],
            }
        ]
    }

    issues = module._validate_review_lanes(payload, repo_root=tmp_path)

    assert issues == [
        "missing-root-path: marked present but path is missing",
    ]


def test_validate_blocked_lane_matches_catalog(tmp_path: Path) -> None:
    registry = {
        "review_lanes": [
            {
                "lane_id": "retention_sensitive_boundaries",
                "classification": "blocked_cleanup_zone",
                "verification": [
                    "docs/05-operations/runbooks/retention-sensitive-cleanup.md"
                ],
                "candidates": [
                    {
                        "path": "data",
                        "current_live_state": "present_blocked_cleanup_zone",
                        "canonical_path": None,
                        "cleanup_runbook": "docs/05-operations/runbooks/retention-sensitive-cleanup.md",
                    }
                ],
            }
        ]
    }
    catalog = {
        "blocked_cleanup_zones": [
            {
                "path": "data",
                "cleanup_runbook": "docs/05-operations/runbooks/retention-sensitive-cleanup.md",
            }
        ]
    }

    issues = module._validate_blocked_lane_against_catalog(registry, catalog)

    assert issues == []


def test_validate_review_lanes_accepts_absent_transient_root_candidates(
    tmp_path: Path,
) -> None:
    canonical_path = (
        tmp_path / "reports" / "observability" / "runtime_cardinality_inventory.json"
    )
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text("{}", encoding="utf-8")

    payload = {
        "review_lanes": [
            {
                "lane_id": "root_transient_helpers_and_outputs",
                "classification": "review_required",
                "verification": ["git ls-files temp_helper.py artifacts"],
                "candidates": [
                    {
                        "path": "artifacts",
                        "current_live_state": "absent_from_root_baseline",
                        "canonical_path": "reports/observability/runtime_cardinality_inventory.json",
                    },
                    {
                        "path": "temp_helper.py",
                        "current_live_state": "absent_from_root_baseline",
                        "canonical_path": None,
                    },
                ],
            }
        ]
    }

    issues = module._validate_review_lanes(payload, repo_root=tmp_path)

    assert issues == []


def test_validate_review_lanes_accepts_present_local_only_codex_tmp(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex_tmp").mkdir()

    payload = {
        "review_lanes": [
            {
                "lane_id": "local_runtime_root_dirs",
                "classification": "review_required",
                "verification": ["git check-ignore -v .codex_tmp"],
                "candidates": [
                    {
                        "path": ".codex_tmp",
                        "current_live_state": "present_local_only_root_surface",
                        "canonical_path": None,
                    }
                ],
            }
        ]
    }

    issues = module._validate_review_lanes(payload, repo_root=tmp_path)

    assert issues == []


def test_validate_review_lanes_accepts_missing_present_local_only_surface(
    tmp_path: Path,
) -> None:
    payload = {
        "review_lanes": [
            {
                "lane_id": "local_runtime_root_dirs",
                "classification": "review_required",
                "verification": ["git check-ignore -v .qodo"],
                "candidates": [
                    {
                        "path": ".qodo",
                        "current_live_state": "present_local_only_root_surface",
                        "canonical_path": None,
                    }
                ],
            }
        ]
    }

    issues = module._validate_review_lanes(payload, repo_root=tmp_path)

    assert issues == []


def test_load_yaml_object_requires_mapping(tmp_path: Path) -> None:
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(["not", "a", "mapping"]), encoding="utf-8")

    try:
        module._load_yaml_object(path)
    except ValueError as exc:
        assert str(exc) == f"{path} must contain a YAML object"
    else:
        raise AssertionError("Expected ValueError for non-mapping YAML payload")
