"""Checkpoint freshness HTTP handler for HealthServer control-plane routes."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.ports import CheckpointPort, RunManifestPort
from bioetl.interfaces.http._health_server_checkpoint_freshness_payloads import (
    build_checkpoint_freshness_ok_payload,
    build_checkpoint_freshness_unknown_payload,
    extract_checkpoint_saved_at_epoch_seconds,
    optional_text,
)
from bioetl.interfaces.http._health_server_checkpoint_lookup import (
    load_checkpoint_freshness_evidence,
)
from bioetl.interfaces.http._health_server_control_plane_scope import (
    _IdentityScope,
    resolve_control_plane_identity_scope,
)

_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS = 12.0
_IDENTITY_CHECKPOINT_LOAD_TIMEOUT_SECONDS = 1.5


class _CheckpointFreshnessHost(Protocol):
    @property
    def _run_manifest_port(self) -> RunManifestPort | None: ...

    @property
    def _checkpoint_port(self) -> CheckpointPort | None: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool: ...

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None: ...


def _resolved_scope_pipeline(scope: _IdentityScope) -> str:
    resolved_manifest = scope.resolved_manifest
    if resolved_manifest is not None:
        return str(resolved_manifest.pipeline_name)
    return str(scope.requested_pipeline)


async def handle_control_plane_checkpoint_freshness(
    host: _CheckpointFreshnessHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle HTTP-backed checkpoint freshness evidence for Control Plane."""
    loaded = await _load_checkpoint_freshness_context(host, writer, query)
    if loaded is None:
        return
    scope, target_pipeline, checkpoint_tuple, evidence_source, manifest_id = loaded
    checkpoint_run_id, metadata = checkpoint_tuple
    saved_at_epoch_seconds = extract_checkpoint_saved_at_epoch_seconds(metadata)
    if saved_at_epoch_seconds is None:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=target_pipeline,
            resolved_via=scope.resolved_via,
            detail=(
                "Persisted checkpoint metadata is missing "
                "checkpoint_saved_at_epoch_seconds."
            ),
            evidence_source=evidence_source,
            manifest_id=manifest_id or optional_text(metadata.get("manifest_id")),
            checkpoint_run_id=str(checkpoint_run_id),
        )
        return

    await host._send_payload_response(
        writer,
        200,
        build_checkpoint_freshness_ok_payload(
            pipeline=target_pipeline,
            resolved_via=scope.resolved_via,
            manifest_id=manifest_id,
            checkpoint_run_id=checkpoint_run_id,
            evidence_source=evidence_source,
            saved_at_epoch_seconds=saved_at_epoch_seconds,
            current_epoch_seconds=current_utc_time().timestamp(),
            metadata=metadata,
        ),
    )


async def _load_checkpoint_freshness_context(
    host: _CheckpointFreshnessHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> tuple[object, str, tuple[object, dict[str, object]], str, str | None] | None:
    """Resolve scope and load checkpoint evidence, or send unknown and return None."""
    assert host._run_manifest_port is not None
    if host._checkpoint_port is None:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=host._read_required_param(query, "pipeline"),
            resolved_via="checkpoint_port_unavailable",
            detail="Checkpoint persistence port is unavailable in this backend.",
            evidence_source="checkpoint_port_missing",
        )
        return None
    try:
        scope = await asyncio.wait_for(
            asyncio.to_thread(resolve_control_plane_identity_scope, host, query),
            timeout=_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=query.get("pipeline") or "unknown",
            resolved_via="scope_resolve_timeout",
            detail="Checkpoint freshness scope resolve timed out.",
            evidence_source="scope_resolve_timeout",
        )
        return None
    target_pipeline = _resolved_scope_pipeline(scope)
    try:
        (
            checkpoint_tuple,
            evidence_source,
            manifest_id,
            aggregate_scope_unknown,
        ) = await asyncio.wait_for(
            load_checkpoint_freshness_evidence(
                host,
                scope=scope,
                target_pipeline=target_pipeline,
            ),
            timeout=_IDENTITY_CHECKPOINT_LOAD_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=target_pipeline,
            resolved_via=scope.resolved_via,
            detail="Checkpoint freshness evidence load timed out.",
            evidence_source="scope_resolve_timeout",
        )
        return None
    if aggregate_scope_unknown:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=target_pipeline,
            resolved_via=scope.resolved_via,
            detail=(
                "Checkpoint freshness requires one exact pipeline scope or run_id; "
                "aggregate scope cannot infer one persisted checkpoint."
            ),
            evidence_source="aggregate_scope_requires_exact_pipeline",
        )
        return None
    if checkpoint_tuple is None:
        await _send_checkpoint_unknown(
            host,
            writer,
            pipeline=target_pipeline,
            resolved_via=scope.resolved_via,
            detail="No persisted checkpoint evidence was found for the current scope.",
            evidence_source=evidence_source,
            manifest_id=manifest_id,
        )
        return None
    return scope, target_pipeline, checkpoint_tuple, evidence_source, manifest_id


async def _send_checkpoint_unknown(
    host: _CheckpointFreshnessHost,
    writer: asyncio.StreamWriter,
    *,
    pipeline: str,
    resolved_via: str,
    detail: str,
    evidence_source: str,
    manifest_id: str | None = None,
    checkpoint_run_id: str | None = None,
) -> None:
    await host._send_payload_response(
        writer,
        200,
        build_checkpoint_freshness_unknown_payload(
            pipeline=pipeline,
            resolved_via=resolved_via,
            detail=detail,
            evidence_source=evidence_source,
            manifest_id=manifest_id,
            checkpoint_run_id=checkpoint_run_id,
        ),
    )


__all__ = ["handle_control_plane_checkpoint_freshness"]
