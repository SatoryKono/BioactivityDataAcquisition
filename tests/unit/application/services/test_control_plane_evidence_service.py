"""Tests for bounded control-plane validation evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_evidence import (
    FAILURE_REASON_CATEGORIES,
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactReplayImpact,
    ControlPlaneArtifactSurface,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 9, tzinfo=UTC)
_RUN_ID = RunID(UUID("00000000-0000-0000-0000-000000008490"))


def _manifest(**overrides: object) -> RunManifest:
    values: dict[str, object] = {
        "manifest_id": "manifest-8490",
        "execution_fingerprint": "fingerprint-8490",
        "schema_version": "1.0",
        "created_at": _NOW,
        "run_id": _RUN_ID,
        "run_type": RunType.INCREMENTAL,
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "launch_context": {"required_persistence_profile": "replay_ready"},
        "code_provenance": RunCodeProvenance(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="1",
            effective_config_artifact_id="effective-config-8490",
        ),
    }
    values.update(overrides)
    return RunManifest(**values)  # type: ignore[arg-type]


def _scope(manifest: RunManifest | None = None) -> EvidenceScopeContext:
    resolved = manifest or _manifest()
    return EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=str(resolved.run_id),
        selected_run_types=("incremental",),
        resolved_via="selected_run_id",
        manifest=resolved,
    )


def _reasons(payload: dict[str, object]) -> set[str]:
    return {
        str(row["reason"])
        for row in payload["rows"]  # type: ignore[union-attr]
        if isinstance(row, dict)
    }


def _unresolved_scope(
    reason: str = "selected_run_id_not_found",
) -> EvidenceScopeContext:
    return EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=str(_RUN_ID),
        selected_run_types=("incremental",),
        resolved_via=reason,
        manifest=None,
    )


def _snapshot_manifest(**overrides: object) -> RunManifest:
    snapshot = RunInputSnapshotRef(
        snapshot_id="sha256:snapshot-8493",
        content_hash="snapshot-8493",
    )
    return _manifest(
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=(snapshot,),
            ),
        ),
        **overrides,
    )


def test_checkpoint_validation_keeps_legacy_checksum_unknown() -> None:
    service = ControlPlaneEvidenceService()
    manifest = _manifest(created_at=_NOW - timedelta(days=90))

    payload = service.checkpoint_validation(
        scope=_scope(manifest),
        checkpoint=(
            manifest.run_id,
            {
                "manifest_id": manifest.manifest_id,
                "pipeline_name": manifest.pipeline_name,
                "run_type": manifest.run_type.value,
                "execution_fingerprint": manifest.execution_fingerprint,
                "records_processed": 10,
            },
        ),
        evidence_source="immutable_manifest_history",
        aggregate_scope_unknown=False,
    )

    assert "checkpoint_parse_ok" in _reasons(payload)
    assert "checkpoint_schema_valid" in _reasons(payload)
    assert "checkpoint_checksum_not_recorded" in _reasons(payload)
    assert "checkpoint_anchors_match_manifest" in _reasons(payload)


def test_checkpoint_validation_reports_schema_and_anchor_mismatch_reasons() -> None:
    manifest = _manifest(created_at=_NOW - timedelta(days=90))

    payload = ControlPlaneEvidenceService().checkpoint_validation(
        scope=_scope(manifest),
        checkpoint=(
            manifest.run_id,
            {
                "manifest_id": "different-manifest",
                "pipeline_name": manifest.pipeline_name,
                "run_type": manifest.run_type.value,
                "execution_fingerprint": manifest.execution_fingerprint,
                "records_processed": "corrupt-count",
                "checkpoint_checksum_valid": False,
            },
        ),
        evidence_source="immutable_manifest_history",
        aggregate_scope_unknown=False,
    )

    assert payload["status"] == "ERROR"
    assert "checkpoint_records_processed_invalid" in _reasons(payload)
    assert "checkpoint_checksum_mismatch" in _reasons(payload)
    assert "checkpoint_anchor_mismatch" in _reasons(payload)


def test_checkpoint_validation_preserves_selected_run_not_found_reason() -> None:
    payload = ControlPlaneEvidenceService().checkpoint_validation(
        scope=_unresolved_scope(),
        checkpoint=None,
        evidence_source="selected_run_id_not_found",
        aggregate_scope_unknown=False,
    )

    assert payload["status"] == "UNKNOWN"
    assert payload["evidence_source"] == "selected_run_id_not_found"
    assert _reasons(payload) == {"selected_run_id_not_found"}


def test_manifest_validation_reports_version_and_contract_reasons() -> None:
    manifest = _manifest(
        schema_version="2.0",
        code_provenance=RunCodeProvenance(),
    )

    payload = ControlPlaneEvidenceService().manifest_validation(scope=_scope(manifest))

    assert payload["status"] == "ERROR"
    assert "manifest_schema_version_incompatible" in _reasons(payload)
    assert "manifest_contract_anchors_incomplete" in _reasons(payload)


def test_manifest_validation_does_not_overclaim_registry_compatibility() -> None:
    payload = ControlPlaneEvidenceService().manifest_validation(
        scope=_scope(_manifest())
    )

    assert payload["status"] == "UNKNOWN"
    assert "manifest_contract_compatibility_not_verified" in _reasons(payload)


def test_manifest_validation_rejects_unknown_persistence_profile() -> None:
    manifest = _manifest(launch_context={"required_persistence_profile": "replay_redy"})

    payload = ControlPlaneEvidenceService().manifest_validation(scope=_scope(manifest))

    assert payload["status"] == "ERROR"
    assert "manifest_persistence_profile_unsupported" in _reasons(payload)


class _LineageStore:
    def __init__(self, fragments: tuple[LineageGraphFragment, ...]) -> None:
        self.fragments = fragments

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        return list(self.fragments)

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        return list(self.fragments)


def test_lineage_validation_detects_directed_cycle() -> None:
    manifest = _manifest(created_at=_NOW - timedelta(days=90))
    node_a = LineageNodeRef(LineageNodeType.DATASET, "dataset:a")
    node_b = LineageNodeRef(LineageNodeType.TRANSFORM, "transform:b")
    run_node = LineageNodeRef(
        LineageNodeType.RUN,
        f"run:{manifest.run_id}",
        attributes={"run_id": str(manifest.run_id)},
    )
    manifest_node = LineageNodeRef(
        LineageNodeType.MANIFEST,
        f"manifest:{manifest.manifest_id}",
        attributes={"manifest_id": manifest.manifest_id},
    )
    fragment = LineageGraphFragment(
        fragment_id="fragment-8492",
        run_id=str(manifest.run_id),
        manifest_id=manifest.manifest_id,
        nodes=(node_a, node_b, run_node, manifest_node),
        edges=(
            LineageEdge(LineageEdgeType.DERIVED_FROM, node_a, node_b),
            LineageEdge(LineageEdgeType.PRODUCED_BY, node_b, node_a),
        ),
    )
    service = ControlPlaneEvidenceService(
        lineage_store=_LineageStore((fragment,))  # type: ignore[arg-type]
    )

    payload = service.lineage_validation(scope=_scope(manifest))

    assert payload["status"] == "ERROR"
    assert "lineage_cycle_detected" in _reasons(payload)
    assert "lineage_identity_consistent" in _reasons(payload)


def test_lineage_validation_detects_conflicting_node_definitions() -> None:
    manifest = _manifest(created_at=_NOW - timedelta(days=90))
    fragment_a = LineageGraphFragment(
        fragment_id="fragment-a",
        run_id=str(manifest.run_id),
        manifest_id=manifest.manifest_id,
        nodes=(
            LineageNodeRef(
                LineageNodeType.DATASET,
                "shared:node",
                attributes={"version": "1"},
            ),
        ),
    )
    fragment_b = LineageGraphFragment(
        fragment_id="fragment-b",
        run_id=str(manifest.run_id),
        manifest_id=manifest.manifest_id,
        nodes=(
            LineageNodeRef(
                LineageNodeType.TRANSFORM,
                "shared:node",
                attributes={"version": "2"},
            ),
        ),
    )
    service = ControlPlaneEvidenceService(
        lineage_store=_LineageStore((fragment_b, fragment_a))  # type: ignore[arg-type]
    )

    payload = service.lineage_validation(scope=_scope(manifest))

    assert payload["status"] == "ERROR"
    assert "lineage_identity_mismatch" in _reasons(payload)
    assert "node_definition_conflict:shared:node" in str(payload)


@pytest.mark.parametrize(
    ("profile", "expected_status", "profile_reason"),
    (
        ("degraded_observable", "WARNING", "lineage_persistence_profile_degraded"),
        ("replay_ready", "WARNING", "lineage_persistence_profile_degraded"),
        ("forensic_grade", "ERROR", "lineage_persistence_profile_unsatisfied"),
        ("replay_redy", "ERROR", "lineage_persistence_profile_unsupported"),
    ),
)
def test_lineage_missing_fragments_obeys_profile_contract(
    profile: str,
    expected_status: str,
    profile_reason: str,
) -> None:
    manifest = _manifest(launch_context={"required_persistence_profile": profile})
    service = ControlPlaneEvidenceService(
        lineage_store=_LineageStore(())  # type: ignore[arg-type]
    )

    payload = service.lineage_validation(scope=_scope(manifest))

    assert payload["status"] == expected_status
    assert profile_reason in _reasons(payload)
    assert "lineage_fragments_missing" in _reasons(payload)


class _LifecyclePlanner:
    def __init__(self, plan: ControlPlaneArtifactLifecyclePlan) -> None:
        self.plan_result = plan

    def plan(self, policy: object, *, dry_run: bool = True) -> object:
        return self.plan_result


def test_retention_compliance_uses_dry_run_evidence_floor() -> None:
    manifest = _snapshot_manifest(created_at=_NOW - timedelta(days=90))
    artifacts = tuple(
        ControlPlaneArtifactRef(
            surface=surface,
            path=f"/redacted/{surface.value}",
            artifact_id=(
                manifest.manifest_id
                if surface is ControlPlaneArtifactSurface.RUN_MANIFEST
                else (
                    "effective-config-8490"
                    if surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG
                    else (
                        "sha256:snapshot-8493"
                        if surface is ControlPlaneArtifactSurface.CACHED_BRONZE
                        else f"artifact-{surface.value}"
                    )
                )
            ),
            decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
            reason="reproducibility_evidence_floor",
            protected_by=(f"evidence_floor:manifest:{manifest.manifest_id}",),
            replay_impact=(
                ControlPlaneArtifactReplayImpact.STRICT_REPLAY_EVIDENCE_PROTECTED
            ),
        )
        for surface in (
            ControlPlaneArtifactSurface.RUN_MANIFEST,
            ControlPlaneArtifactSurface.RUN_LEDGER,
            ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
            ControlPlaneArtifactSurface.LINEAGE,
            ControlPlaneArtifactSurface.CACHED_BRONZE,
        )
    )
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=_NOW,
        cutoff=_NOW,
        dry_run=True,
        artifacts=artifacts,
    )
    service = ControlPlaneEvidenceService(
        lifecycle_planner=_LifecyclePlanner(plan)  # type: ignore[arg-type]
    )

    payload = service.retention_compliance(scope=_scope(manifest), now=_NOW)

    assert "reproducibility_evidence_floor_satisfied" in _reasons(payload)
    assert "required_evidence_surfaces_present" in _reasons(payload)
    assert "snapshot_lifecycle_evidence_present" in _reasons(payload)
    assert "archive_evidence_not_recorded" in _reasons(payload)
    assert all("path" not in row for row in payload["artifacts"])


def test_retention_compliance_reports_delete_and_evidence_floor_violations() -> None:
    manifest = _manifest(created_at=_NOW - timedelta(days=90))
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=_NOW,
        cutoff=_NOW + timedelta(seconds=1),
        dry_run=True,
        artifacts=(
            ControlPlaneArtifactRef(
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                path="/redacted/manifest.json",
                artifact_id=manifest.manifest_id,
                decision=ControlPlaneArtifactLifecycleDecision.DELETE,
                reason="retention_expired",
                replay_impact=(
                    ControlPlaneArtifactReplayImpact.STRICT_REPLAY_EVIDENCE_PROTECTED
                ),
            ),
        ),
    )
    service = ControlPlaneEvidenceService(
        lifecycle_planner=_LifecyclePlanner(plan)  # type: ignore[arg-type]
    )

    payload = service.retention_compliance(scope=_scope(manifest), now=_NOW)

    assert payload["status"] == "ERROR"
    assert "retention_delete_candidates_present" in _reasons(payload)
    assert "reproducibility_evidence_floor_unprotected" in _reasons(payload)
    assert "required_evidence_surfaces_missing" in _reasons(payload)


def test_retention_rejects_unknown_persistence_profile() -> None:
    manifest = _manifest(
        launch_context={"required_persistence_profile": "forensic_grdae"}
    )
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=_NOW,
        cutoff=_NOW - timedelta(days=90),
        dry_run=True,
        artifacts=(),
    )
    service = ControlPlaneEvidenceService(
        lifecycle_planner=_LifecyclePlanner(plan)  # type: ignore[arg-type]
    )

    payload = service.retention_compliance(scope=_scope(manifest), now=_NOW)

    assert payload["status"] == "ERROR"
    assert "retention_persistence_profile_unsupported" in _reasons(payload)


def test_failure_reasons_expose_only_fixed_categories() -> None:
    manifest = _manifest(created_at=_NOW - timedelta(days=90))
    ledger = InMemoryRunLedgerStore()
    for index, error_type in enumerate(
        ("ApiError", "SchemaViolationError", "ConnectionTimeout", "NovelCrash")
    ):
        ledger.append(
            RunLedgerEntry(
                entry_id=f"entry-{index}",
                manifest_id=manifest.manifest_id,
                run_id=manifest.run_id,
                event_type="run_failed",
                occurred_at=_NOW,
                status="failed",
                error_type=error_type,
                message=f"secret raw failure {index}",
            )
        )
    payload = ControlPlaneEvidenceService(ledger_port=ledger).failure_reasons(
        scope=_scope(manifest)
    )

    rows = payload["rows"]
    assert [row["category"] for row in rows] == list(FAILURE_REASON_CATEGORIES)
    assert {row["category"]: row["count"] for row in rows} == {
        "api": 1,
        "dq": 0,
        "schema": 1,
        "storage": 0,
        "network": 1,
        "validation": 0,
        "unknown": 1,
    }
    assert payload["total_failure_count"] == 4
    assert "secret raw failure" not in str(payload)
    assert "NovelCrash" not in str(payload)


@pytest.mark.parametrize(
    ("scope", "ledger", "expected_reason"),
    (
        (_unresolved_scope(), None, "selected_run_id_not_found"),
        (_scope(_manifest()), None, "run_ledger_unavailable"),
    ),
)
def test_failure_reasons_make_unknown_state_visible_without_zero_counts(
    scope: EvidenceScopeContext,
    ledger: object | None,
    expected_reason: str,
) -> None:
    payload = ControlPlaneEvidenceService(ledger_port=ledger).failure_reasons(
        scope=scope
    )  # type: ignore[arg-type]

    rows = payload["rows"]
    assert [row["category"] for row in rows] == list(FAILURE_REASON_CATEGORIES)
    assert {row["status"] for row in rows} == {"UNKNOWN"}
    assert {row["reason"] for row in rows} == {expected_reason}
    assert all(row["count"] is None for row in rows)
    assert payload["total_failure_count"] is None
