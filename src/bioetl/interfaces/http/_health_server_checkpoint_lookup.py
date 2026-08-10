"""Checkpoint freshness lookup helpers for health-server routing."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bioetl.domain.ports import CheckpointPort
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

_CheckpointTuple = tuple[object, dict[str, object]]

_CheckpointEvidence = tuple[_CheckpointTuple | None, str, str | None, bool]


class _CheckpointLookupHost(Protocol):
    @property
    def _checkpoint_port(self) -> CheckpointPort | None: ...

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool: ...


@runtime_checkable
class _LatestCheckpointLookupPort(Protocol):
    async def load_latest_for_pipeline(
        self,
        pipeline: str,
    ) -> _CheckpointTuple | None: ...


async def load_checkpoint_freshness_evidence(
    host: _CheckpointLookupHost,
    *,
    scope: _IdentityScope,
    target_pipeline: str,
) -> _CheckpointEvidence:
    checkpoint_port = host._checkpoint_port
    if checkpoint_port is None:
        return None, "checkpoint_port_unavailable", None, False
    if scope.selected_run_id is not None and scope.resolved_manifest is None:
        return None, "selected_run_id_not_found", None, False

    evidence_source = "mutable_latest_pointer"

    if scope.selected_run_id is not None and scope.resolved_manifest is not None:
        return await _load_for_resolved_manifest(checkpoint_port, scope.resolved_manifest)
    elif scope.selected_pipelines or not host._is_all_scope_token(scope.requested_pipeline):
        return await _load_for_pipeline_target(checkpoint_port, target_pipeline)
    else:
        return None, evidence_source, None, True

async def _load_for_resolved_manifest(checkpoint_port: Any, manifest: Any) -> _CheckpointEvidence:
    manifest_id = manifest.manifest_id
    checkpoint_tuple = await checkpoint_port.load_for_manifest_id(manifest_id)
    evidence_source = "immutable_manifest_history"
    if checkpoint_tuple is None:
        checkpoint_tuple = await checkpoint_port.load_for_run(
            manifest.pipeline_name,
            manifest.run_id,
        )
        evidence_source = "immutable_run_history"
    return checkpoint_tuple, evidence_source, manifest_id, False

async def _load_for_pipeline_target(checkpoint_port: Any, target_pipeline: str) -> _CheckpointEvidence:
    checkpoint_tuple = await checkpoint_port.load(target_pipeline)
    evidence_source = "mutable_latest_pointer"
    if checkpoint_tuple is None and isinstance(
        checkpoint_port, _LatestCheckpointLookupPort
    ):
        checkpoint_tuple = await checkpoint_port.load_latest_for_pipeline(
            target_pipeline
        )
        if checkpoint_tuple is not None:
            evidence_source = "immutable_pipeline_history_latest"
    return checkpoint_tuple, evidence_source, None, False
