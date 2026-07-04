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


async def handle_control_plane_identity_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed identity rows for Overview v3."""
    assert host._run_manifest_port is not None
    scope = await asyncio.to_thread(resolve_control_plane_identity_scope, host, query)
    checkpoint_metadata = await _load_identity_checkpoint_metadata(host, scope)

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
    summary = (
        identity_evidence_summary
        if isinstance(identity_evidence_summary, dict)
        else None
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
    (
        checkpoint_tuple,
        _,
        _,
        aggregate_scope_unknown,
    ) = await load_checkpoint_freshness_evidence(
        host,
        scope=scope,
        target_pipeline=target_pipeline,
    )
    if aggregate_scope_unknown or checkpoint_tuple is None:
        return None
    _, checkpoint_metadata = checkpoint_tuple
    return checkpoint_metadata
