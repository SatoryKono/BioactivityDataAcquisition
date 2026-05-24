"""Anchor value aggregation for Control Plane identity evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunInputSnapshotRef, RunLedgerEntry, RunManifest
from bioetl.interfaces.http.control_plane_identity.checkpoint_extractors import (
    checkpoint_value,
    composite_run_identity,
    first_payload_value,
)
from bioetl.interfaces.http.control_plane_identity.formatting import (
    join_non_empty,
    stable_hash,
)
from bioetl.interfaces.http.control_plane_identity.ledger_extractors import (
    artifact_refs,
    bronze_batch_ids,
    component_run_ids,
    dq_report_paths,
    lineage_fragment_ids,
    published_artifacts,
)
from bioetl.interfaces.http.control_plane_identity.manifest_extractors import (
    artifact_ref_values,
    correlation_anchor_gaps,
    diagnostic_value,
    identity_graph_diagnostics,
    input_snapshot_fingerprint,
    input_snapshots,
    source_ref_values,
)
from bioetl.interfaces.http.control_plane_identity.replay_extractors import (
    exact_replay_blockers,
    exact_replay_eligible,
    replay_mode,
    runtime_mode,
)


def _anchor_snapshot_fingerprint(
    diagnostics: dict[str, object],
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> object | None:
    """Return canonical input-snapshot identity fingerprint from diagnostics or data."""
    return diagnostic_value(
        diagnostics,
        "input_snapshot_identity_fingerprint",
        "input_snapshot_fingerprint",
    ) or input_snapshot_fingerprint(snapshots)


def _manifest_anchor_values(
    *,
    manifest: RunManifest,
    diagnostics: dict[str, object],
    snapshots: tuple[RunInputSnapshotRef, ...],
    checkpoint_status: str,
    snapshot_fingerprint: object | None,
) -> dict[str, object | None]:
    """Return manifest-backed anchor values without ledger-derived enrichments."""
    code = manifest.code_provenance
    exact_replay_supported = diagnostic_value(diagnostics, "exact_replay_eligible")
    return {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "pipeline_name": manifest.pipeline_name,
        "provider_entity": join_non_empty((manifest.provider, manifest.entity), "."),
        "runtime_mode": runtime_mode(manifest),
        "execution_fingerprint": diagnostic_value(diagnostics, "execution_fingerprint")
        or manifest.execution_fingerprint,
        "git_commit": code.git_commit,
        "pipeline_version": code.pipeline_version,
        "effective_config_hash": diagnostic_value(diagnostics, "effective_config_hash")
        or code.effective_config_hash,
        "resolved_config_hash": code.resolved_config_hash,
        "effective_config_artifact_id": diagnostic_value(
            diagnostics, "effective_config_artifact_id"
        )
        or code.effective_config_artifact_id,
        "contract_ref": code.contract_ref,
        "contract_version": code.contract_version,
        "contract_schema_hash": code.contract_schema_hash,
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "input_snapshot_count": len(snapshots) if snapshots else None,
        "replay_mode": replay_mode(manifest),
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
        "checkpoint_anchor_status": checkpoint_status,
        "composite_run_identity": composite_run_identity(manifest),
        "config_hash": code.config_hash,
        "dq_policy_ref": code.dq_policy_ref,
        "rule_bundle_version": code.rule_bundle_version,
        "dq_contract_compatibility_hash": code.dq_contract_compatibility_hash,
        "source_refs": source_ref_values(manifest.source_refs),
        "input_snapshot_ids": [item.snapshot_id for item in snapshots],
        "input_snapshot_content_hashes": [item.content_hash for item in snapshots],
        "replay_capability": diagnostic_value(diagnostics, "replay_capability")
        or manifest.replay_capability.value,
        "exact_replay_eligible": exact_replay_supported
        if exact_replay_supported is not None
        else exact_replay_eligible(manifest, snapshots),
        "resume_contract": first_payload_value(
            manifest,
            "resume_contract",
            "checkpoint_resume_contract",
        ),
        "launch_context_hash": stable_hash(manifest.launch_context),
        "runtime_config_hash": stable_hash(manifest.runtime_config),
        "planned_artifacts": artifact_ref_values(manifest.planned_artifacts),
        "checkpoint_file_id": checkpoint_value(
            manifest, "checkpoint_file_id", "checkpoint_path"
        ),
        "lock_owner_id": first_payload_value(
            manifest, "lock_owner_id", "fencing_token"
        ),
        "cross_validation_rule_ids": first_payload_value(
            manifest,
            "cross_validation_rule_ids",
            "cross_validation_rules",
        ),
        "identity_graph_complete": diagnostic_value(
            diagnostics,
            "identity_graph_complete",
            "complete",
        ),
        "correlation_anchor_gaps": correlation_anchor_gaps(diagnostics),
        "exact_replay_blockers": exact_replay_blockers(
            manifest,
            snapshots,
            diagnostics,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
    }


def _ledger_anchor_values(
    *,
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object | None]:
    """Return anchor values derived from ledger or published artifact surfaces."""
    return {
        "lineage_fragment_ids": lineage_fragment_ids(ledger_entries),
        "artifact_refs": artifact_refs(manifest, ledger_entries),
        "latest_event_id": ledger_entries[-1].entry_id if ledger_entries else None,
        "published_artifacts": published_artifacts(ledger_entries),
        "component_run_ids": component_run_ids(ledger_entries),
        "dq_report_paths": dq_report_paths(manifest, ledger_entries),
        "bronze_batch_ids": bronze_batch_ids(manifest, ledger_entries),
    }


def build_anchor_values(
    manifest: RunManifest | None,
    *,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
) -> dict[str, object | None]:
    """Extract raw anchor values from manifest, ledger, and derived diagnostics."""
    if manifest is None:
        return {}
    snapshots = input_snapshots(manifest)
    diagnostics = identity_graph_diagnostics(manifest)
    snapshot_fingerprint = _anchor_snapshot_fingerprint(diagnostics, snapshots)
    return {
        **_manifest_anchor_values(
            manifest=manifest,
            diagnostics=diagnostics,
            snapshots=snapshots,
            checkpoint_status=checkpoint_status,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
        **_ledger_anchor_values(
            manifest=manifest,
            ledger_entries=ledger_entries,
        ),
    }


__all__ = ["build_anchor_values"]
