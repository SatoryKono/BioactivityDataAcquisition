# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Extracted control-plane identity routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from threading import BoundedSemaphore
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
    IDENTITY_UNAVAILABLE_VALUES,
    build_control_plane_identity_payload,
)
from bioetl.interfaces.http._identity_display_rows import identity_display_rows
from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_payload

if TYPE_CHECKING:
    from bioetl.interfaces.http._health_server_routing_support import _HealthRoutingHost

# Identity-table is the shared Grafana "ID" panel path. Bound *heavy* I/O so
# Infinity panels never hang forever on large control-plane trees / slow mounts.
# Scope resolve must stay aligned with identity-evidence (no aggressive 2s cut):
# a short resolve timeout produced ``scope_resolve_timeout`` placeholders while
# evidence still resolved the same scope.
_IDENTITY_CHECKPOINT_LOAD_TIMEOUT_SECONDS = 1.5
_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS = 12.0
_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS = 1.5
_IDENTITY_SUMMARY_EXECUTOR = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="bioetl-identity"
)
_IDENTITY_SUMMARY_SLOTS = BoundedSemaphore(4)
_IDENTITY_UNAVAILABLE_VALUES = IDENTITY_UNAVAILABLE_VALUES


async def handle_control_plane_identity_table(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle control-plane-backed identity rows for Overview v3.

    Lightweight path: resolve scope + optional bounded checkpoint metadata and a
    compact evidence *summary* only. Full evidence payload remains on the
    dedicated ``identity-evidence`` route.

    Scope resolution uses the same ``resolve_control_plane_identity_scope`` as
    identity-evidence, with a generous budget so Grafana ID panels do not show
    false ``not available for current scope`` rows on warm control-plane trees.
    """
    _require_run_manifest_port(host)
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
            timezone=query.get("timezone") or "UTC",
        ),
    )


async def handle_control_plane_identity_evidence(
    host: _HealthRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle dedicated Control Plane identity evidence rows."""
    _require_run_manifest_port(host)
    # Same resolve SLA as identity-table so evidence does not hang while the
    # compact table already degrades to an explicit timeout marker.
    try:
        scope = await asyncio.wait_for(
            asyncio.to_thread(resolve_control_plane_identity_scope, host, query),
            timeout=_IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await host._send_payload_response(
            writer,
            200,
            {
                "status": "scope_resolve_timeout",
                "message": (
                    "scope resolve timed out — retry or select exact run_id "
                    "(control-plane store slow)"
                ),
                "rows": [],
                "summary": {
                    "status": "timeout",
                    "reason": "scope_resolve_timeout",
                },
            },
        )
        return
    view = host._read_optional_param(query, "view") or "anchors"
    priority = host._read_optional_param(query, "priority")
    checkpoint_metadata = await _load_identity_checkpoint_metadata(host, scope)

    def _build_evidence() -> dict[str, object]:
        return build_control_plane_identity_evidence_payload(
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
        )

    try:
        evidence_payload = await asyncio.wait_for(
            asyncio.to_thread(_build_evidence),
            timeout=_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await host._send_payload_response(
            writer,
            200,
            {
                "status": "evidence_build_timeout",
                "message": (
                    "identity evidence build timed out — retry or select exact run_id"
                ),
                "rows": [],
                "summary": {
                    "status": "timeout",
                    "reason": "evidence_build_timeout",
                },
            },
        )
        return

    await host._send_payload_response(
        writer,
        200,
        evidence_payload,
    )


def _require_run_manifest_port(host: _HealthRoutingHost) -> None:
    """Typed guard: identity routes require a configured manifest port."""
    if host._run_manifest_port is None:
        raise RuntimeError(
            "run_manifest_port is required for control-plane identity routes"
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
        if not isinstance(identity_evidence_summary, dict):
            return None
        return identity_evidence_summary

    summary, report_summary = await asyncio.gather(
        _bounded_identity_summary(_build),
        _bounded_identity_summary(lambda: _selected_report_summary(scope)),
    )
    if report_summary:
        return {**(summary or {}), **report_summary}
    return summary


async def _bounded_identity_summary(
    build: Callable[[], dict[str, object] | None],
) -> dict[str, object] | None:
    """Bound each source independently so report I/O cannot erase evidence."""
    try:
        return await asyncio.wait_for(
            _identity_summary_worker(build),
            timeout=_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return None


async def _identity_summary_worker(
    build: Callable[[], dict[str, object] | None],
) -> dict[str, object] | None:
    """Keep capacity occupied until synchronous I/O actually finishes."""
    slots = _IDENTITY_SUMMARY_SLOTS
    while not slots.acquire(blocking=False):
        await asyncio.sleep(0.01)
    try:
        pending = _IDENTITY_SUMMARY_EXECUTOR.submit(copy_context().run, build)
    except RuntimeError:
        slots.release()
        raise
    pending.add_done_callback(lambda _: slots.release())
    return await asyncio.wrap_future(pending)


def _selected_report_summary(scope: _IdentityScope) -> dict[str, object]:
    """Read summary fields only from the report for the exact selected run."""
    if scope.selected_run_id is None:
        return {}
    pipeline = (
        scope.resolved_manifest.pipeline_name
        if scope.resolved_manifest
        else scope.requested_pipeline
    )
    report = load_pipeline_run_report_payload(
        run_id=scope.selected_run_id, pipeline_name=pipeline
    )
    if not isinstance(report, dict):
        return {}
    identity = report.get("identity")
    if not isinstance(identity, dict) or (
        str(identity.get("run_id")),
        identity.get("pipeline_name"),
    ) != (scope.selected_run_id, pipeline):
        return {}
    keys = (
        "status",
        "started_at",
        "completed_at",
        "duration_seconds",
        "tracking_coverage",
        "workflow_id",
        "workflow_run_id",
        "workflow_step_id",
    )
    values = dict(identity)
    if values.get("tracking_coverage") in (None, ""):
        values["tracking_coverage"] = report.get("tracking_coverage")
    return {
        "run_status" if key == "status" else key: values[key]
        for key in keys
        if values.get(key) not in (None, "")
    }


def _identity_row_needs_timeout_value(
    row: dict[object, object],
    *,
    pipeline: str,
) -> bool:
    """Return whether a generic identity row should expose the timeout marker."""
    parameter = str(row.get("parameter") or "")
    value = str(row.get("value") or "")
    return (
        parameter == "Provider.Entity [Version]" and value == pipeline
    ) or value in _IDENTITY_UNAVAILABLE_VALUES


def _rewrite_timeout_identity_rows(
    payload: dict[str, object],
    *,
    pipeline: str,
) -> None:
    """Replace generic unavailability copy with an explicit timeout marker."""
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return
    timeout_msg = (
        "scope resolve timed out — retry or select exact run_id "
        "(control-plane store slow)"
    )
    rewritten: list[object] = []
    for row in rows:
        if isinstance(row, dict) and _identity_row_needs_timeout_value(
            row, pipeline=pipeline
        ):
            rewritten.append({**row, "value": timeout_msg})
        else:
            rewritten.append(row)
    payload["rows"] = rewritten


def _timeout_identity_payload(query: dict[str, str]) -> dict[str, object]:
    """Fail-open identity payload when scope resolution exceeds SLA.

    Uses an explicit timeout marker so operators can distinguish slow control-plane
    I/O from a true empty scope (no runs / wrong selector).
    """
    pipeline = query.get("pipeline") or "unknown"
    run_type_raw = query.get("run_type") or ""
    run_types = (
        tuple(part.strip() for part in run_type_raw.split(",") if part.strip()) or ()
    )
    payload = build_control_plane_identity_payload(
        requested_pipeline=pipeline,
        resolved_manifest=None,
        selected_pipelines=(pipeline,),
        selected_run_id=None,
        selected_run_types=run_types,
        resolved_via="scope_resolve_timeout",
        checkpoint_metadata=None,
        identity_evidence_summary=None,
    )
    _rewrite_timeout_identity_rows(payload, pipeline=pipeline)
    payload["display_rows"] = identity_display_rows(
        payload.get("rows"), query.get("timezone") or "UTC"
    )
    return payload
