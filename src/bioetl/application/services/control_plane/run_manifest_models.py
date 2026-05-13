"""Shared models for run-manifest service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunSourceRef,
)
from bioetl.domain.types import RunID, RunType


@dataclass(frozen=True, slots=True)
class RunManifestCreateSpec:
    """Normalized inputs required to build an immutable run manifest."""

    run_id: RunID
    run_type: RunType | str
    pipeline_name: str
    provider: str
    entity: str
    launch_context: dict[str, object]
    runtime_config: dict[str, object]
    resolved_config: dict[str, object]
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    source_refs: tuple[RunSourceRef, ...] = ()
    planned_artifacts: tuple[RunArtifactRef, ...] = ()
    pipeline_version: str | None = None
    git_commit: str | None = None
    source_revision_state: str | None = None
    dependency_lock_hash: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY


__all__ = ["RunManifestCreateSpec"]
