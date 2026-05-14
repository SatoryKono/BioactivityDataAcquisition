"""Extracted quarantine and control-plane routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import Protocol, cast
from urllib.parse import unquote

_NOT_FOUND_MESSAGE = "Not Found"
_RUN_ID_NO_SELECTION = "-"


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
        if path == "/ops/control-plane/identity-table":
            await handle_control_plane_identity_table(host, writer, query)
            return
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await response_support._send_response(writer, 400, str(exc))


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
    requested_pipeline = host._read_required_param(query, "pipeline")
    selected_pipelines = host._read_scope_csv_param(query, "pipeline")
    dimension = host._read_optional_param(query, "dimension") or "run_id"
    if dimension != "run_id":
        raise ValueError(f"Unsupported control-plane filter dimension: {dimension}")

    selected_run_types = host._read_scope_csv_param(query, "run_type")
    run_ids = tuple(
        str(manifest.run_id)
        for manifest in host._run_manifest_port.list_all()
        if (not selected_pipelines or manifest.pipeline_name in selected_pipelines)
        and (not selected_run_types or str(manifest.run_type) in selected_run_types)
    )
    response_shape = host._read_optional_param(query, "response_shape") or "object"
    if response_shape == "list":
        await host._send_payload_response(
            writer,
            200,
            {"items": [_RUN_ID_NO_SELECTION, *run_ids]},
        )
        return
    await host._send_payload_response(
        writer,
        200,
        {
            "pipeline": requested_pipeline,
            "run_type": list(selected_run_types),
            "run_ids": list(run_ids),
        },
    )


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
    selected_run_id = host._read_optional_param(query, "run_id")
    if selected_run_id == _RUN_ID_NO_SELECTION:
        selected_run_id = None

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
        {
            "pipeline": requested_pipeline,
            "run_type": list(selected_run_types),
            "selected_run_id": selected_run_id,
            "resolved_via": resolved_via,
            "rows": _build_identity_rows(
                requested_pipeline=requested_pipeline,
                resolved_manifest=resolved_manifest,
                selected_pipelines=selected_pipelines,
                selected_run_id=selected_run_id,
            ),
        },
    )


def _build_identity_rows(
    *,
    requested_pipeline: str,
    resolved_manifest: object | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
) -> list[dict[str, str]]:
    manifest_unavailable = (
        "select one concrete pipeline or exact run_id"
        if len(selected_pipelines) != 1 and resolved_manifest is None
        else "not available for current scope"
    )
    provenance_unavailable = "not available in selected manifest"
    code_provenance = (
        getattr(resolved_manifest, "code_provenance", None)
        if resolved_manifest is not None
        else None
    )
    return [
        _identity_row(
            "manifest_id",
            getattr(resolved_manifest, "manifest_id", None),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "run_id",
            getattr(resolved_manifest, "run_id", None) or selected_run_id,
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "pipeline name",
            getattr(resolved_manifest, "pipeline_name", None) or requested_pipeline,
            unavailable="not available for current scope",
        ),
        _identity_row(
            "pipelineversion",
            getattr(code_provenance, "pipeline_version", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "git commit hash",
            getattr(code_provenance, "git_commit", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "config hash",
            getattr(code_provenance, "config_hash", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "execution fingerprint",
            getattr(resolved_manifest, "execution_fingerprint", None),
            unavailable=manifest_unavailable,
        ),
        _identity_row(
            "schema contract",
            getattr(code_provenance, "contract_ref", None),
            unavailable=provenance_unavailable,
        ),
        _identity_row(
            "version",
            getattr(code_provenance, "contract_version", None),
            unavailable=provenance_unavailable,
        ),
    ]


def _identity_row(parameter: str, value: object | None, *, unavailable: str) -> dict[str, str]:
    return {
        "parameter": parameter,
        "value": _display(value, unavailable=unavailable),
    }


def _display(value: object | None, *, unavailable: str) -> str:
    if value is None:
        return unavailable
    text = str(value).strip()
    return text or unavailable


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
