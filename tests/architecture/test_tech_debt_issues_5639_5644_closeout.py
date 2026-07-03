"""Closeout guards for technical-debt issues #5639 through #5644."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.application.services.control_plane.manifest.diagnostics.base_effective_config_diagnostics import (
    _build_effective_config_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.main_helpers import (
    _build_unified_reproducibility_diagnostics_semantic_identity,
)
from bioetl.composition.bootstrap.runtime import composite as composite_runtime
from bioetl.composition.bootstrap.runtime import composite_support_helpers

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5639-5644-closeout.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
SERVICES_FACTORY = ROOT / "src" / "bioetl" / "composition" / "factories" / "services" / "factory.py"
COMPOSITE_RUNTIME = (
    ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "runtime" / "composite.py"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _latest_report(pattern: str) -> Path:
    matches = sorted((ROOT / "reports" / "quality").glob(pattern))
    assert matches, f"missing report matching {pattern}"
    return matches[-1]


def test_closeout_artifact_covers_requested_issues__5639_5644() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5639-5644-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == {5639, 5640, 5641, 5644}
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5639_architecture_debt_planner_tracks_live_artifact_backlog() -> None:
    tasks = _load_json(
        ROOT / "reports" / "quality" / "tasks_architecture_metric_exemptions_2026-06-26-15-51.json"
    )
    plan = _load_json(
        ROOT / "reports" / "quality" / "architecture_debt_execution_plan_2026-06-26-15-51.json"
    )

    assert tasks["registry_summary"]["total_tasks"] > 0
    assert plan["summary"]["total_tasks"] > 0
    assert plan["summary"]["actionable_tasks"] > 0
    counts = plan["summary"]["category_counts"]
    assert counts["COMPATIBILITY_DEBT"] > 0
    assert counts["DUPLICATION"] > 0
    assert counts["HOTSPOT_SIZE_COUPLING_DEBT"] > 0
    assert counts["DEAD_CODE_REVIEW_DEBT"] > 0
    assert plan["execution_order"][:4] == [
        "COMPATIBILITY_DEBT",
        "DUPLICATION",
        "HOTSPOT_SIZE_COUPLING_DEBT",
        "DEAD_CODE_REVIEW_DEBT",
    ]


def test_issue_5640_stable_public_seams_are_governed_outside_compatibility_debt() -> None:
    scorecard = _load_yaml(DEBT_SCORECARD)
    census = _load_json(COMPATIBILITY_CENSUS)
    registry = _load_yaml(COMPATIBILITY_REGISTRY)

    compatibility_metrics = scorecard["compatibility_debt_metrics"]["metrics"]
    assert set(compatibility_metrics) == {
        "transition_compat_count",
        "sunset_compat_count",
        "expired_compat_count",
    }

    governance_metrics = scorecard["sanctioned_public_entrypoint_governance"]["metrics"]
    assert governance_metrics["public_entrypoint_count"]["current_count"] == len(
        registry["retained_entrypoints"]
    )
    assert governance_metrics["public_export_facade_count"]["current_count"] == int(
        census["summary"]["retained_public_export_facade_count"]
    )
    assert (
        governance_metrics["public_export_facade_conflict_count"]["current_count"]
        == 0
    )


def test_issue_5641_local_storage_and_runtime_wrapper_seams_are_collapsed() -> None:
    services_factory_text = SERVICES_FACTORY.read_text(encoding="utf-8")
    composite_runtime_text = COMPOSITE_RUNTIME.read_text(encoding="utf-8")

    assert "class _LazyStorageFactory" not in services_factory_text
    assert (
        "from bioetl.composition.factories.services.common_service_wiring import"
        in services_factory_text
    )
    assert "StorageFactory" in services_factory_text
    assert "def _load_field_group_registry(" not in composite_runtime_text
    assert (
        composite_runtime._load_field_group_registry
        is composite_support_helpers._load_field_group_registry
    )


def test_issue_5644_diagnostics_payloads_no_longer_emit_legacy_config_hash_aliases() -> (
    None
):
    summary = {
        "config_hash": "legacy-hash",
        "resolved_config_hash": "resolved-hash",
        "effective_config_hash": "effective-hash",
        "effective_config_artifact_id": "eca-1",
        "source_fingerprint": "source-fingerprint",
        "execution_fingerprint": "fingerprint-1",
        "input_snapshot_identity_fingerprint": "snapshot-fingerprint",
        "snapshot_status": "present",
        "input_snapshot_ids": ["snapshot-1"],
        "run_id": "run-1",
        "manifest_id": "manifest-1",
        "manifest_created_at": "2026-01-01T00:00:00+00:00",
    }

    effective_config = _build_effective_config_diagnostics(summary)
    semantic_identity = _build_unified_reproducibility_diagnostics_semantic_identity(
        summary
    )

    forbidden_keys = {
        "legacy_config_hash",
        "legacy_config_hash_alias_of",
        "legacy_config_hash_replay_identity_anchor",
        "config_hash_compatibility_anchor",
        "config_hash_legacy_alias_of",
    }
    assert forbidden_keys.isdisjoint(effective_config["semantic"])
    assert forbidden_keys.isdisjoint(semantic_identity)
    assert (
        effective_config["diff_policy"]["config_hash_policy"]
        == "resolved_and_effective_hashes_only"
    )
