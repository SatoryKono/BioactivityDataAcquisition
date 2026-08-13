"""Control-plane coverage KPI helpers for the normalization field matrix."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from scripts.docs.matrix.normalization_matrix_catalog import (
    CANONICAL_COMPOSITE_RUN_ID,
    CANONICAL_CONTRACT_REF,
    CANONICAL_CONTRACT_REF_RAW,
    CANONICAL_CONTRACT_VERSION,
    CANONICAL_EFFECTIVE_CONFIG_HASH,
    CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
    CANONICAL_MANIFEST_ID,
    CANONICAL_NORMALIZATION_PROFILE_HASH_RAW,
    CANONICAL_NORMALIZATION_PROFILE_REF_RAW,
    CANONICAL_NORMALIZATION_PROFILE_VERSION_RAW,
    CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI,
    CONTROL_PLANE_REPRODUCIBILITY_SURFACE,
    CompositeCheckpointState,
    CompositePipelineState,
    ExpectedCheckpointContext,
    build_execution_identity_payload,
    create_expected_checkpoint_context,
    merge_expected_anchors,
    normalize_run_ledger_payload,
    normalize_run_manifest_spec,
    normalize_runtime_anchor_payload,
)

def _control_plane_surface_statuses() -> list[dict[str, object]]:
    occurred_at = datetime(2026, 4, 8, 12, 53, 47, tzinfo=UTC)
    manifest_status = normalize_run_manifest_spec(
        {
            "code_provenance": {"config_hash": "DEADBEEF"},
            "source_refs": [
                {
                    "pipeline_name": "chembl_activity",
                    "input_snapshots": [
                        {"snapshot_id": "b"},
                        {"snapshot_id": "a"},
                    ],
                }
            ],
            "planned_artifacts": [
                {"path": "b", "layer": "gold"},
                {"path": "a", "layer": "bronze"},
            ],
        }
    )
    ledger_status = normalize_run_ledger_payload(
        {
            "run_id": UUID("11111111-1111-1111-1111-111111111111"),
            "occurred_at": occurred_at,
            "metrics_snapshot": {"records_b": 2, "records_a": 1},
        }
    )
    execution_identity_status = build_execution_identity_payload(
        pipeline_name=" chembl_activity ",
        run_type=" INCREMENTAL ",
        pipeline_version=" 1.2.3 ",
        git_commit=" ABCDEF123 ",
        effective_config_hash=CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
        dq_contract_compatibility_hash=" DEADBEEF ",
        contract=(CANONICAL_CONTRACT_REF_RAW, " v2 "),
        normalization_profile=(
            CANONICAL_NORMALIZATION_PROFILE_REF_RAW,
            CANONICAL_NORMALIZATION_PROFILE_VERSION_RAW,
            CANONICAL_NORMALIZATION_PROFILE_HASH_RAW,
        ),
        effective_config_artifact_id=" artifact-42 ",
        exact_replay=True,
        input_snapshot_fingerprint=" FACE ",
    )
    runtime_anchor_status = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
            "contract_ref": CANONICAL_CONTRACT_REF_RAW,
            "contract_version": " v2 ",
            "manifest_id": f" {CANONICAL_MANIFEST_ID} ",
            "composite_run_identity": f" {CANONICAL_COMPOSITE_RUN_ID} ",
        }
    )
    checkpoint_context = create_expected_checkpoint_context(
        effective_config_hash=CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
        contract_ref=CANONICAL_CONTRACT_REF_RAW,
        contract_version=" v2 ",
        manifest_id=f" {CANONICAL_MANIFEST_ID} ",
        composite_run_identity=f" {CANONICAL_COMPOSITE_RUN_ID} ",
    )
    merged_checkpoint = merge_expected_anchors(
        CompositeCheckpointState(
            composite_name="composite_publication",
            run_id="run-1",
            state=CompositePipelineState.SEED_RUNNING,
        ),
        checkpoint_context,
    )

    return [
        _control_plane_status(
            "run_manifest_spec",
            _manifest_status_covered(manifest_status),
        ),
        _control_plane_status(
            "run_ledger_payload",
            _ledger_status_covered(ledger_status),
        ),
        _control_plane_status(
            "execution_identity_payload",
            _execution_identity_status_covered(execution_identity_status),
        ),
        _control_plane_status(
            "runtime_anchor_payload",
            _runtime_anchor_status_covered(runtime_anchor_status),
        ),
        _control_plane_status(
            "checkpoint_expected_context",
            _checkpoint_context_covered(checkpoint_context),
        ),
        _control_plane_status(
            "checkpoint_anchor_merge",
            _checkpoint_anchor_merge_covered(merged_checkpoint),
        ),
    ]


def _control_plane_status(seam: str, covered: bool) -> dict[str, object]:
    """Build one control-plane normalization seam status row."""
    return {"seam": seam, "covered": covered}


def _manifest_status_covered(manifest_status: dict[str, object]) -> bool:
    """Return whether manifest normalization preserves canonical ordering/seams."""
    planned_artifacts = manifest_status.get("planned_artifacts", [])
    source_refs = manifest_status.get("source_refs", [])
    if not isinstance(planned_artifacts, list) or not isinstance(source_refs, list):
        return False
    return (
        manifest_status.get("code_provenance") == {"config_hash": "deadbeef"}
        and bool(planned_artifacts)
        and planned_artifacts[0].get("layer") == "bronze"
        and bool(source_refs)
        and _first_snapshot_id(source_refs) == "a"
    )


def _first_snapshot_id(source_refs: list[object]) -> str | None:
    """Return the first normalized snapshot id when present."""
    if not source_refs:
        return None
    first_source = source_refs[0]
    if not isinstance(first_source, dict):
        return None
    input_snapshots = first_source.get("input_snapshots")
    if not isinstance(input_snapshots, list) or not input_snapshots:
        return None
    first_snapshot = input_snapshots[0]
    if not isinstance(first_snapshot, dict):
        return None
    snapshot_id = first_snapshot.get("snapshot_id")
    return snapshot_id if isinstance(snapshot_id, str) else None


def _ledger_status_covered(ledger_status: dict[str, object]) -> bool:
    """Return whether ledger normalization preserves canonical ordering/format."""
    return (
        ledger_status.get("run_id") == "11111111-1111-1111-1111-111111111111"
        and ledger_status.get("occurred_at") == "2026-04-08T12:53:47Z"
        and ledger_status.get("metrics_snapshot") == {"records_a": 1, "records_b": 2}
    )


def _execution_identity_status_covered(
    execution_identity_status: Mapping[str, object],
) -> bool:
    """Return whether execution identity normalization produces canonical values."""
    return (
        execution_identity_status.get("contract_ref") == CANONICAL_CONTRACT_REF
        and execution_identity_status.get("contract_version")
        == CANONICAL_CONTRACT_VERSION
        and execution_identity_status.get("exact_replay") == "true"
    )


def _runtime_anchor_status_covered(runtime_anchor_status: Mapping[str, object]) -> bool:
    """Return whether runtime anchor normalization produces canonical values."""
    return (
        runtime_anchor_status.get("effective_config_hash")
        == CANONICAL_EFFECTIVE_CONFIG_HASH
        and runtime_anchor_status.get("contract_ref") == CANONICAL_CONTRACT_REF
        and runtime_anchor_status.get("contract_version") == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_context_covered(
    checkpoint_context: ExpectedCheckpointContext,
) -> bool:
    """Return whether checkpoint context normalization preserves canonical anchors."""
    return (
        checkpoint_context.effective_config_hash == CANONICAL_EFFECTIVE_CONFIG_HASH
        and checkpoint_context.contract_ref == CANONICAL_CONTRACT_REF
        and checkpoint_context.contract_version == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_anchor_merge_covered(
    merged_checkpoint: CompositeCheckpointState,
) -> bool:
    """Return whether merged checkpoint anchors preserve canonical values."""
    return (
        merged_checkpoint.effective_config_hash == CANONICAL_EFFECTIVE_CONFIG_HASH
        and merged_checkpoint.contract_ref == CANONICAL_CONTRACT_REF
        and merged_checkpoint.contract_version == CANONICAL_CONTRACT_VERSION
        and merged_checkpoint.manifest_id == CANONICAL_MANIFEST_ID
        and merged_checkpoint.composite_run_identity == CANONICAL_COMPOSITE_RUN_ID
    )


def build_control_plane_normalization_coverage_kpi() -> dict[str, object]:
    statuses = _control_plane_surface_statuses()
    covered = sum(1 for status in statuses if bool(status["covered"]))
    total = len(statuses)
    value_pct = round((covered * 100 / total) if total else 0.0, 2)
    return {
        "surface": CONTROL_PLANE_REPRODUCIBILITY_SURFACE,
        "name": CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI,
        "description": (
            "Percent of governed control-plane and reproducibility normalization seams "
            "covered by canonical normalization contracts."
        ),
        "numerator": covered,
        "denominator": total,
        "value_pct": value_pct,
    }

