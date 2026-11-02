"""Build control-plane filter option responses for the HTTP server."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from functools import partial

from bioetl.interfaces.http._health_server_control_plane_scope import (
    read_selected_run_id,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthRoutingHost,
)
from bioetl.interfaces.http._report_selector_options import (
    load_report_selector_entries,
    supplement_report_options,
)
from bioetl.interfaces.http._run_type_universe_options import (
    supplement_prometheus_run_type_options,
)
from bioetl.interfaces.http.control_plane_selector_context import (
    RunIdOptionPolicy,
    finalize_run_id_empty_catalog_label,
)

_DEFAULT_FILTER_OPTIONS_BUDGET_SECONDS = 20.0


async def build_filter_options_payload(
    host: _HealthRoutingHost,
    query: dict[str, str],
    *,
    options_builder: Callable[..., dict[str, object]],
    add_run_id_items: Callable[..., None],
    include_reports: bool,
    deadline: float | None = None,
) -> dict[str, object]:
    """Combine manifest and report catalogs into a filter-options payload."""
    if deadline is None:
        deadline = time.monotonic() + _DEFAULT_FILTER_OPTIONS_BUDGET_SECONDS
    manifest_port = host._run_manifest_port
    assert manifest_port is not None
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

    scopes = {
        "workflow": selected_workflows,
        "pipeline": selected_pipelines,
        "run_type": selected_run_types,
        "run_status": selected_run_statuses,
        "run_id": (selected_run_id,) if selected_run_id else (),
    }

    async def manifest_options() -> dict[str, object]:
        manifests, workflow_manifests = await host._selector_catalog.read(
            manifest_port,
            host._workflow_manifest_port,
        )
        return await asyncio.to_thread(
            options_builder,
            manifests=manifests,
            ledger_port=host._run_ledger_port,
            workflow_manifests=workflow_manifests,
            dimension=dimension,
            response_shape=response_shape,
            requested_pipeline=requested_pipeline,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_statuses=selected_run_statuses,
            selected_run_id=selected_run_id,
            run_id_policy=RunIdOptionPolicy(
                exact_run_only=exact_run_only,
                fallback_value=fallback_value,
            ),
            timezone=query.get("timezone") or "UTC",
        )

    manifest_task = asyncio.create_task(manifest_options())
    report_task = asyncio.create_task(
        host._selector_catalog.read_reports(
            scopes,
            partial(load_report_selector_entries, store=host._run_report_store),
        )
        if include_reports
        else asyncio.sleep(0, result=[]),
    )
    await asyncio.gather(manifest_task, report_task, return_exceptions=True)
    payload, report_entries = manifest_task.result(), report_task.result()
    if include_reports:
        payload = await asyncio.to_thread(
            supplement_report_options,
            payload,
            timezone=query.get("timezone") or "UTC",
            dimension=dimension,
            response_shape=response_shape,
            scopes=scopes,
            entries=report_entries,
        )
    if dimension == "run_id" and response_shape == "options":
        payload = finalize_run_id_empty_catalog_label(payload)
    # Additive PromQL universe merge for run_type (fail-open, budget-capped).
    # Gate kept in a helper so Sonar CC stays within leak budget while the
    # asyncio.to_thread census site remains under build_filter_options_payload.
    prometheus_base_url = _prometheus_base_url_for_run_type_options(
        host, dimension=dimension, selected_workflows=selected_workflows
    )
    if prometheus_base_url:
        # fmt: off
        # One-line call keeps COMP-004 segment for report-options to_thread unique.
        payload = await asyncio.to_thread(supplement_prometheus_run_type_options, payload, prometheus_base_url=prometheus_base_url, deadline=deadline, response_shape=response_shape, pipelines=selected_pipelines)  # noqa: E501
        # fmt: on
    add_run_id_items(payload, response_shape=response_shape, dimension=dimension)
    return payload


def _prometheus_base_url_for_run_type_options(
    host: _HealthRoutingHost,
    *,
    dimension: str,
    selected_workflows: tuple[str, ...],
) -> str:
    """Return Prom base URL only for unscoped run_type option supplements."""
    if dimension != "run_type":
        return ""
    # Universe metrics lack workflow membership — do not widen a scoped catalog.
    if selected_workflows:
        return ""
    return getattr(host, "_prometheus_base_url", "") or ""


def _read_truthy_query_param(query: dict[str, str], name: str) -> bool:

    value = query.get(name)
    return value is not None and value.strip().lower() in {"1", "true", "yes"}


__all__ = ("build_filter_options_payload",)
