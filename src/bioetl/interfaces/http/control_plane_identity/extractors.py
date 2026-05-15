"""Source extraction helpers for Control Plane identity evidence."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.interfaces.http.control_plane_identity.formatting import (
    append_value,
    dedupe,
    is_present,
    join_non_empty,
    mapping_value,
    stable_hash,
)
from bioetl.interfaces.http.control_plane_identity.specs import TERMINAL_STATUSES

_COMPOSITE_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)


def build_anchor_values(
    manifest: RunManifest | None,
    *,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
) -> dict[str, object | None]:
    """Extract raw anchor values from manifest, ledger, and derived diagnostics."""
    if manifest is None:
        return {}
    code = manifest.code_provenance
    snapshots = input_snapshots(manifest)
    diagnostics = identity_graph_diagnostics(manifest)
    snapshot_fingerprint = (
        diagnostic_value(
            diagnostics,
            "input_snapshot_identity_fingerprint",
            "input_snapshot_fingerprint",
        )
        or input_snapshot_fingerprint(snapshots)
    )
    return {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "pipeline_name": manifest.pipeline_name,
        "provider_entity": join_non_empty((manifest.provider, manifest.entity), "."),
        "runtime_mode": runtime_mode(manifest),
        "execution_fingerprint": diagnostic_value(
            diagnostics,
            "execution_fingerprint",
        )
        or manifest.execution_fingerprint,
        "git_commit": code.git_commit,
        "pipeline_version": code.pipeline_version,
        "effective_config_hash": diagnostic_value(
            diagnostics,
            "effective_config_hash",
        )
        or code.effective_config_hash,
        "effective_config_artifact_id": diagnostic_value(
            diagnostics,
            "effective_config_artifact_id",
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
        "exact_replay_eligible": diagnostic_value(
            diagnostics,
            "exact_replay_eligible",
        )
        if diagnostic_value(diagnostics, "exact_replay_eligible") is not None
        else exact_replay_eligible(manifest, snapshots),
        "resume_contract": first_payload_value(
            manifest,
            "resume_contract",
            "checkpoint_resume_contract",
        ),
        "lineage_fragment_ids": lineage_fragment_ids(ledger_entries),
        "artifact_refs": artifact_refs(manifest, ledger_entries),
        "latest_event_id": ledger_entries[-1].entry_id if ledger_entries else None,
        "launch_context_hash": stable_hash(manifest.launch_context),
        "runtime_config_hash": stable_hash(manifest.runtime_config),
        "planned_artifacts": artifact_ref_values(manifest.planned_artifacts),
        "published_artifacts": published_artifacts(ledger_entries),
        "component_run_ids": component_run_ids(ledger_entries),
        "checkpoint_file_id": checkpoint_value(
            manifest, "checkpoint_file_id", "checkpoint_path"
        ),
        "lock_owner_id": first_payload_value(
            manifest, "lock_owner_id", "fencing_token"
        ),
        "dq_report_paths": dq_report_paths(manifest, ledger_entries),
        "cross_validation_rule_ids": first_payload_value(
            manifest,
            "cross_validation_rule_ids",
            "cross_validation_rules",
        ),
        "bronze_batch_ids": bronze_batch_ids(manifest, ledger_entries),
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


def identity_graph_diagnostics(manifest: RunManifest) -> dict[str, object]:
    """Return identity graph diagnostics embedded in known manifest payloads."""
    diagnostics: dict[str, object] = {}
    for payload in (
        manifest.runtime_config,
        manifest.resolved_config,
        manifest.launch_context,
    ):
        for key in (
            "identity_graph",
            "identity_graph_diagnostics",
            "diagnostics",
            "reproducibility_diagnostics",
        ):
            value = payload.get(key)
            if isinstance(value, dict):
                diagnostics.update({str(item_key): item for item_key, item in value.items()})
    return diagnostics


def diagnostic_value(
    diagnostics: dict[str, object],
    *keys: str,
) -> object | None:
    for key in keys:
        value = diagnostics.get(key)
        if is_present(value):
            return value
    return None


def correlation_anchor_gaps(diagnostics: dict[str, object]) -> dict[str, object]:
    value = diagnostics.get("correlation_anchor_gaps")
    return dict(value) if isinstance(value, dict) else {}


def exact_replay_blockers(
    manifest: RunManifest,
    snapshots: tuple[RunInputSnapshotRef, ...],
    diagnostics: dict[str, object],
    *,
    snapshot_fingerprint: object | None,
) -> list[str]:
    reported = diagnostics.get("exact_replay_blockers")
    if isinstance(reported, list | tuple | set):
        return [str(item) for item in reported if is_present(item)]
    if not requested_exact_replay(manifest):
        return []
    blockers: list[str] = []
    code = manifest.code_provenance
    required = {
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": code.effective_config_hash,
        "effective_config_artifact_id": code.effective_config_artifact_id,
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "input_snapshot_ids": [item.snapshot_id for item in snapshots],
        "replay_of_run_id": manifest.replay_of_run_id,
    }
    for name, value in required.items():
        if not is_present(value):
            blockers.append(name)
    return blockers


def input_snapshots(manifest: RunManifest) -> tuple[RunInputSnapshotRef, ...]:
    snapshots: list[RunInputSnapshotRef] = []
    for source_ref in manifest.source_refs:
        snapshots.extend(source_ref.input_snapshots)
    return tuple(snapshots)


def input_snapshot_fingerprint(
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> str | None:
    if not snapshots:
        return None
    payload: list[object] = [
        {
            "snapshot_id": item.snapshot_id,
            "content_hash": item.content_hash,
            "immutable_uri": item.immutable_uri,
            "query_fingerprint": item.query_fingerprint,
        }
        for item in snapshots
    ]
    return compute_input_snapshot_identity_fingerprint(payload)


def source_ref_values(source_refs: Sequence[RunSourceRef]) -> list[str]:
    values: list[str] = []
    for item in source_refs:
        value = join_non_empty((item.provider, item.entity, item.pipeline_name), "/")
        if value:
            values.append(value)
    return values


def artifact_ref_values(artifacts: Sequence[RunArtifactRef]) -> list[str]:
    return [
        ref
        for item in artifacts
        if (ref := join_non_empty((item.layer, item.path), ":"))
    ]


def artifact_refs(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = published_artifacts(ledger_entries)
    if values:
        return values
    return artifact_ref_values(manifest.planned_artifacts)


def published_artifacts(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("artifact_ref", "artifact_path", "path", "uri"):
            append_value(values, details.get(key))
    return dedupe(values)


def lineage_fragment_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    return dedupe(
        [
            entry.lineage_fragment_id
            for entry in ledger_entries
            if entry.lineage_fragment_id
        ]
    )


def component_run_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        if entry.event_type not in _COMPOSITE_EVENTS:
            continue
        details = entry.details or {}
        for key in ("component_run_id", "child_run_id", "upstream_run_id", "run_id"):
            append_value(values, details.get(key))
        append_value(values, details.get("component_run_ids"))
    return dedupe(values)


def dq_report_paths(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values: list[str] = []
    append_value(
        values, first_payload_value(manifest, "dq_report_paths", "dq_report_path")
    )
    for entry in ledger_entries:
        details = entry.details or {}
        append_value(values, details.get("dq_report_paths"))
        append_value(values, details.get("dq_report_path"))
    return dedupe(values)


def bronze_batch_ids(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = [item.snapshot_id for item in input_snapshots(manifest)]
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("bronze_batch_id", "bronze_batch_ids", "source_batch_ids"):
            append_value(values, details.get(key))
    return dedupe(values)


def checkpoint_anchor_payload(manifest: RunManifest) -> dict[str, object]:
    for payload in (
        manifest.runtime_config,
        manifest.resolved_config,
        manifest.launch_context,
    ):
        checkpoint = mapping_value(
            payload,
            "checkpoint_metadata",
            "persisted_checkpoint_metadata",
            "checkpoint_anchors",
            "persisted_checkpoint_anchors",
        )
        if checkpoint:
            return normalize_checkpoint_metadata_payload(checkpoint)
    reproducibility = mapping_value(
        manifest.resolved_config,
        "reproducibility_diagnostics",
        "reproducibility",
    )
    if reproducibility:
        checkpoint = mapping_value(reproducibility, "checkpoint_anchors")
        if checkpoint:
            persisted = mapping_value(
                checkpoint,
                "checkpoint",
                "checkpoint_metadata",
                "persisted_checkpoint_anchors",
            )
            return normalize_checkpoint_metadata_payload(persisted or checkpoint)
    return {}


def normalize_checkpoint_metadata_payload(
    checkpoint: object,
) -> dict[str, object]:
    """Normalize persisted CheckpointMetadata-like mappings into anchor payloads."""
    if not isinstance(checkpoint, dict):
        return {}
    normalized = CheckpointMetadata.from_dict(
        {str(key): value for key, value in checkpoint.items()}
    ).to_dict()
    # Preserve custom metadata keys that are not modeled on CheckpointMetadata yet.
    for key, value in checkpoint.items():
        normalized.setdefault(str(key), value)
    return normalized


def checkpoint_value(manifest: RunManifest, *keys: str) -> object | None:
    checkpoint = checkpoint_anchor_payload(manifest)
    for key in keys:
        value = checkpoint.get(key)
        if is_present(value):
            return value
    return first_payload_value(manifest, *keys)


def composite_run_identity(manifest: RunManifest) -> object | None:
    return checkpoint_value(manifest, "composite_run_identity")


def first_payload_value(manifest: RunManifest, *keys: str) -> object | None:
    for payload in (
        manifest.runtime_config,
        manifest.launch_context,
        manifest.resolved_config,
    ):
        for key in keys:
            value = payload.get(key)
            if is_present(value):
                return value
    return None


def runtime_mode(manifest: RunManifest) -> str:
    flags = []
    for name in (
        "execution_context",
        "resume",
        "dry_run",
        "exact_replay",
        "use_cached_bronze",
    ):
        value = first_payload_value(manifest, name)
        if value not in (None, False, "", [], {}):
            flags.append(f"{name}={value}")
    return " | ".join([manifest.run_type.value, *flags])


def replay_mode(manifest: RunManifest) -> str:
    if requested_exact_replay(manifest):
        return "exact_replay"
    if manifest.replay_of_run_id or manifest.replay_of_manifest_id:
        return "replay"
    return manifest.run_type.value


def exact_replay_eligible(
    manifest: RunManifest,
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> bool:
    code = manifest.code_provenance
    required = (
        manifest.execution_fingerprint,
        code.effective_config_hash,
        code.effective_config_artifact_id,
        input_snapshot_fingerprint(snapshots),
    )
    return all(is_present(item) for item in required)


def requested_exact_replay(manifest: RunManifest) -> bool:
    value = first_payload_value(manifest, "exact_replay", "requested_exact_replay")
    return value is True or str(value).strip().lower() == "true"


def is_replay(manifest: RunManifest) -> bool:
    return (
        bool(manifest.replay_of_run_id)
        or bool(manifest.replay_of_manifest_id)
        or requested_exact_replay(manifest)
    )


def is_composite(manifest: RunManifest) -> bool:
    return (
        manifest.pipeline_name.startswith("composite_")
        or manifest.provider == "composite"
        or bool(composite_run_identity(manifest))
    )


def is_terminal(ledger_entries: tuple[RunLedgerEntry, ...]) -> bool:
    return any(
        str(entry.status or "").lower() in TERMINAL_STATUSES for entry in ledger_entries
    )
