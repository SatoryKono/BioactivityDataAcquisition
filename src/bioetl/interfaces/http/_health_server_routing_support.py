"""Extracted quarantine and control-plane routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import Protocol, cast

from bioetl.domain.context import current_utc_time
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
    read_selected_run_id,
    resolve_control_plane_identity_scope,
)
from bioetl.interfaces.http._health_server_identity_evidence import (
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http._health_server_identity_support import (
    build_control_plane_identity_payload,
)
from bioetl.interfaces.http._health_server_observability_routing import (
    dispatch_observability_request,
)
from bioetl.interfaces.http._health_server_quarantine_routing import (
    dispatch_quarantine_request,
)
from bioetl.interfaces.http.control_plane_selector_context import (
    RUN_ID_NO_SELECTION,
    build_selector_context_payload,
    build_selector_filter_options_payload,
)

_NOT_FOUND_MESSAGE = "Not Found"


class _HealthResponseSupport(Protocol):
    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None: ...

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None: ...

    async def _handle_request_error(
        self,
        writer: asyncio.StreamWriter,
        error: BaseException,
    ) -> None: ...


class _HealthRoutingHost(_HealthResponseSupport, Protocol):
    _checkpoint_port: object | None
    _run_manifest_port: object | None
    _run_ledger_port: object | None

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool: ...

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...


async def dispatch_control_plane_request(
    host: _HealthRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route control-plane selector helper endpoints."""
    response_support = cast(_HealthResponseSupport, host)
    if host._run_manifest_port is None:
        await response_support._send_response(
            writer,
            503,
            "Control-plane selector catalog unavailable",
        )
        return

    try:
        if path == "/ops/control-plane/filter-options":
            await handle_control_plane_filter_options(host, writer, query)
            return
        if path == "/ops/control-plane/selector-context":
            await handle_control_plane_selector_context(host, writer, query)
            return
        if path == "/ops/control-plane/identity-table":
            await handle_control_plane_identity_table(host, writer, query)
            return
        if path == "/ops/control-plane/identity-evidence":
            await handle_control_plane_identity_evidence(host, writer, query)
            return
        if path == "/ops/control-plane/checkpoint-freshness":
            await handle_control_plane_checkpoint_freshness(host, writer, query)
            return
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await response_support._send_response(writer, 400, str(exc))


async def handle_control_plane_filter_options(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed selector options for Grafana variables."""
    assert host._run_manifest_port is not None
    dimension = host._read_optional_param(query, "dimension") or "run_id"
    requested_pipeline = (
        host._read_required_param(query, "pipeline")
        if dimension == "run_id"
        else host._read_optional_param(query, "pipeline")
    )
    selected_pipelines = host._read_scope_csv_param(query, "pipeline")
    selected_workflows = host._read_scope_csv_param(query, "workflow")
    selected_run_types = host._read_scope_csv_param(query, "run_type")
    selected_run_statuses = host._read_scope_csv_param(query, "run_status")
    selected_run_id = read_selected_run_id(host, query)
    response_shape = host._read_optional_param(query, "response_shape") or "object"
    exact_run_only = _read_truthy_query_param(query, "exact_run_only")
    fallback_value = host._read_optional_param(query, "fallback_value")

    payload = build_selector_filter_options_payload(
        manifests=host._run_manifest_port.list_all(),
        ledger_port=host._run_ledger_port,
        dimension=dimension,
        response_shape=response_shape,
        requested_pipeline=requested_pipeline,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=selected_run_id,
        exact_run_only=exact_run_only,
        fallback_value=fallback_value,
    )
    if response_shape != "list" and dimension == "run_id":
        payload["run_ids"] = [
            value for value in payload.get("items", []) if value != RUN_ID_NO_SELECTION
        ]
    await host._send_payload_response(writer, 200, payload)


def _read_truthy_query_param(query: dict[str, str], name: str) -> bool:
    value = query.get(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes"}


async def handle_control_plane_selector_context(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Resolve a coherent selector tuple for dashboard selector shells."""
    assert host._run_manifest_port is not None
    payload = build_selector_context_payload(
        manifests=host._run_manifest_port.list_all(),
        ledger_port=host._run_ledger_port,
        selected_workflows=host._read_scope_csv_param(query, "workflow"),
        selected_pipelines=host._read_scope_csv_param(query, "pipeline"),
        selected_run_types=host._read_scope_csv_param(query, "run_type"),
        selected_run_statuses=host._read_scope_csv_param(query, "run_status"),
        selected_run_id=read_selected_run_id(host, query),
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_control_plane_identity_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed identity rows for Overview v3."""
    assert host._run_manifest_port is not None
    scope = resolve_control_plane_identity_scope(host, query)
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
    scope = resolve_control_plane_identity_scope(host, query)
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


def _resolved_scope_pipeline(scope: object) -> str:
    resolved_manifest = getattr(scope, "resolved_manifest", None)
    if resolved_manifest is not None:
        return str(resolved_manifest.pipeline_name)
    return str(scope.requested_pipeline)


async def handle_control_plane_checkpoint_freshness(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle HTTP-backed checkpoint freshness evidence for Control Plane."""
    assert host._run_manifest_port is not None
    if host._checkpoint_port is None:
        await host._send_payload_response(
            writer,
            200,
            build_checkpoint_freshness_unknown_payload(
                pipeline=host._read_required_param(query, "pipeline"),
                resolved_via="checkpoint_port_unavailable",
                detail="Checkpoint persistence port is unavailable in this backend.",
                evidence_source="checkpoint_port_missing",
            ),
        )
        return

    scope = resolve_control_plane_identity_scope(host, query)
    target_pipeline = _resolved_scope_pipeline(scope)

    (
        checkpoint_tuple,
        evidence_source,
        manifest_id,
        aggregate_scope_unknown,
    ) = await load_checkpoint_freshness_evidence(
        host,
        scope=scope,
        target_pipeline=target_pipeline,
    )
    if aggregate_scope_unknown:
        await host._send_payload_response(
            writer,
            200,
            build_checkpoint_freshness_unknown_payload(
                pipeline=target_pipeline,
                resolved_via=scope.resolved_via,
                detail=(
                    "Checkpoint freshness requires one exact pipeline scope or run_id; "
                    "aggregate scope cannot infer one persisted checkpoint."
                ),
                evidence_source="aggregate_scope_requires_exact_pipeline",
            ),
        )
        return

    if checkpoint_tuple is None:
        await host._send_payload_response(
            writer,
            200,
            build_checkpoint_freshness_unknown_payload(
                pipeline=target_pipeline,
                resolved_via=scope.resolved_via,
                detail="No persisted checkpoint evidence was found for the current scope.",
                evidence_source=evidence_source,
                manifest_id=manifest_id,
            ),
        )
        return

    checkpoint_run_id, metadata = checkpoint_tuple
    saved_at_epoch_seconds = extract_checkpoint_saved_at_epoch_seconds(metadata)
    if saved_at_epoch_seconds is None:
        await host._send_payload_response(
            writer,
            200,
            build_checkpoint_freshness_unknown_payload(
                pipeline=target_pipeline,
                resolved_via=scope.resolved_via,
                detail=(
                    "Persisted checkpoint metadata is missing "
                    "checkpoint_saved_at_epoch_seconds."
                ),
                evidence_source=evidence_source,
                manifest_id=manifest_id or optional_text(metadata.get("manifest_id")),
                checkpoint_run_id=str(checkpoint_run_id),
            ),
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


__all__ = [
    "dispatch_control_plane_request",
    "dispatch_observability_request",
    "dispatch_quarantine_request",
]
