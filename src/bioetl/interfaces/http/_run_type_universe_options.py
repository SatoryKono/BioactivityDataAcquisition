"""Supplement filter-options run_type lists with Prometheus universe labels.

Manifest/report catalogs alone omit telemetry-only pairs that still appear in
``bioetl_overview_pipeline_run_type_universe`` / control-plane universe. Grafana
PromQL panels remain filterable for those types when the HTTP selector merges
them in. Prometheus failures are fail-open: the catalog payload is unchanged.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable

from bioetl.interfaces.http._processed_records_prometheus import (
    PROMETHEUS_QUERY_TIMEOUT_SECONDS,
    _candidate_prometheus_base_urls,
    _fetch_prometheus_query_payload,
    _prometheus_result_list,
    _require_prometheus_success,
)

_LOG = logging.getLogger(__name__)

_UNIVERSE_METRICS = (
    "bioetl_overview_pipeline_run_type_universe",
    "bioetl_control_plane_run_type_universe",
)
_ALL_SCOPE = frozenset({"", "All", "all", "$__all", ".*"})
# Optional Prom supplement must not consume the outer filter-options budget:
# leave headroom so run_bounded_forensic_operation can still return the
# already-built manifest/report catalog instead of HTTP 504.
_FILTER_OPTIONS_PROMETHEUS_RETURN_RESERVE_SECONDS = 1.0


def _pipeline_matcher(pipelines: tuple[str, ...]) -> str:
    concrete = [value for value in pipelines if value not in _ALL_SCOPE]
    if not concrete:
        return ""
    # PromQL regex alternation over concrete pipeline ids.
    joined = "|".join(re.escape(value) for value in sorted(set(concrete)))
    promql_literal = joined.replace("\\", "\\\\").replace('"', '\\"')
    return f'pipeline=~"{promql_literal}"'


def _universe_query(pipelines: tuple[str, ...]) -> str:
    matcher = _pipeline_matcher(pipelines)
    clauses: list[str] = []
    for metric in _UNIVERSE_METRICS:
        selector = f"{metric}{{{matcher}}}" if matcher else metric
        clauses.append(f"count by (run_type) ({selector})")
    return " or ".join(clauses)


def _run_types_from_payload(payload: dict[str, object]) -> set[str]:
    values: set[str] = set()
    for sample in _prometheus_result_list(payload):
        if not isinstance(sample, dict):
            continue
        metric = sample.get("metric")
        if not isinstance(metric, dict):
            continue
        run_type = metric.get("run_type")
        if isinstance(run_type, str) and run_type:
            values.add(run_type)
    return values


def collect_prometheus_run_types(
    *,
    prometheus_base_url: str,
    deadline: float,
    pipelines: tuple[str, ...] = (),
) -> frozenset[str]:
    """Return run_type labels observed in canonical Prometheus universes."""
    query = _universe_query(pipelines)
    errors: list[str] = []
    for base_url in _candidate_prometheus_base_urls(prometheus_base_url):
        remaining = (
            deadline
            - time.monotonic()
            - _FILTER_OPTIONS_PROMETHEUS_RETURN_RESERVE_SECONDS
        )
        if remaining <= 0:
            break
        timeout_seconds = min(remaining, PROMETHEUS_QUERY_TIMEOUT_SECONDS)
        try:
            payload = _fetch_prometheus_query_payload(
                prometheus_base_url=base_url,
                query=query,
                timeout_seconds=timeout_seconds,
            )
            _require_prometheus_success(payload)
            return frozenset(_run_types_from_payload(payload))
        except RuntimeError as exc:
            errors.append(f"{base_url}: {exc}")
    if errors:
        _LOG.debug("prometheus run_type universe unavailable: %s", "; ".join(errors))
    return frozenset()


def _seen_values(items: Iterable[object]) -> set[object]:
    seen: set[object] = set()
    for item in items:
        if isinstance(item, dict):
            seen.add(item.get("value"))
        else:
            seen.add(item)
    return seen


def supplement_prometheus_run_type_options(
    payload: dict[str, object],
    *,
    prometheus_base_url: str,
    deadline: float,
    response_shape: str,
    pipelines: tuple[str, ...] = (),
) -> dict[str, object]:
    """Append telemetry-only run_type values missing from catalog/report items."""
    raw_items = payload.get("items", [])
    items = list(raw_items) if isinstance(raw_items, list) else []
    seen = _seen_values(items)
    for run_type in sorted(
        collect_prometheus_run_types(
            prometheus_base_url=prometheus_base_url,
            deadline=deadline,
            pipelines=pipelines,
        )
    ):
        if run_type in seen:
            continue
        seen.add(run_type)
        if response_shape == "options":
            items.append({"text": run_type, "value": run_type})
        else:
            items.append(run_type)
    return {**payload, "items": items}


__all__ = (
    "collect_prometheus_run_types",
    "supplement_prometheus_run_type_options",
)
