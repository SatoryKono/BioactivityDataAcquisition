"""Extracted quarantine and control-plane routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
import math
from typing import Protocol, cast
from urllib.parse import unquote

from bioetl.domain.context import current_utc_time
from bioetl.interfaces.http._health_server_control_plane_scope import (
    read_selected_run_id,
    resolve_control_plane_identity_scope,
)
from bioetl.interfaces.http._health_server_identity_evidence import (
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http._health_server_identity_support import (
    build_control_plane_identity_payload,
)
from bioetl.interfaces.http.control_plane_selector_context import (
    RUN_ID_NO_SELECTION,
    build_selector_context_payload,
    build_selector_filter_options_payload,
)
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_prometheus,
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
    _quarantine_service: object | None
    _checkpoint_port: object | None
    _run_manifest_port: object | None
    _run_ledger_port: object | None
    _prometheus_base_url: str

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


async def dispatch_quarantine_request(
    host: _HealthRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route record-level quarantine explorer requests."""
    response_support = cast(_HealthResponseSupport, host)
    if host._quarantine_service is None:
        await response_support._send_response(
            writer,
            503,
            "Quarantine explorer unavailable",
        )
        return

    try:
        if path == "/ops/quarantine/filtered-records":
            await handle_filtered_records(host, writer, query)
            return
        if path == "/ops/quarantine/filtered-stats":
            await handle_filtered_stats(host, writer, query)
            return
        if path == "/ops/quarantine/filtered-timeseries":
            await handle_filtered_timeseries(host, writer, query)
            return
        if path == "/ops/quarantine/filter-options":
            await handle_filter_options(host, writer, query)
            return
        if path.startswith("/ops/quarantine/filtered-record/"):
            payload_hash = unquote(path.rsplit("/", maxsplit=1)[-1]).strip()
            if not payload_hash:
                raise ValueError("Missing payload_hash in path")
            await handle_filtered_record_detail(host, writer, query, payload_hash)
            return
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await response_support._send_response(writer, 400, str(exc))


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


async def dispatch_observability_request(
    host: _HealthRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route dashboard observability helper endpoints."""
    response_support = cast(_HealthResponseSupport, host)
    try:
        if path == "/ops/observability/processed-records":
            await handle_processed_records_table(host, writer, query)
            return
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await response_support._send_response(writer, 400, str(exc))
    except RuntimeError as exc:
        await response_support._send_response(writer, 502, str(exc))


async def handle_processed_records_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle formatted Processed Records table rows for Grafana."""
    pipeline = host._read_required_param(query, "pipeline")
    run_type = host._read_optional_param(query, "run_type")
    payload = await asyncio.to_thread(
        build_processed_records_table_payload_from_prometheus,
        prometheus_base_url=host._prometheus_base_url,
        pipeline=pipeline,
        run_type=run_type,
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_records(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle paginated list endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.list_filtered_records(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        payload_hash=host._read_optional_param(query, "payload_hash"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
        limit=host._read_int_param(query, "limit", default=50, minimum=1),
        offset=host._read_int_param(query, "offset", default=0, minimum=0),
        sort=host._read_optional_param(query, "sort") or "ingestion_ts_desc",
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_stats(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle aggregate stats endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.get_filtered_stats(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        payload_hash=host._read_optional_param(query, "payload_hash"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filter_options(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle variable-options endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.get_filtered_filter_options(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_timeseries(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle time-bucketed trend endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.get_filtered_timeseries(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        payload_hash=host._read_optional_param(query, "payload_hash"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
        bucket=host._read_optional_param(query, "bucket") or "1h",
    )
    await host._send_payload_response(writer, 200, payload)


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
    )
    if response_shape != "list" and dimension == "run_id":
        payload["run_ids"] = [
            value for value in payload.get("items", []) if value != RUN_ID_NO_SELECTION
        ]
    await host._send_payload_response(writer, 200, payload)


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
            view=view,
            priority=priority,
        ),
    )


def _extract_checkpoint_saved_at_epoch_seconds(
    metadata: dict[str, object],
) -> float | None:
    raw_value = metadata.get("checkpoint_saved_at_epoch_seconds")
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _build_checkpoint_freshness_unknown_payload(
    *,
    pipeline: str,
    resolved_via: str,
    detail: str,
    evidence_source: str,
    manifest_id: str | None = None,
    checkpoint_run_id: str | None = None,
) -> dict[str, object]:
    return {
        "pipeline": pipeline,
        "resolved_via": resolved_via,
        "manifest_id": manifest_id,
        "checkpoint_run_id": checkpoint_run_id,
        "evidence_source": evidence_source,
        "checkpoint_present": checkpoint_run_id is not None,
        "saved_at_epoch_seconds": None,
        "age_seconds": None,
        "status": "UNKNOWN",
        "detail": detail,
    }


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
            _build_checkpoint_freshness_unknown_payload(
                pipeline=host._read_required_param(query, "pipeline"),
                resolved_via="checkpoint_port_unavailable",
                detail="Checkpoint persistence port is unavailable in this backend.",
                evidence_source="checkpoint_port_missing",
            ),
        )
        return

    scope = resolve_control_plane_identity_scope(host, query)
    target_pipeline = (
        scope.resolved_manifest.pipeline_name
        if scope.resolved_manifest is not None
        else scope.requested_pipeline
    )

    checkpoint_tuple: tuple[object, dict[str, object]] | None = None
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
    else:
        await host._send_payload_response(
            writer,
            200,
            _build_checkpoint_freshness_unknown_payload(
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
            _build_checkpoint_freshness_unknown_payload(
                pipeline=target_pipeline,
                resolved_via=scope.resolved_via,
                detail="No persisted checkpoint evidence was found for the current scope.",
                evidence_source=evidence_source,
                manifest_id=manifest_id,
            ),
        )
        return

    checkpoint_run_id, metadata = checkpoint_tuple
    saved_at_epoch_seconds = _extract_checkpoint_saved_at_epoch_seconds(metadata)
    if saved_at_epoch_seconds is None:
        await host._send_payload_response(
            writer,
            200,
            _build_checkpoint_freshness_unknown_payload(
                pipeline=target_pipeline,
                resolved_via=scope.resolved_via,
                detail=(
                    "Persisted checkpoint metadata is missing "
                    "checkpoint_saved_at_epoch_seconds."
                ),
                evidence_source=evidence_source,
                manifest_id=manifest_id or _optional_text(metadata.get("manifest_id")),
                checkpoint_run_id=str(checkpoint_run_id),
            ),
        )
        return

    payload_manifest_id = manifest_id
    raw_manifest_id = _optional_text(metadata.get("manifest_id"))
    if payload_manifest_id is None and raw_manifest_id is not None:
        payload_manifest_id = raw_manifest_id
    age_seconds = max(current_utc_time().timestamp() - saved_at_epoch_seconds, 0.0)
    await host._send_payload_response(
        writer,
        200,
        {
            "pipeline": target_pipeline,
            "resolved_via": scope.resolved_via,
            "manifest_id": payload_manifest_id,
            "checkpoint_run_id": str(checkpoint_run_id),
            "evidence_source": evidence_source,
            "checkpoint_present": True,
            "saved_at_epoch_seconds": saved_at_epoch_seconds,
            "age_seconds": age_seconds,
            "status": "OK",
            "detail": "Persisted checkpoint freshness derived from checkpoint metadata.",
        },
    )


async def handle_filtered_record_detail(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
    payload_hash: str,
) -> None:
    """Handle detail endpoint for one filtered Silver record."""
    assert host._quarantine_service is not None
    payload = await host._quarantine_service.get_filtered_record(
        payload_hash=payload_hash,
        pipeline=host._read_required_param(query, "pipeline"),
    )
    if payload is None:
        await host._send_response(writer, 404, _NOT_FOUND_MESSAGE)
        return
    await host._send_payload_response(writer, 200, payload)
