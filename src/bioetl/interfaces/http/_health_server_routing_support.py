"""Extracted quarantine and control-plane routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import Protocol, cast
from urllib.parse import unquote

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
    _run_manifest_port: object | None
    _run_ledger_port: object | None
    _prometheus_base_url: str

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

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
    selected_run_id = _read_selected_run_id(host, query)
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
        selected_run_id=_read_selected_run_id(host, query),
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_control_plane_identity_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed identity rows for Overview v3."""
    assert host._run_manifest_port is not None
    requested_pipeline = host._read_required_param(query, "pipeline")
    selected_pipelines = host._read_scope_csv_param(query, "pipeline")
    selected_run_types = host._read_scope_csv_param(query, "run_type")
    selected_run_id = _read_selected_run_id(host, query)

    manifests = tuple(
        manifest
        for manifest in host._run_manifest_port.list_all()
        if (not selected_pipelines or manifest.pipeline_name in selected_pipelines)
        and (not selected_run_types or str(manifest.run_type) in selected_run_types)
    )
    resolved_manifest = next(
        (
            manifest
            for manifest in manifests
            if selected_run_id is not None and str(manifest.run_id) == selected_run_id
        ),
        None,
    )
    resolved_via = "selected_run_id"
    if resolved_manifest is None:
        if len(selected_pipelines) != 1:
            resolved_via = "aggregate_scope_requires_exact_run_id"
        else:
            resolved_manifest = manifests[-1] if manifests else None
            resolved_via = (
                "latest_manifest_for_scope"
                if resolved_manifest is not None
                else "no_manifest_for_scope"
            )

    await host._send_payload_response(
        writer,
        200,
        build_control_plane_identity_payload(
            requested_pipeline=requested_pipeline,
            resolved_manifest=resolved_manifest,
            selected_pipelines=selected_pipelines,
            selected_run_id=selected_run_id,
            selected_run_types=selected_run_types,
            resolved_via=resolved_via,
        ),
    )


def _read_selected_run_id(
    host: _HealthRoutingHost,
    query: dict[str, str],
) -> str | None:
    selected_run_id = host._read_optional_param(query, "run_id")
    return None if selected_run_id in {None, RUN_ID_NO_SELECTION} else selected_run_id


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
