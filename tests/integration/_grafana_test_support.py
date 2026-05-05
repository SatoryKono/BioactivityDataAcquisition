"""Shared helper utilities for Grafana dashboard integration tests."""

from __future__ import annotations

import io
import json
import logging
import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

_PROMQL_METRIC_SELECTOR_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^{}]*)\}")
_PROMQL_LABEL_MATCHER_RE = re.compile(r'([a-zA-Z_]\w*)\s*(=~|=|!=|!~)\s*"')

__all__ = [
    "_PROMQL_METRIC_SELECTOR_RE",
    "_assert_provider_health_variable_contract",
    "_assert_silver_reject_explorer_variable_contract",
    "_assert_standard_variable_contract",
    "_collect_dashboard_links",
    "_emit_sample_structured_log",
    "_extract_selector_labels",
    "_infer_recording_rule_labels",
    "_unknown_metrics_for_query",
    "get_all_valid_metric_names",
    "get_dashboard_files",
    "get_dashboard_panels",
    "get_dashboard_prometheus_queries",
    "get_metric_label_sets",
    "get_panel_expressions",
    "load_dashboard",
]


@cache
def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for histograms."""
    from bioetl.infrastructure.observability import metrics

    all_valid_names: set[str] = set()

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if not hasattr(item, "_name"):
            continue
        base_name = item._name
        all_valid_names.add(base_name)
        all_valid_names.add(f"{base_name}_created")

        class_name = type(item).__name__
        if "Histogram" in class_name or "Summary" in class_name:
            all_valid_names.update(
                {
                    f"{base_name}_bucket",
                    f"{base_name}_sum",
                    f"{base_name}_count",
                }
            )
        elif "Counter" in class_name:
            all_valid_names.add(f"{base_name}_total")

    rules_path = Path("grafana/prometheus-rules/bioetl_observability.yml")
    rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    for group in rules_payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            if isinstance(record_name, str):
                all_valid_names.add(record_name)

    return all_valid_names


def _register_runtime_metric_label_sets(
    label_sets: dict[str, frozenset[str]],
) -> None:
    from bioetl.infrastructure.observability.prometheus_metric_registries import (
        COUNTERS,
        GAUGES,
        HISTOGRAMS,
    )

    _register_simple_metric_label_sets(label_sets, COUNTERS)
    _register_simple_metric_label_sets(label_sets, GAUGES)
    _register_histogram_label_sets(label_sets, HISTOGRAMS)


def _register_simple_metric_label_sets(
    label_sets: dict[str, frozenset[str]], metrics: dict[str, Any]
) -> None:
    for name, metric in metrics.items():
        label_sets[name] = frozenset(metric._labelnames)


def _register_histogram_label_sets(
    label_sets: dict[str, frozenset[str]], histograms: dict[str, Any]
) -> None:
    for name, metric in histograms.items():
        _register_histogram_label_set(label_sets, name=name, label_names=metric._labelnames)


def _register_histogram_label_set(
    label_sets: dict[str, frozenset[str]], *, name: str, label_names: tuple[str, ...]
) -> None:
    base_labels = frozenset(label_names)
    label_sets[name] = base_labels
    label_sets[f"{name}_bucket"] = base_labels | {"le"}
    label_sets[f"{name}_sum"] = base_labels
    label_sets[f"{name}_count"] = base_labels


def _fallback_recording_rule_labels(
    expr: str, label_sets: dict[str, frozenset[str]]
) -> frozenset[str]:
    referenced_label_sets = [
        label_sets[metric_name]
        for metric_name in re.findall(r"\b(bioetl_[a-z0-9_]+)\b", expr)
        if metric_name in label_sets
    ]
    if not referenced_label_sets:
        return frozenset()

    shared_labels = set(referenced_label_sets[0])
    for candidate in referenced_label_sets[1:]:
        shared_labels &= set(candidate)
    return frozenset(shared_labels)


def _recording_rule_labels(
    expr: str, label_sets: dict[str, frozenset[str]]
) -> frozenset[str]:
    inferred_labels = _infer_recording_rule_labels(expr)
    return inferred_labels or _fallback_recording_rule_labels(expr, label_sets)


def _register_recording_rule_label_sets(
    label_sets: dict[str, frozenset[str]],
) -> None:
    rules_path = Path("grafana/prometheus-rules/bioetl_observability.yml")
    rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    for group in rules_payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            expr = rule.get("expr")
            if isinstance(record_name, str) and isinstance(expr, str):
                static_labels = frozenset(
                    str(label_name)
                    for label_name in rule.get("labels", {})
                    if isinstance(label_name, str)
                )
                label_sets[record_name] = (
                    label_sets.get(record_name, frozenset())
                    | _recording_rule_labels(expr, label_sets)
                    | static_labels
                )


@cache
def get_metric_label_sets() -> dict[str, frozenset[str]]:
    """Return the effective label set for shipped metrics and recording rules."""
    label_sets: dict[str, frozenset[str]] = {
        "up": frozenset({"job", "instance"}),
    }

    _register_runtime_metric_label_sets(label_sets)
    _register_recording_rule_label_sets(label_sets)

    return label_sets


@cache
def get_dashboard_files() -> tuple[Path, ...]:
    """Get all Grafana dashboard JSON files."""
    return tuple(Path("grafana/dashboards").glob("*.json"))


@cache
def load_dashboard(dashboard_path: Path) -> dict:
    """Load one dashboard JSON payload."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        return json.load(f)


@cache
def _load_logging_helpers() -> tuple[Any, Any]:
    """Import logging helpers lazily so collection does not bootstrap observability."""
    from bioetl.infrastructure.observability.logging_config import configure_logging
    from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

    return configure_logging, UnifiedLogger


def _walk_panels(panels: list[dict]) -> list[dict]:
    """Flatten dashboard panels, including row-contained nested panels."""
    flattened: list[dict] = []
    for panel in panels:
        flattened.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            flattened.extend(_walk_panels(nested))
    return flattened


def get_dashboard_panels(dashboard: dict) -> list[dict]:
    """Get all panels, including nested row panels."""
    panels = _walk_panels(list(dashboard.get("panels", [])))
    for row in dashboard.get("rows", []):
        panels.extend(_walk_panels(row.get("panels", [])))
    return panels


def get_panel_expressions(dashboard: dict) -> list[str]:
    """Get all PromQL expressions from dashboard panels."""
    expressions: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if isinstance(expr, str) and expr:
                expressions.append(expr)
    return expressions


def get_dashboard_prometheus_queries(dashboard: dict) -> list[str]:
    """Collect Prometheus-backed queries from panels and variables."""
    queries = get_panel_expressions(dashboard)

    for variable in dashboard.get("templating", {}).get("list", []):
        if variable.get("datasource") != "Prometheus":
            continue
        query = variable.get("query", {})
        if isinstance(query, dict):
            query_text = query.get("query")
            if isinstance(query_text, str) and query_text:
                queries.append(query_text)

    return queries


def _collect_dashboard_links(dashboard: dict) -> list[dict]:
    """Collect top-level, panel, data, and field links."""
    links = list(dashboard.get("links", []))
    for panel in get_dashboard_panels(dashboard):
        links.extend(panel.get("links", []))
        links.extend(panel.get("options", {}).get("dataLinks", []))
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        if isinstance(defaults, dict):
            links.extend(defaults.get("links", []))
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            for prop in override.get("properties", []):
                if prop.get("id") == "links":
                    links.extend(prop.get("value", []))
    return links


def _unknown_metrics_for_query(query: str, valid_metrics: set[str]) -> list[str]:
    """Return metric-like tokens that are not present in the known metric set."""
    unknown_metrics: list[str] = []
    for metric in re.findall(r"(bioetl_[a-z0-9_]+)", query):
        if metric in valid_metrics:
            continue
        base = re.sub(r"(_total|_bucket|_sum|_count|_created)$", "", metric)
        if base not in valid_metrics:
            unknown_metrics.append(metric)
    return unknown_metrics


def _infer_recording_rule_labels(expr: str) -> frozenset[str]:
    """Infer the exported label set for simple recording-rule aggregations."""
    match = re.search(r"\b(?:sum|max|min|avg|count)\s+by\s*\(([^)]*)\)", expr)
    if not match:
        return frozenset()
    return frozenset(
        label.strip() for label in match.group(1).split(",") if label.strip()
    )


def _extract_selector_labels(selector_body: str) -> set[str]:
    """Extract explicit label matchers from a PromQL metric selector body."""
    labels: set[str] = set()
    for label_name, _operator in _PROMQL_LABEL_MATCHER_RE.findall(selector_body):
        if label_name != "__name__":
            labels.add(label_name)
    return labels


def _assert_standard_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for standard dashboards."""
    assert "run_id" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not define deprecated 'run_id' variable"
    )

    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
    )
    pipeline_query = pipeline_var.get("query", {})
    pipeline_query_text = (
        pipeline_query.get("query", "") if isinstance(pipeline_query, dict) else ""
    )
    if dashboard_path.name == "bioetl-control-plane-v1.json":
        expected_pipeline_metric = "bioetl_control_plane_manifest_writes_total"
    else:
        expected_pipeline_metric = "bioetl_records_processed_total"
    assert expected_pipeline_metric in pipeline_query_text, (
        f"Dashboard {dashboard_path.name} 'pipeline' query must use "
        f"{expected_pipeline_metric}"
    )

    run_type_var = variable_map.get("run_type")
    assert run_type_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'run_type' variable"
    )
    run_type_query = run_type_var.get("query", {})
    run_type_query_text = (
        run_type_query.get("query", "") if isinstance(run_type_query, dict) else ""
    )
    assert expected_pipeline_metric in run_type_query_text, (
        f"Dashboard {dashboard_path.name} 'run_type' query must use "
        f"{expected_pipeline_metric}"
    )
    assert "run_type" in run_type_query_text, (
        f"Dashboard {dashboard_path.name} 'run_type' query must select run_type label"
    )


def _assert_provider_health_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the provider health dashboard."""
    assert "run_id" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not define deprecated 'run_id' variable"
    )

    provider_var = variable_map.get("provider")
    assert provider_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'provider' variable"
    )
    provider_query = provider_var.get("query", {})
    provider_query_text = (
        provider_query.get("query", "") if isinstance(provider_query, dict) else ""
    )
    assert "bioetl_health_check_(success|degraded|failures)_total" in (
        provider_query_text
    ), (
        f"Dashboard {dashboard_path.name} 'provider' query must use "
        "the union of health-check outcome counters"
    )
    adapter_var = variable_map.get("adapter")
    assert adapter_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'adapter' variable for "
        "circuit-breaker metrics"
    )
    adapter_query = adapter_var.get("query", {})
    adapter_query_text = (
        adapter_query.get("query", "") if isinstance(adapter_query, dict) else ""
    )
    assert "bioetl_circuit_breaker_state" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must use "
        "circuit-breaker state metric"
    )
    assert "adapter" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must select adapter label"
    )
    assert "pipeline" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not expose misleading 'pipeline' variable"
    )


def _assert_silver_reject_explorer_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the silver reject explorer dashboard."""

    def _extract_query_url(variable: dict[str, object]) -> str:
        query = variable.get("query", {})
        if not isinstance(query, dict):
            return ""
        infinity_query = query.get("infinityQuery")
        if isinstance(infinity_query, dict):
            url = infinity_query.get("url", "")
            if isinstance(url, str):
                return url
        legacy_url = query.get("query", "")
        return legacy_url if isinstance(legacy_url, str) else ""

    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
    )
    assert pipeline_var.get("datasource") == "Prometheus", (
        f"Dashboard {dashboard_path.name} 'pipeline' must use Prometheus datasource"
    )
    pipeline_query = pipeline_var.get("query", {})
    pipeline_query_text = (
        pipeline_query.get("query", "") if isinstance(pipeline_query, dict) else ""
    )
    assert "bioetl_records_processed_total" in pipeline_query_text, (
        f"Dashboard {dashboard_path.name} 'pipeline' query must use "
        "bioetl_records_processed_total"
    )
    assert pipeline_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must disable All scope"
    )
    assert pipeline_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must be single-select"
    )

    for variable_name in ("run_type", "reason_code", "field", "run_id"):
        variable = variable_map.get(variable_name)
        assert variable is not None, (
            f"Dashboard {dashboard_path.name} must define '{variable_name}' variable"
        )
        assert variable.get("datasource") == "Quarantine Explorer", (
            f"Dashboard {dashboard_path.name} '{variable_name}' must use "
            "Quarantine Explorer datasource"
        )
        query_url = _extract_query_url(variable)
        assert "/ops/quarantine/filter-options" in query_url, (
            f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
            "/ops/quarantine/filter-options endpoint"
        )
        assert "pipeline=${pipeline:csv}" not in query_url, (
            f"Dashboard {dashboard_path.name} '{variable_name}' query must pass "
            "one concrete pipeline value"
        )

    run_id_var = variable_map["run_id"]
    assert run_id_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'run_id' must disable All scope"
    )
    assert run_id_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'run_id' must stay bounded as single-select"
    )

    payload_hash_var = variable_map.get("payload_hash")
    assert payload_hash_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'payload_hash' variable"
    )
    assert payload_hash_var.get("type") == "textbox", (
        f"Dashboard {dashboard_path.name} 'payload_hash' must be a textbox"
    )


def _emit_sample_structured_log(*, pipeline: str, provider: str) -> str:
    """Emit one JSON log line through the shipped structlog pipeline."""
    configure_logging, unified_logger_cls = _load_logging_helpers()
    configure_logging(json_format=True, force=True)
    stream = io.StringIO()
    root = logging.getLogger()
    for handler in root.handlers:
        try:
            handler.setStream(stream)
        except AttributeError:
            continue

    logger = unified_logger_cls(
        pipeline=pipeline,
        run_id="123e4567-e89b-12d3-a456-426614174000",
    )
    logger.info(
        "sample-event",
        stage="extract",
        provider=provider,
        operation="health_check",
    )
    return stream.getvalue().strip().splitlines()[-1]
