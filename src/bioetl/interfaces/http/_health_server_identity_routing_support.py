# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Extracted control-plane identity routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bioetl.interfaces.http._health_server_checkpoint_lookup import (
    load_checkpoint_freshness_evidence,
)
from bioetl.interfaces.http._health_server_control_plane_scope import (
    _IdentityScope,
    resolve_control_plane_identity_scope,
)
from bioetl.interfaces.http._health_server_identity_evidence import (
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http._health_server_identity_support import (
    build_control_plane_identity_payload,
)

if TYPE_CHECKING:
    from bioetl.interfaces.http._health_server_routing_support import _HealthRoutingHost

# Identity-table is the shared Grafana "ID" panel path. Bound heavy I/O so Infinity
# panels never hang forever on large control-plane trees / slow bind mounts.
_IDENTITY_CHECKPOINT_LOAD_TIMEOUT_SECONDS = 1.5
_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS = 2.0
_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS = 1.5


async def handle_control_plane_identity_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed identity rows for Overview v3.

    Lightweight path: resolve scope + optional bounded checkpoint metadata and a
    compact evidence *summary* only. Full evidence payload remains on the
    dedicated ``identity-evidence`` route.
    """
    assert host._run_manifest_port is not None
    try:
        scope = await asyncio.wait_for(
            asyncio.to_thread(resolve_control_plane_identity_scope, host, query),
            timeout=_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await host._send_payload_response(
            writer,
            200,
            _timeout_identity_payload(query),
        )
        return

    checkpoint_metadata = await _load_identity_checkpoint_metadata(host, scope)
    summary = await _build_identity_evidence_summary(
        host,
        scope=scope,
        checkpoint_metadata=checkpoint_metadata,
    )

    await host._send_payload_response(
        writer,
        200,
        build_control_plane_identity_payload(
            requested_pipeline=scope.requested_pipeline,
            resolved_manifest=scope.resolved_manifest,
            selected_pipelines=scope.selected_pipelines,
            selected_run_id=scope.selected_run_id,
            selected_run_types=scope.selected_run_types,
            resolved_via=scope.resolved_via,
            checkpoint_metadata=checkpoint_metadata,
            identity_evidence_summary=summary,
        ),
    )


async def handle_control_plane_identity_evidence(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle dedicated Control Plane identity evidence rows."""
    assert host._run_manifest_port is not None
    scope = await asyncio.to_thread(resolve_control_plane_identity_scope, host, query)
    view = host._read_optional_param(query, "view") or "anchors"
    priority = host._read_optional_param(query, "priority")
    checkpoint_metadata = await _load_identity_checkpoint_metadata(host, scope)

    await host._send_payload_response(
        writer,
        200,
        build_control_plane_identity_evidence_payload(
            requested_pipeline=scope.requested_pipeline,
            resolved_manifest=scope.resolved_manifest,
            selected_pipelines=scope.selected_pipelines,
            selected_run_id=scope.selected_run_id,
            selected_run_types=scope.selected_run_types,
            resolved_via=scope.resolved_via,
            ledger_port=host._run_ledger_port,
            checkpoint_metadata=checkpoint_metadata,
            view=view,
            priority=priority,
        ),
    )


async def _load_identity_checkpoint_metadata(
    host: _HealthRoutingHost,
    scope: _IdentityScope,
) -> dict[str, object] | None:
    if host._checkpoint_port is None:
        return None
    target_pipeline = (
        scope.resolved_manifest.pipeline_name
        if scope.resolved_manifest is not None
        else scope.requested_pipeline
    )
    try:
        (
            checkpoint_tuple,
            _,
            _,
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
        return None
    if aggregate_scope_unknown or checkpoint_tuple is None:
        return None
    _, checkpoint_metadata = checkpoint_tuple
    return checkpoint_metadata


async def _build_identity_evidence_summary(
    host: _HealthRoutingHost,
    *,
    scope: _IdentityScope,
    checkpoint_metadata: dict[str, object] | None,
) -> dict[str, object] | None:
    """Build only the overview summary used by the compact ID table.

    Bound wall time so large ledgers / slow mounts degrade to empty health rows
    instead of Grafana Infinity timeouts.
    """

    def _build() -> dict[str, object] | None:
        identity_evidence_summary = build_control_plane_identity_evidence_payload(
            requested_pipeline=scope.requested_pipeline,
            resolved_manifest=scope.resolved_manifest,
            selected_pipelines=scope.selected_pipelines,
            selected_run_id=scope.selected_run_id,
            selected_run_types=scope.selected_run_types,
            resolved_via=scope.resolved_via,
            ledger_port=host._run_ledger_port,
            checkpoint_metadata=checkpoint_metadata,
            view="overview",
        ).get("summary")
        return (
            identity_evidence_summary
            if isinstance(identity_evidence_summary, dict)
            else None
        )

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_build),
            timeout=_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return None


def _timeout_identity_payload(query: dict[str, str]) -> dict[str, object]:
    """Fail-open identity payload when scope resolution exceeds SLA."""
    pipeline = query.get("pipeline") or "unknown"
    run_type_raw = query.get("run_type") or ""
    run_types = (
        tuple(part.strip() for part in run_type_raw.split(",") if part.strip()) or ()
    )
    return build_control_plane_identity_payload(
        requested_pipeline=pipeline,
        resolved_manifest=None,
        selected_pipelines=(pipeline,),
        selected_run_id=None,
        selected_run_types=run_types,
        resolved_via="scope_resolve_timeout",
        checkpoint_metadata=None,
        identity_evidence_summary=None,
    )
