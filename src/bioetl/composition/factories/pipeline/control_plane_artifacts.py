"""Shared control-plane artifact bundle for pipeline creation helpers."""

from __future__ import annotations

from bioetl.domain.ports.runtime.runner import (
    PipelineControlPlaneArtifacts as ControlPlaneArtifacts,
)


def build_control_plane_artifacts(
    *,
    manifest_id: str | None = None,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> ControlPlaneArtifacts:
    """Build a typed control-plane artifact bundle."""
    return ControlPlaneArtifacts(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        config_hash=config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
    )
