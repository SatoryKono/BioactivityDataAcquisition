"""Contracts for the shipped Pipeline Runtime Grafana dashboard."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
from tests.integration._grafana_test_support import (
    _PROMQL_METRIC_SELECTOR_RE,
    _collect_dashboard_links,
    _extract_selector_labels,
    _unknown_metrics_for_query,
    get_all_valid_metric_names,
    get_dashboard_panels,
    get_dashboard_prometheus_queries,
    get_metric_label_sets,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_DASHBOARD_PATH = Path("grafana/dashboards/bioetl-runtime.json")
_DASHBOARD_UID_RE = re.compile(r"^/d/([^\\/?]+)")
_LINK_VAR_RE = re.compile(r"[?&]var-(\w+)=")
_WINDOW_TOKEN_RE = re.compile(r"\[(?:\$__[^]]+|\d+[smhdw])\]")
_QUERY_WINDOW_FUNC_RE = re.compile(
    r"\b(?:rate|increase|count_over_time|max_over_time|histogram_quantile)\b"
)
_ALLOWED_DASHBOARD_LINK_VARS = {
    "bioetl-overview-v2": frozenset({"pipeline", "run_type"}),
    "bioetl-dq-v2": frozenset({"pipeline", "run_type", "stage"}),
    "bioetl-runtime": frozenset({"pipeline", "run_type", "stage"}),
    "bioetl-provider-health-v2": frozenset({"provider", "adapter"}),
    "bioetl-control-plane-v1": frozenset({"pipeline", "run_type"}),
}


def _dashboard() -> dict:
    return load_dashboard(_DASHBOARD_PATH)


def _extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    return match.group(1) if match is not None else None


def _extract_link_vars(url: str) -> set[str]:
    return set(_LINK_VAR_RE.findall(url))


def _runtime_data_panels() -> list[dict]:
    return [
        panel
        for panel in get_dashboard_panels(_dashboard())
        if panel.get("type") not in {"row", "text"}
    ]


def test_pipeline_runtime_dashboard_json_is_valid() -> None:
    dashboard = _dashboard()
    assert isinstance(dashboard, dict)
    assert dashboard.get("title") == "2. Runtime"


def test_pipeline_runtime_dashboard_uid_is_bioetl_runtime() -> None:
    assert _dashboard().get("uid") == "bioetl-runtime"


def test_pipeline_runtime_has_required_variables() -> None:
    variables = {
        variable.get("name")
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }
    assert variables == {"pipeline", "run_type", "stage"}


def test_pipeline_runtime_does_not_have_forensic_variables() -> None:
    variables = {
        variable.get("name")
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }
    assert "run_id" not in variables
    assert "payload_hash" not in variables
    assert "record_id" not in variables


def test_pipeline_runtime_panels_have_units() -> None:
    missing_units = []
    for panel in _runtime_data_panels():
        unit = panel.get("fieldConfig", {}).get("defaults", {}).get("unit")
        if not isinstance(unit, str) or not unit.strip():
            missing_units.append(panel.get("title", "<untitled>"))
    assert not missing_units, (
        "Runtime dashboard panels missing explicit units:\n" + "\n".join(missing_units)
    )


def test_pipeline_runtime_count_panels_have_window_in_title_or_description() -> None:
    titles = {
        "Runtime Blockers",
        "Failed Runs",
        "No-Records Runs",
        "Runtime Error Rate",
        "Worst Stage Lag",
        "Memory Pressure Active",
        "Pipeline Alert Conditions",
        "DQ Alert Conditions",
        "Control-plane Alert Conditions",
        "GLOBAL Provider Alert Conditions",
        "Freshness Alert Conditions",
        "Warnings",
        "Unstructured Logs",
        "Top Warning Events",
        "Errors by Stage / Error Code / Range",
        "Records by Stage / Run Type / Range",
        "Shutdown Initiated by Reason / Interval",
        "Shutdown Completed by Reason / Interval",
    }
    offenders = []
    for panel in _runtime_data_panels():
        title = panel.get("title", "")
        if title not in titles:
            continue
        description = panel.get("description", "")
        windowed = any(
            token in f"{title} {description}"
            for token in ("15m", "30m", "1h", "24h", "Range", "Interval", "range")
        )
        if not windowed:
            offenders.append(title)
    assert not offenders, (
        "Runtime count panels missing window semantics in title/description:\n"
        + "\n".join(offenders)
    )


def test_pipeline_runtime_rate_queries_have_explicit_window() -> None:
    offenders = []
    for panel in _runtime_data_panels():
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            if not isinstance(expr, str) or not _QUERY_WINDOW_FUNC_RE.search(expr):
                continue
            if not _WINDOW_TOKEN_RE.search(expr):
                offenders.append(f"{panel.get('title')}: {expr}")
    assert not offenders, (
        "Runtime dashboard windowed queries missing explicit range selectors:\n"
        + "\n".join(offenders)
    )


def test_pipeline_runtime_latency_panels_have_p50_p95_p99() -> None:
    panels = {
        panel.get("title"): panel
        for panel in _runtime_data_panels()
        if panel.get("title")
    }
    for title in (
        "Pipeline Phase Duration p50/p95/p99",
        "Pipeline Duration p50/p95/p99",
    ):
        panel = panels.get(title)
        assert panel is not None, f"Missing latency panel: {title}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any("histogram_quantile(0.50" in expr for expr in expressions)
        assert any("histogram_quantile(0.95" in expr for expr in expressions)
        assert any("histogram_quantile(0.99" in expr for expr in expressions)


def test_pipeline_runtime_links_are_target_scoped() -> None:
    for link in _collect_dashboard_links(_dashboard()):
        url = link.get("url", "")
        if not isinstance(url, str) or not url.startswith("/d/"):
            continue
        target_uid = _extract_dashboard_uid(url)
        assert target_uid is not None, f"Could not parse dashboard UID from {url}"
        allowed_vars = _ALLOWED_DASHBOARD_LINK_VARS[target_uid]
        assert _extract_link_vars(url) <= allowed_vars, (
            f"Runtime dashboard link to {target_uid} leaks variables via {url}"
        )


def test_pipeline_runtime_links_do_not_use_blanket_include_vars() -> None:
    offenders = [
        link.get("title", "<untitled>")
        for link in _collect_dashboard_links(_dashboard())
        if link.get("includeVars") is True
    ]
    assert not offenders, (
        "Runtime dashboard links must not use blanket includeVars=true:\n"
        + "\n".join(offenders)
    )


def test_pipeline_runtime_metric_names_exist() -> None:
    valid_metrics = get_all_valid_metric_names()
    errors = []
    for panel in _runtime_data_panels():
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            if not isinstance(expr, str) or not expr:
                continue
            for metric in _unknown_metrics_for_query(expr, valid_metrics):
                errors.append(f"{panel.get('title')}: {metric}")
    assert not errors, "Runtime dashboard uses unknown metrics:\n" + "\n".join(errors)


def test_pipeline_runtime_metric_label_schemas_exist() -> None:
    label_sets = get_metric_label_sets()
    errors = []
    for query in get_dashboard_prometheus_queries(_dashboard()):
        for metric_name, selector_body in _PROMQL_METRIC_SELECTOR_RE.findall(query):
            expected_labels = label_sets.get(metric_name)
            if expected_labels is None:
                continue
            selector_labels = _extract_selector_labels(selector_body)
            unknown_labels = sorted(selector_labels - expected_labels)
            if unknown_labels:
                errors.append(
                    f"{metric_name} selector_labels={unknown_labels} "
                    f"allowed={sorted(expected_labels)} query={query}"
                )
    assert not errors, (
        "Runtime dashboard uses selectors with nonexistent labels:\n"
        + "\n".join(errors)
    )


def test_pipeline_runtime_recording_rules_exist() -> None:
    missing = []
    for panel in _runtime_data_panels():
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            if not isinstance(expr, str):
                continue
            for token in re.findall(
                r"\b(bioetl_runtime_alert_condition_[a-z0-9_]+)\b", expr
            ):
                if token not in get_all_valid_metric_names():
                    missing.append(f"{panel.get('title')}: {token}")
    assert not missing, (
        "Runtime dashboard references missing recording rules:\n" + "\n".join(missing)
    )


def test_runtime_blockers_panel_does_not_filter_by_stage() -> None:
    """Runtime Blockers aggregate must include all stages (incl. output/gold).

    The stage variable filter was the root cause of L0/L2 desync: Overview
    saw output backlog but Runtime Blockers filtered it out via stage=~"$stage".
    """
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    blockers_panel = panels.get("Runtime Blockers")
    assert blockers_panel is not None, "Runtime Blockers panel is missing"
    expr = blockers_panel["targets"][0]["expr"]
    backlog_term = "bioetl_runtime_alert_condition_stage_backlog_active_15m"
    lag_term = "bioetl_runtime_alert_condition_stage_lag_high_15m"
    for term in (backlog_term, lag_term):
        start = expr.find(term)
        assert start != -1, f"Missing {term} in Runtime Blockers query"
        brace_end = expr.find(")", start)
        selector = expr[start:brace_end]
        assert 'stage=~"$stage"' not in selector, (
            f"{term} in Runtime Blockers must not filter by stage variable"
        )


def test_runtime_blockers_includes_gold_write_missing() -> None:
    """Runtime Blockers must include gold_write_missing recording rule."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    blockers_panel = panels.get("Runtime Blockers")
    assert blockers_panel is not None
    expr = blockers_panel["targets"][0]["expr"]
    assert "bioetl_runtime_alert_condition_gold_write_missing_15m" in expr, (
        "Runtime Blockers query must reference gold_write_missing recording rule"
    )


def test_runtime_blockers_includes_no_terminal_run() -> None:
    """Runtime Blockers must include no_terminal_run recording rule."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    blockers_panel = panels.get("Runtime Blockers")
    assert blockers_panel is not None
    expr = blockers_panel["targets"][0]["expr"]
    assert "bioetl_runtime_alert_condition_no_terminal_run_30m" in expr, (
        "Runtime Blockers query must reference no_terminal_run recording rule"
    )


def test_active_runtime_blocker_detail_panel_exists() -> None:
    """Active Runtime Blocker Detail table panel must be present."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    detail_panel = panels.get("Active Runtime Blocker Detail")
    assert detail_panel is not None, "Active Runtime Blocker Detail panel is missing"
    assert detail_panel["type"] == "table"
    targets = detail_panel.get("targets", [])
    blocker_names = set()
    for t in targets:
        expr = t.get("expr", "")
        if "label_replace" in expr:
            for match in re.findall(r'"blocker",\s*"([^"]+)"', expr):
                blocker_names.add(match)
    expected = {
        "preflight_failed",
        "runs_failed",
        "stage_backlog_active",
        "stage_lag_high",
        "gold_write_missing",
        "no_terminal_run",
        "flow_invariant_violated",
    }
    assert expected <= blocker_names, (
        f"Active Runtime Blocker Detail missing blockers: {expected - blocker_names}"
    )


def test_stage_expectedness_panel_exists() -> None:
    """Stage Expectedness panel must be present on Runtime dashboard."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    panel = panels.get("Stage Expectedness")
    assert panel is not None, "Stage Expectedness panel is missing"
    assert panel["type"] == "table"
    expr_texts = [t.get("expr", "") for t in panel.get("targets", [])]
    assert any("bioetl_pipeline_stage_expected" in e for e in expr_texts), (
        "Stage Expectedness panel must query bioetl_pipeline_stage_expected"
    )


def test_pipeline_duration_has_explicit_no_value_message() -> None:
    """Pipeline Duration panel must show explicit message instead of bare No data."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    panel = panels.get("Pipeline Duration p50/p95/p99")
    assert panel is not None
    no_value = panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
    assert "terminal" in no_value.lower() or "samples" in no_value.lower(), (
        f"Pipeline Duration noValue must explain missing terminal metric, got: {no_value!r}"
    )


def test_runtime_row_sequence_is_fixed_detect_localize_escalate() -> None:
    """Runtime row lanes must keep canonical Detect -> Localize -> Escalate order."""
    row_panels = [
        panel for panel in _dashboard().get("panels", []) if panel.get("type") == "row"
    ]
    row_pairs = [(panel.get("id"), panel.get("title")) for panel in row_panels]
    assert row_pairs[:3] == [
        (252, "Detect (collapsed)"),
        (253, "Localize (collapsed)"),
        (254, "Escalate (collapsed)"),
    ], f"Runtime row order/title drifted: {row_pairs}"
