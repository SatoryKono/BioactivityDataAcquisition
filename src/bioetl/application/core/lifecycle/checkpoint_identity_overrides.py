"""Checkpoint execution identity enrichment helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import TypedDict

from bioetl.domain.types import JsonDict
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


class _CoreIdentityOverrides(TypedDict):
    dq_contract_compatibility_hash: str | None
    dq_policy_hash: str | None
    dq_rule_bundle_version: str | None
    pipeline_name: str | None
    run_type: str | None
    pipeline_version: str | None
    git_commit: str | None
    dependency_lock_hash: str | None
    effective_config_hash: str | None
    effective_config_artifact_id: str | None

class _ReplayIdentityOverrides(TypedDict):
    execution_fingerprint: str | None
    composite_run_identity: str | None
    manifest_id: str | None
    contract_ref: str | None
    contract_version: str | None
    normalization_profile_ref: str | None
    normalization_profile_version: str | None
    normalization_profile_hash: str | None
    exact_replay: bool | None
    input_snapshot_refs: tuple[JsonDict, ...]
    input_snapshot_ids: tuple[str, ...]
    input_snapshot_fingerprint: str | None
    silver_filter_compatibility_mode: str | None
    memory_decision_trace: tuple[JsonDict, ...]
    run_context: JsonDict | None

def _prefer_identity_value(
    current_value: str | None,
    identity_value: str | None,
) -> str | None:
    """Prefer persisted execution identity, then fall back to current identity."""
    return current_value if current_value is not None else identity_value

def _prefer_identity_flag(
    current_value: bool | None,
    identity_value: bool | None,
) -> bool | None:
    """Prefer persisted boolean identity flag, then fall back to current identity."""
    return current_value if current_value is not None else identity_value

def _prefer_identity_sequence[T](
    current_value: tuple[T, ...],
    identity_value: tuple[T, ...],
) -> tuple[T, ...]:
    """Prefer persisted non-empty tuple values, otherwise use identity fallback."""
    return current_value if current_value else identity_value

def _build_core_identity_overrides(
    metadata: CheckpointMetadata,
    identity: CheckpointMetadata,
) -> _CoreIdentityOverrides:
    """Build core execution-identity overrides for checkpoint enrichment."""
    return {
        "dq_contract_compatibility_hash": _prefer_identity_value(
            metadata.dq_contract_compatibility_hash,
            identity.dq_contract_compatibility_hash,
        ),
        "dq_policy_hash": _prefer_identity_value(
            metadata.dq_policy_hash,
            identity.dq_policy_hash,
        ),
        "dq_rule_bundle_version": _prefer_identity_value(
            metadata.dq_rule_bundle_version,
            identity.dq_rule_bundle_version,
        ),
        "pipeline_name": _prefer_identity_value(
            metadata.pipeline_name,
            identity.pipeline_name,
        ),
        "run_type": _prefer_identity_value(metadata.run_type, identity.run_type),
        "pipeline_version": _prefer_identity_value(
            metadata.pipeline_version,
            identity.pipeline_version,
        ),
        "git_commit": _prefer_identity_value(metadata.git_commit, identity.git_commit),
        "dependency_lock_hash": _prefer_identity_value(
            metadata.dependency_lock_hash,
            identity.dependency_lock_hash,
        ),
        "effective_config_hash": _prefer_identity_value(
            metadata.effective_config_hash,
            identity.effective_config_hash,
        ),
        "effective_config_artifact_id": _prefer_identity_value(
            metadata.effective_config_artifact_id,
            identity.effective_config_artifact_id,
        ),
    }

def _build_replay_identity_overrides(
    metadata: CheckpointMetadata,
    identity: CheckpointMetadata,
) -> _ReplayIdentityOverrides:
    """Build replay and traceability identity overrides for checkpoint enrichment."""
    return {
        "execution_fingerprint": _prefer_identity_value(
            metadata.execution_fingerprint,
            identity.execution_fingerprint,
        ),
        "composite_run_identity": _prefer_identity_value(
            metadata.composite_run_identity,
            identity.composite_run_identity,
        ),
        "manifest_id": _prefer_identity_value(
            metadata.manifest_id,
            identity.manifest_id,
        ),
        "contract_ref": _prefer_identity_value(
            metadata.contract_ref,
            identity.contract_ref,
        ),
        "contract_version": _prefer_identity_value(
            metadata.contract_version,
            identity.contract_version,
        ),
        "normalization_profile_ref": _prefer_identity_value(
            metadata.normalization_profile_ref,
            identity.normalization_profile_ref,
        ),
        "normalization_profile_version": _prefer_identity_value(
            metadata.normalization_profile_version,
            identity.normalization_profile_version,
        ),
        "normalization_profile_hash": _prefer_identity_value(
            metadata.normalization_profile_hash,
            identity.normalization_profile_hash,
        ),
        "exact_replay": _prefer_identity_flag(
            metadata.exact_replay,
            identity.exact_replay,
        ),
        "input_snapshot_refs": _prefer_identity_sequence(
            metadata.input_snapshot_refs,
            identity.input_snapshot_refs,
        ),
        "input_snapshot_ids": _prefer_identity_sequence(
            metadata.input_snapshot_ids,
            identity.input_snapshot_ids,
        ),
        "input_snapshot_fingerprint": _prefer_identity_value(
            metadata.input_snapshot_fingerprint,
            identity.input_snapshot_fingerprint,
        ),
        "silver_filter_compatibility_mode": _prefer_identity_value(
            metadata.silver_filter_compatibility_mode,
            identity.silver_filter_compatibility_mode,
        ),
        "memory_decision_trace": (
            metadata.memory_decision_trace or identity.memory_decision_trace
        ),
        "run_context": metadata.run_context or identity.run_context,
    }

def enrich_metadata_with_execution_identity(
    metadata: CheckpointMetadata,
    *,
    identity: CheckpointMetadata | None,
) -> CheckpointMetadata:
    """Fill checkpoint metadata gaps from current execution identity."""
    if identity is None:
        return metadata
    return replace(
        metadata,
        **_build_core_identity_overrides(metadata, identity),
        **_build_replay_identity_overrides(metadata, identity),
    )

def checkpoint_identity_payload(
    metadata: CheckpointMetadata | None,
) -> dict[str, object | None]:
    """Return the compact identity anchors most useful for resume forensics."""
    if metadata is None:
        return {
            "composite_run_identity": None,
            "execution_fingerprint": None,
            "manifest_id": None,
            "effective_config_hash": None,
            "contract_ref": None,
            "contract_version": None,
            "exact_replay": None,
            "input_snapshot_ids": [],
        }
    return {
        "composite_run_identity": metadata.composite_run_identity,
        "execution_fingerprint": metadata.execution_fingerprint,
        "manifest_id": metadata.manifest_id,
        "effective_config_hash": metadata.effective_config_hash,
        "contract_ref": metadata.contract_ref,
        "contract_version": metadata.contract_version,
        "exact_replay": metadata.exact_replay,
        "required_persistence_profile": metadata.required_persistence_profile,
        "input_snapshot_ids": list(metadata.input_snapshot_ids),
    }

__all__ = [
    "checkpoint_identity_payload",
    "enrich_metadata_with_execution_identity",
]
