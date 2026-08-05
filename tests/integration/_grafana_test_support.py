# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
_PROMETHEUS_RULE_FILES = tuple(Path("grafana/prometheus-rules").glob("*.yml"))

# DUX4-01 optional Approach A title prefix (ASCII). Titles may omit it today
# (Approach B); helpers keep contracts prefix-tolerant when prefixes appear.
SCOPE_TITLE_PREFIX_RE = re.compile(
    r"^\[(NOW|RANGE|RUN|WORKFLOW|GLOBAL)/(HEALTH|EXEC|EVIDENCE|IMPACT|APPLICABILITY)\]\s+"
)

__all__ = [
    "SCOPE_TITLE_PREFIX_RE",
    "_PROMQL_METRIC_SELECTOR_RE",
    "_assert_operator_context_shell_contract",
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
    "get_dashboard_navigation_links",
    "get_dashboard_panels",
    "get_dashboard_prometheus_queries",
    "get_metric_label_sets",
    "get_panel_expressions",
    "get_row_child_panels",
    "index_panels_by_base_title",
    "load_dashboard",
    "panel_base_title",
    "require_dashboard_navigation_links",
    "strip_scope_title_prefix",
]


def strip_scope_title_prefix(title: str) -> str:
    """Remove optional DUX4 ``[SCOPE/FAMILY] `` prefix from a panel title."""
    return SCOPE_TITLE_PREFIX_RE.sub("", title)


def panel_base_title(panel: dict[str, Any]) -> str:
    """Return panel title without optional scope prefix."""
    return strip_scope_title_prefix(str(panel.get("title") or ""))


def index_panels_by_base_title(
    panels: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map base titles to panels (last wins on duplicates)."""
    return {panel_base_title(panel): panel for panel in panels if panel.get("title")}


def _add_metric_name_suffixes(
    all_valid_names: set[str], *, base_name: str, class_name: str
) -> None:
    """Register base metric name plus Prometheus type suffixes."""
    all_valid_names.add(base_name)
    all_valid_names.add(f"{base_name}_created")
    if "Histogram" in class_name or "Summary" in class_name:
        all_valid_names.update(
            {
                f"{base_name}_bucket",
                f"{base_name}_sum",
                f"{base_name}_count",
            }
        )
        return
    if "Counter" in class_name:
        all_valid_names.add(f"{base_name}_total")


def _register_runtime_metric_names(all_valid_names: set[str]) -> None:
    from bioetl.infrastructure.observability import metrics

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if not hasattr(item, "_name"):
            continue
        _add_metric_name_suffixes(
            all_valid_names,
            base_name=item._name,
            class_name=type(item).__name__,
        )


def _register_group_recording_rule_names(
    all_valid_names: set[str], group: dict[str, Any]
) -> None:
    for rule in group.get("rules", []):
        record_name = rule.get("record")
        if isinstance(record_name, str):
            all_valid_names.add(record_name)


def _register_recording_rule_metric_names(all_valid_names: set[str]) -> None:
    for rules_path in _PROMETHEUS_RULE_FILES:
        rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        for group in rules_payload.get("groups", []):
            _register_group_recording_rule_names(all_valid_names, group)


@cache
def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for histograms."""
    all_valid_names: set[str] = {"ALERTS"}
    _register_runtime_metric_names(all_valid_names)
    _register_recording_rule_metric_names(all_valid_names)
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
        _register_histogram_label_set(
            label_sets, name=name, label_names=metric._labelnames
        )


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


def _static_labels_from_rule(rule: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        str(label_name)
        for label_name in rule.get("labels", {})
        if isinstance(label_name, str)
    )


def _apply_recording_rule_label_set(
    label_sets: dict[str, frozenset[str]], rule: dict[str, Any]
) -> None:
    record_name = rule.get("record")
    expr = rule.get("expr")
    if not isinstance(record_name, str) or not isinstance(expr, str):
        return
    label_sets[record_name] = (
        label_sets.get(record_name, frozenset())
        | _recording_rule_labels(expr, label_sets)
        | _static_labels_from_rule(rule)
    )


def _register_recording_rule_label_sets_from_file(
    label_sets: dict[str, frozenset[str]], rules_path: Path
) -> None:
    rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    for group in rules_payload.get("groups", []):
        for rule in group.get("rules", []):
            _apply_recording_rule_label_set(label_sets, rule)


def _register_recording_rule_label_sets(
    label_sets: dict[str, frozenset[str]],
) -> None:
    for rules_path in _PROMETHEUS_RULE_FILES:
        _register_recording_rule_label_sets_from_file(label_sets, rules_path)


@cache
def get_metric_label_sets() -> dict[str, frozenset[str]]:
    """Return the effective label set for shipped metrics and recording rules."""
    label_sets: dict[str, frozenset[str]] = {
        "ALERTS": frozenset({"alertname", "alertstate", "severity"}),
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


def get_row_child_panels(dashboard: dict, row_title: str) -> list[dict]:
    """Return panels that belong to a row in nested or expanded Grafana JSON."""
    panels = list(dashboard.get("panels", []))
    for index, panel in enumerate(panels):
        if panel.get("type") != "row" or panel.get("title") != row_title:
            continue
        nested = panel.get("panels")
        if isinstance(nested, list) and nested:
            return list(nested)
        children: list[dict] = []
        for candidate in panels[index + 1 :]:
            if candidate.get("type") == "row":
                break
            children.append(candidate)
        return children
    return []


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
        datasource = variable.get("datasource")
        is_prometheus = datasource == "Prometheus" or datasource == {
            "type": "prometheus",
            "uid": "prometheus",
        }
        if not is_prometheus:
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


def get_dashboard_navigation_links(dashboard: dict) -> list[dict]:
    """Collect canonical dashboard-bus links from the navigation surface.

    Fail-closed: panel ``id=1000`` must exist, ``links`` must be a list, and
    every entry must be a mapping. Callers that require a non-empty bus should
    also call :func:`require_dashboard_navigation_links`.
    """
    navigation_panels = [
        panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 1000
    ]
    assert navigation_panels, "dashboard must define navigation panel id=1000"
    assert len(navigation_panels) == 1, (
        "dashboard must define exactly one navigation panel id=1000"
    )
    panel_links = navigation_panels[0].get("links", [])
    assert isinstance(panel_links, list), (
        "navigation panel id=1000 links must be a list, "
        f"got {type(panel_links).__name__}"
    )
    links: list[dict] = []
    for index, link in enumerate(panel_links):
        assert isinstance(link, dict), (
            f"navigation panel id=1000 links[{index}] must be a mapping, "
            f"got {type(link).__name__}"
        )
        links.append(link)
    return links


def require_dashboard_navigation_links(
    dashboard: dict,
    *,
    dashboard_name: str,
) -> list[dict]:
    """Return navigation links and fail closed when the bus is empty."""
    links = get_dashboard_navigation_links(dashboard)
    assert links, (
        f"{dashboard_name} must expose a non-empty navigation link bus "
        "(panel id=1000 links[])"
    )
    return links


def _unknown_metrics_for_query(query: str, valid_metrics: set[str]) -> list[str]:
    """Return metric-like tokens that are not present in the known metric set."""
    unknown_metrics: list[str] = []
    query_without_strings = re.sub(r'"[^"]*"', '""', query)
    for metric in re.findall(r"(bioetl_[a-z0-9_]+)", query_without_strings):
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
    _assert_operator_context_shell_contract(dashboard_path, variable_map)

    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
    )
    pipeline_query = pipeline_var.get("query", {})
    pipeline_query_text = (
        pipeline_query.get("query", "") if isinstance(pipeline_query, dict) else ""
    )
    expected_pipeline_metric_by_dashboard = {
        "bioetl-control-plane-v1.json": "bioetl_control_plane_run_type_universe",
        "bioetl-runtime.json": "bioetl_runtime_pipeline_run_type_universe",
    }
    expected_pipeline_metric = expected_pipeline_metric_by_dashboard.get(
        dashboard_path.name,
        "bioetl_overview_pipeline_run_type_universe",
    )
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


def _query_text(variable: dict[str, object] | None) -> str:
    if variable is None:
        return ""
    query = variable.get("query", {})
    if isinstance(query, dict):
        return str(query.get("query", "") or "")
    return ""


def _assert_workflow_context_variable(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    workflow_var = variable_map.get("workflow")
    assert workflow_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'workflow' context"
    )
    assert "bioetl_workflow_universe" in _query_text(workflow_var), (
        f"Dashboard {dashboard_path.name} 'workflow' query must use workflow universe"
    )


def _assert_run_id_filter_options_url(query_url: str) -> None:
    assert "/ops/control-plane/filter-options" in query_url
    assert "dimension=run_id" in query_url
    assert "response_shape=list" in query_url
    assert "workflow=${workflow}" in query_url
    assert "pipeline=${pipeline}" in query_url
    assert "run_type=${run_type:csv}" in query_url


def _assert_run_id_infinity_shell(
    dashboard_path: Path, run_id_var: dict[str, object]
) -> None:
    assert run_id_var.get("type") == "query"
    assert run_id_var.get("datasource") == "BioETL Ops HTTP"
    assert run_id_var.get("includeAll") is False
    assert run_id_var.get("multi") is False
    run_id_query = run_id_var.get("query", {})
    assert isinstance(run_id_query, dict)
    assert run_id_query.get("queryType") == "infinity"
    assert run_id_query.get("refId") == "variable"
    infinity_query = run_id_query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict)
    assert infinity_query.get("format") == "table"
    assert infinity_query.get("parser") == "backend"
    assert infinity_query.get("root_selector") == "$.items"
    assert infinity_query.get("url_options", {}).get("method") == "GET"
    _assert_run_id_filter_options_url(str(infinity_query.get("url", "")))


def _assert_operator_context_shell_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert shared context selectors without allowing Prometheus run_id use."""
    _assert_workflow_context_variable(dashboard_path, variable_map)
    run_id_var = variable_map.get("run_id")
    assert run_id_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'run_id' identity context"
    )
    _assert_run_id_infinity_shell(dashboard_path, run_id_var)


def _assert_prom_datasource_object(
    dashboard_path: Path, variable_name: str, variable: dict[str, object]
) -> None:
    assert variable.get("datasource") == {
        "type": "prometheus",
        "uid": "prometheus",
    }, (
        f"Dashboard {dashboard_path.name} '{variable_name}' must use canonical "
        "Prometheus datasource object"
    )


def _assert_provider_health_pipeline_run_type(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'pipeline' context"
    )
    assert "bioetl_overview_pipeline_run_type_universe" in _query_text(pipeline_var)

    run_type_var = variable_map.get("run_type")
    assert run_type_var is not None, (
        f"Dashboard {dashboard_path.name} must define shared 'run_type' context"
    )
    assert "bioetl_overview_pipeline_run_type_universe" in _query_text(run_type_var)


def _assert_provider_health_provider_var(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    provider_var = variable_map.get("provider")
    assert provider_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'provider' variable"
    )
    _assert_prom_datasource_object(dashboard_path, "provider", provider_var)
    query_text = _query_text(provider_var)
    assert "query_result(" in query_text, (
        f"Dashboard {dashboard_path.name} 'provider' query must derive from "
        "pipeline/workflow via query_result(label_replace(...))"
    )
    assert "${pipeline}" in query_text and "${workflow}" in query_text, (
        f"Dashboard {dashboard_path.name} 'provider' derivation must read "
        "pipeline and workflow template vars"
    )
    assert provider_var.get("current", {}).get("value") == "unknown", (
        f"Dashboard {dashboard_path.name} 'provider' default must be fail-closed "
        "unknown when pipeline/workflow are unset"
    )
    assert provider_var.get("includeAll") is False
    assert provider_var.get("multi") is False


def _assert_provider_health_adapter_var(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    adapter_var = variable_map.get("adapter")
    assert adapter_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'adapter' variable for "
        "circuit-breaker metrics"
    )
    _assert_prom_datasource_object(dashboard_path, "adapter", adapter_var)
    adapter_query_text = _query_text(adapter_var)
    assert "bioetl_circuit_breaker_state" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must use "
        "circuit-breaker state metric"
    )
    assert "adapter" in adapter_query_text, (
        f"Dashboard {dashboard_path.name} 'adapter' query must select adapter label"
    )


def _assert_provider_health_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the provider health dashboard."""
    _assert_operator_context_shell_contract(dashboard_path, variable_map)
    _assert_provider_health_pipeline_run_type(dashboard_path, variable_map)
    _assert_provider_health_provider_var(dashboard_path, variable_map)
    _assert_provider_health_adapter_var(dashboard_path, variable_map)
    pipeline_context = variable_map.get("pipeline_context")
    assert pipeline_context is not None
    assert pipeline_context.get("hide") == 2


def _extract_infinity_query_url(variable: dict[str, object]) -> str:
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


_SILVER_REJECT_ROOT_SELECTORS = {
    "run_type": "$.run_types",
    "reason_code": "$.reason_codes",
    "field": "$.fields",
    "quarantine_run_id": "$.run_ids",
}


def _assert_silver_reject_pipeline_var(
    dashboard_path: Path, pipeline_var: dict[str, object]
) -> None:
    assert pipeline_var.get("datasource") == "Prometheus", (
        f"Dashboard {dashboard_path.name} 'pipeline' must use Prometheus datasource"
    )
    assert "bioetl_records_processed_total" in _query_text(pipeline_var), (
        f"Dashboard {dashboard_path.name} 'pipeline' query must use "
        "bioetl_records_processed_total"
    )
    assert pipeline_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must disable All scope"
    )
    assert pipeline_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'pipeline' must be single-select"
    )


def _assert_silver_reject_infinity_query_block(
    dashboard_path: Path,
    variable_name: str,
    query: dict[str, object],
    variable: dict[str, object],
) -> None:
    infinity_query = query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict), (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must define "
        "an infinityQuery block"
    )
    assert infinity_query.get("format") == "table", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must return "
        "a table for Grafana variable extraction"
    )
    assert infinity_query.get("parser") == "backend", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "the backend parser"
    )
    expected_root_selector = _SILVER_REJECT_ROOT_SELECTORS[variable_name]
    assert infinity_query.get("root_selector") == expected_root_selector, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must select "
        f"{expected_root_selector}"
    )
    assert infinity_query.get("url_options", {}).get("method") == "GET", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use GET"
    )
    query_url = _extract_infinity_query_url(variable)
    assert "/ops/quarantine/filter-options" in query_url, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "/ops/quarantine/filter-options endpoint"
    )
    assert "pipeline=${pipeline:csv}" not in query_url, (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must pass "
        "one concrete pipeline value"
    )
    if variable_name == "quarantine_run_id":
        assert "dimension=run_id" in query_url, (
            f"Dashboard {dashboard_path.name} 'quarantine_run_id' must keep "
            "the backend run_id dimension"
        )


def _assert_silver_reject_infinity_variable(
    dashboard_path: Path,
    variable_name: str,
    variable: dict[str, object] | None,
) -> None:
    assert variable is not None, (
        f"Dashboard {dashboard_path.name} must define '{variable_name}' variable"
    )
    assert variable.get("datasource") == "BioETL Ops HTTP", (
        f"Dashboard {dashboard_path.name} '{variable_name}' must use "
        "BioETL Ops HTTP datasource"
    )
    query = variable.get("query", {})
    assert isinstance(query, dict), (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must be a "
        "structured Infinity variable query"
    )
    assert query.get("queryType") == "infinity", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must opt "
        "into Infinity CustomVariableSupport"
    )
    assert query.get("refId") == "variable", (
        f"Dashboard {dashboard_path.name} '{variable_name}' query must use "
        "the Infinity variable refId"
    )
    _assert_silver_reject_infinity_query_block(
        dashboard_path, variable_name, query, variable
    )


def _assert_silver_reject_explorer_variable_contract(
    dashboard_path: Path, variable_map: dict[str, dict[str, object]]
) -> None:
    """Assert the variable contract for the silver reject explorer dashboard."""
    pipeline_var = variable_map.get("pipeline")
    assert pipeline_var is not None, (
        f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
    )
    _assert_silver_reject_pipeline_var(dashboard_path, pipeline_var)

    assert "workflow" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not own shared 'workflow' context"
    )

    for variable_name in ("run_type", "reason_code", "field", "quarantine_run_id"):
        _assert_silver_reject_infinity_variable(
            dashboard_path, variable_name, variable_map.get(variable_name)
        )

    quarantine_run_id_var = variable_map["quarantine_run_id"]
    assert quarantine_run_id_var.get("includeAll") is False, (
        f"Dashboard {dashboard_path.name} 'quarantine_run_id' must disable All scope"
    )
    assert quarantine_run_id_var.get("multi") is False, (
        f"Dashboard {dashboard_path.name} 'quarantine_run_id' must stay bounded as single-select"
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
