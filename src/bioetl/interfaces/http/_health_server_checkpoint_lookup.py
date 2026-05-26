"""Checkpoint freshness lookup helpers for health-server routing."""

from __future__ import annotations

from typing import Protocol

from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

_CheckpointTuple = tuple[object, dict[str, object]]
_CheckpointEvidence = tuple[_CheckpointTuple | None, str, str | None, bool]


class _CheckpointLookupHost(Protocol):
    _checkpoint_port: object | None

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool: ...


async def load_checkpoint_freshness_evidence(
    host: _CheckpointLookupHost,
    *,
    scope: _IdentityScope,
    target_pipeline: str,
) -> _CheckpointEvidence:
    checkpoint_tuple: _CheckpointTuple | None = None
    evidence_source = "mutable_latest_pointer"
    manifest_id: str | None = None

    if scope.selected_run_id is not None and scope.resolved_manifest is not None:
        manifest_id = scope.resolved_manifest.manifest_id
        checkpoint_tuple = await host._checkpoint_port.load_for_manifest_id(manifest_id)
        evidence_source = "immutable_manifest_history"
        if checkpoint_tuple is None:
            checkpoint_tuple = await host._checkpoint_port.load_for_run(
                scope.resolved_manifest.pipeline_name,
                scope.resolved_manifest.run_id,
            )
            evidence_source = "immutable_run_history"
    elif (
        scope.selected_pipelines
        or not host._is_all_scope_token(scope.requested_pipeline)
    ):
        checkpoint_tuple = await host._checkpoint_port.load(target_pipeline)
        if checkpoint_tuple is None and hasattr(
            host._checkpoint_port, "load_latest_for_pipeline"
        ):
            checkpoint_tuple = await host._checkpoint_port.load_latest_for_pipeline(
                target_pipeline
            )
            if checkpoint_tuple is not None:
                evidence_source = "immutable_pipeline_history_latest"
    else:
        return None, evidence_source, None, True

    return checkpoint_tuple, evidence_source, manifest_id, False
