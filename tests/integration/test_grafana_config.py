"""Integration tests for Grafana dashboard configurations and observability contracts."""

from collections import Counter
import json
from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import (
    _PROMQL_METRIC_SELECTOR_RE,
    _assert_provider_health_variable_contract,
    _assert_silver_reject_explorer_variable_contract,
    _assert_standard_variable_contract,
    _extract_selector_labels,
    _unknown_metrics_for_query,
    get_all_valid_metric_names,
    get_dashboard_files,
    get_dashboard_panels,
    get_dashboard_prometheus_queries,
    get_metric_label_sets,
    get_panel_expressions,
    load_dashboard,
)


pytestmark = pytest.mark.integration

RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
GRAFANA_DASHBOARD_PROVISIONING_PATH = Path(
    "grafana/provisioning/dashboards/bioetl.yaml"
)
GRAFANA_README_PATH = Path("grafana/README.md")
_BIOETL_METRIC_TOKEN_RE = re.compile(r"\b(bioetl_[a-z0-9_]+)\b")


def _load_recording_rule_names() -> set[str]:
    payload = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return {
        record_name
        for group in payload.get("groups", [])
        for rule in group.get("rules", [])
        if isinstance(record_name := rule.get("record"), str)
    }


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_is_valid_json(dashboard_path):
    """L1: Verify that the dashboard file is a valid JSON."""
    data = load_dashboard(dashboard_path)
    assert isinstance(data, dict)
    assert "title" in data


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_metrics_contract(dashboard_path):
    """L3: Verify that all metrics used in PromQL exist in the codebase."""
    valid_metrics = get_all_valid_metric_names()
    dashboard = load_dashboard(dashboard_path)
    panels = get_dashboard_panels(dashboard)

    errors = []
    for panel in panels:
        targets = panel.get("targets", [])
        for target in targets:
            query = target.get("expr", "")
            if not query:
                continue

            for metric in _unknown_metrics_for_query(query, valid_metrics):
                errors.append(
                    f"Panel '{panel.get('title')}' uses unknown metric: {metric}"
                )

    assert not errors, f"Metric mismatch in {dashboard_path.name}:\n" + "\n".join(
        errors
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_queries_use_real_metric_label_schemas(dashboard_path: Path) -> None:
    """PromQL selectors must only use labels that exist on the referenced metric."""
    dashboard = load_dashboard(dashboard_path)
    label_sets = get_metric_label_sets()
    errors: list[str] = []

    for query in get_dashboard_prometheus_queries(dashboard):
        for metric_name, selector_body in _PROMQL_METRIC_SELECTOR_RE.findall(query):
            expected_labels = label_sets.get(metric_name)
            if expected_labels is None:
                continue
            selector_labels = _extract_selector_labels(selector_body)
            unknown_labels = sorted(selector_labels - expected_labels)
            if unknown_labels:
                errors.append(
                    f"metric={metric_name} selector_labels={unknown_labels} "
                    f"allowed={sorted(expected_labels)} query={query}"
                )

    assert not errors, (
        f"Dashboard {dashboard_path.name} uses selectors with nonexistent labels:\n"
        + "\n".join(errors)
    )


def test_dashboard_recording_rule_queries_are_backed_by_shipped_rules_config() -> None:
    """Dashboard recording-rule references must resolve to shipped rule records."""
    recording_rules = _load_recording_rule_names()
    used_recording_rules: set[str] = set()
    errors: list[str] = []

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for query in get_dashboard_prometheus_queries(dashboard):
            for token in _BIOETL_METRIC_TOKEN_RE.findall(query):
                if token in recording_rules:
                    used_recording_rules.add(token)
                    continue
                if token.startswith("bioetl_runtime_alert_condition_"):
                    errors.append(
                        f"{dashboard_path.name} references missing recording rule "
                        f"{token}: {query}"
                    )

    assert not errors, "Dashboard recording-rule drift:\n" + "\n".join(errors)
    assert used_recording_rules, (
        "At least one shipped dashboard must consume recording rules; otherwise "
        "runtime dashboard parity checks are no longer exercising the rule pack."
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_has_required_variables(dashboard_path):
    """Check dashboard variables match the current contract."""
    expected_vars_by_dashboard = {
        "bioetl-overview-v2.json": {"pipeline", "run_type"},
        "bioetl-dq-v2.json": {"pipeline", "run_type", "stage"},
        "bioetl-runtime.json": {"pipeline", "run_type", "stage"},
        "bioetl-provider-health-v2.json": {"provider", "adapter"},
        "bioetl-control-plane-v1.json": {"pipeline", "run_type"},
        "bioetl-workflow-overview.json": {"workflow", "status"},
        "bioetl-silver-reject-explorer.json": {
            "pipeline",
            "run_type",
            "reason_code",
            "field",
            "run_id",
            "payload_hash",
        },
    }
    dashboard = load_dashboard(dashboard_path)
    variables = {
        v.get("name")
        for v in dashboard.get("templating", {}).get("list", [])
        if v.get("name")
    }
    expected_vars = expected_vars_by_dashboard.get(dashboard_path.name)

    assert expected_vars is not None, (
        f"Unexpected dashboard file: {dashboard_path.name}"
    )
    assert variables == expected_vars, (
        f"Dashboard {dashboard_path.name} variables mismatch. "
        f"Expected: {sorted(expected_vars)}, got: {sorted(variables)}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_no_duplicate_variable_names(dashboard_path):
    """Ensure variable names in dashboard templating list are unique."""
    dashboard = load_dashboard(dashboard_path)
    names = [
        var.get("name")
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    ]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    assert not duplicates, (
        f"Dashboard {dashboard_path.name} has duplicate variables: {duplicates}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_variable_query_sources(dashboard_path):
    """Ensure templating variables use the intended metric sources."""
    dashboard = load_dashboard(dashboard_path)
    variable_map = {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }

    if dashboard_path.name == "bioetl-silver-reject-explorer.json":
        _assert_silver_reject_explorer_variable_contract(dashboard_path, variable_map)
        return

    if dashboard_path.name == "bioetl-workflow-overview.json":
        workflow_query = variable_map["workflow"].get("query", {})
        status_query = variable_map["status"].get("query", {})
        assert isinstance(workflow_query, dict)
        assert isinstance(status_query, dict)
        assert "bioetl_workflow_runs_total" in workflow_query.get("query", "")
        assert "bioetl_workflow_runs_total" in status_query.get("query", "")
        return

    if dashboard_path.name == "bioetl-provider-health-v2.json":
        _assert_provider_health_variable_contract(dashboard_path, variable_map)
    else:
        _assert_standard_variable_contract(dashboard_path, variable_map)


def test_production_dashboard_provisioning_disables_ui_updates() -> None:
    """Production dashboards must remain dashboard-as-code, not mutable UI state."""
    payload = yaml.safe_load(
        GRAFANA_DASHBOARD_PROVISIONING_PATH.read_text(encoding="utf-8")
    )
    providers = payload.get("providers", []) if isinstance(payload, dict) else []
    bioetl_provider = next(
        (
            provider
            for provider in providers
            if isinstance(provider, dict) and provider.get("name") == "BioETL"
        ),
        None,
    )
    assert bioetl_provider is not None, "BioETL dashboard provider is missing"
    assert bioetl_provider.get("allowUiUpdates") is False, (
        "Production BioETL dashboard provisioning must disable UI updates"
    )


def test_monitoring_readme_dashboard_inventory_matches_shipped_json() -> None:
    """README dashboard inventory must not drift from shipped dashboard JSON files."""
    dashboard_names = sorted(path.name for path in get_dashboard_files())
    readme = GRAFANA_README_PATH.read_text(encoding="utf-8")

    assert "Dashboards: 5 JSON" not in readme
    assert f"Dashboards: {len(dashboard_names)} JSON" in readme
    for dashboard_name in dashboard_names:
        assert dashboard_name.removesuffix(".json") in readme, (
            f"grafana/README.md must mention shipped dashboard {dashboard_name}"
        )


def test_summary_queries_use_zero_fallbacks() -> None:
    """Runtime/provider summary panels should show zero instead of no-data."""
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Failed Runs in Range": "or vector(0)",
            "Manifest / Ledger Failures": "or vector(0)",
            "Checkpoint Incompatibilities": "or vector(0)",
            "Lineage Refs Missing": "or vector(0)",
            "Silver Rejects Count + Rate": "or vector(0)",
            "DQ Hard Blockers": "or vector(0)",
            "Control-plane Blockers": "or vector(0)",
            "Workflow Status": "or vector(0)",
        },
        "bioetl-runtime.json": {
            "Runtime Blockers / 15m": "or vector(0)",
            "Failed Runs / 15m": "or vector(0)",
            "No-Records Runs / 30m": "or vector(0)",
            "Runtime Error Rate / 30m": "or vector(0)",
            "Worst Stage Lag / 15m": "or vector(0)",
            "Memory Pressure Active / 15m": "or vector(0)",
            "Records by Stage / Interval": "or vector(0)",
            "Pipeline Alert Conditions": "or vector(0)",
            "DQ Alert Conditions": "or vector(0)",
            "Control-plane Alert Conditions": "or vector(0)",
            "GLOBAL Provider Alert Conditions": "or vector(0)",
            "Freshness Alert Conditions": "or vector(0)",
            "Shutdown Initiated by Reason / Interval": "or vector(0)",
            "Shutdown Completed by Reason / Interval": "or vector(0)",
        },
        "bioetl-provider-health-v2.json": {
            "Healthy Checks": "or vector(0)",
            "Degraded Checks": "or vector(0)",
            "Provider Failure Rate": "or vector(0)",
            "Health Checks Total": "or vector(0)",
            "HTTP Errors by Method / Error Type": "or vector(0)",
            "Minimum Rate Limiter Tokens Available": "or vector(0)",
            "Circuit Breaker State (max)": "or vector(0)",
            "Circuit Breaker Trips by Provider": 'or label_replace(vector(0), "adapter",',
        },
        "bioetl-dq-v2.json": {
            "Records Quarantined": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
            "Soft Threshold Exceeded": "or vector(0)",
            "Silver Validation Failures": "or vector(0)",
            "Gold Strict Validation Failures": "or vector(0)",
        },
        "bioetl-control-plane-v1.json": {
            "Replay / Resume Blockers": "or vector(0)",
            "Manifest Write Failures": "or vector(0)",
            "Ledger Append Failures": "or vector(0)",
            "Checkpoint Incompatibilities": "or vector(0)",
            "GLOBAL Control-Plane Read Failures": "or vector(0)",
            "GLOBAL Control-Plane Read Failure Ratio": "or vector(0)",
            "Checkpoint Load Failures": "or vector(0)",
            "Checkpoint Save Failures": "or vector(0)",
            "GLOBAL Checkpoint Operator Failures": "or vector(0)",
            "Replay Not Reconstructable": "or vector(0)",
            "Replay Drift": "or vector(0)",
            "Replay Lag Seconds": "or vector(0)",
            "Audit Write Outcomes": "or vector(0)",
            "Audit Query Outcomes": "or vector(0)",
            "Lineage Fragment Persistence Failures": "or vector(0)",
            "Lineage Refs Missing": "or vector(0)",
        },
    }

    for dashboard_name, panel_expectations in expected_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_snippet in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions, (
                f"Dashboard {dashboard_name} panel {panel_title!r} has no expressions"
            )
            assert any(expected_snippet in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must include "
                f"{expected_snippet!r} to render zero instead of no-data"
            )


def test_latency_p95_panels_preserve_no_data_state() -> None:
    """Latency p95 panels must not collapse missing samples into zero."""
    expected_latency_panels = {
        "bioetl-runtime.json": {
            "Pipeline Phase Duration p50/p95/p99",
            "Pipeline Duration p50/p95/p99",
        },
        "bioetl-provider-health-v2.json": {
            "Health Check Latency by Provider (p95)",
            "Provider Health Check Latency (p95) - $provider",
            "Adapter Request Latency by Endpoint (p95)",
            "Rate Limiter Wait by Provider (p95)",
        },
        "bioetl-dq-v2.json": {"DQ Check Duration (p95)"},
        "bioetl-control-plane-v1.json": {
            "GLOBAL Control-Plane Read Latency p50/p95/p99",
            "Checkpoint Save Latency p50/p95/p99",
            "GLOBAL Checkpoint Operator Latency p50/p95/p99",
            "Audit Write Latency p50/p95/p99",
            "Audit Query Latency p50/p95/p99",
        },
    }

    for dashboard_name, panel_titles in expected_latency_panels.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions, (
                f"Dashboard {dashboard_name} panel {panel_title!r} has no expressions"
            )
            assert any("histogram_quantile(0.95" in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must stay histogram-backed"
            )
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must preserve "
                "no-data instead of rendering zero latency"
            )


def test_count_like_summary_panels_use_rounding_or_boolean_conditions() -> None:
    """Count-like summary panels should avoid fractional event semantics."""
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Failed Runs in Range": "round(",
            "Manifest / Ledger Failures": "round(",
            "Checkpoint Incompatibilities": "round(",
            "Lineage Refs Missing": "round(",
            "Silver Rejects Count + Rate": "round(",
            "DQ Hard Blockers": "round(",
            "Control-plane Blockers": "round(",
            "Global Provider Degradation": "round(",
            "Workflow Status": "round(",
        },
        "bioetl-provider-health-v2.json": {
            "Healthy Checks": "round(",
            "Degraded Checks": "round(",
            "Health Checks Total": "round(",
        },
        "bioetl-dq-v2.json": {
            "Records Quarantined": "round(",
            "Silver Filter Rejects": "round(",
            "Soft Threshold Exceeded": "round(",
            "Silver Validation Failures": "round(",
            "Lineage Refs Missing": "round(",
        },
        "bioetl-runtime.json": {
            "Pipeline Alert Conditions": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
            "DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Control-plane Alert Conditions": "bioetl_runtime_alert_condition_manifest_write_failed_15m",
            "GLOBAL Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
            "Shutdown Initiated by Reason / Interval": "round(",
            "Shutdown Completed by Reason / Interval": "round(",
        },
    }

    for dashboard_name, panel_expectations in expected_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_snippet in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(expected_snippet in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must include "
                f"{expected_snippet!r} for stable count semantics"
            )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Data Quality Score (Volume-weighted)"),
    ],
)
def test_dq_score_uses_validation_metric(dashboard_file, panel_title):
    """Ensure DQ score panels use the canonical DQ validation metric."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use bioetl_dq_validation_score"
    )
    assert any("bioetl_dq_validation_record_count" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use "
        "bioetl_dq_validation_record_count for volume-aware weighting"
    )
    assert any("or vector(0)" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must stay zero-safe"
    )


def test_worst_entity_dq_score_preserves_no_data_state() -> None:
    """Worst-score gauges must not collapse missing DQ samples into score zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Worst-Entity DQ Score"
        ),
        None,
    )
    assert panel is not None, "Panel 'Worst-Entity DQ Score' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Worst-Entity DQ Score must preserve no-data rather than rendering score 0"
    )


def test_dashboards_do_not_use_prometheus_created_timestamps() -> None:
    """Operator dashboards must not expose Prometheus client bookkeeping timestamps."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        expressions = get_panel_expressions(dashboard)
        assert all("_created" not in expr for expr in expressions), (
            f"Dashboard {dashboard_path.name} must not use Prometheus *_created series"
        )


def test_selected_range_kpis_do_not_use_raw_counters() -> None:
    """Selected-range KPI panels must use windowed counter semantics."""
    allowed_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Processing Volume by Stage": ("increase(", "last_over_time("),
            "Pipeline Run Outcomes": ("increase(",),
            "Flow Balance": ("increase(",),
        },
        "bioetl-dq-v2.json": {
            "Data Flow in Range: Bronze -> Silver -> Gold": (
                "increase(",
                "last_over_time(",
            ),
            "Source Records in Range (Bronze)": ("increase(", "last_over_time("),
            "Clean Records in Range (Gold)": ("increase(", "last_over_time("),
        },
        "bioetl-runtime.json": {
            "Errors by Stage / Error Code / Range": ("increase(",),
            "Records by Stage / Run Type / Range": ("increase(",),
            "Shutdown Initiated by Reason / Interval": ("increase(",),
            "Shutdown Completed by Reason / Interval": ("increase(",),
        },
    }

    for dashboard_name, panel_expectations in allowed_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, allowed_snippets in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(
                any(snippet in expr for snippet in allowed_snippets)
                for expr in expressions
            ), (
                f"Panel {panel_title!r} in {dashboard_name} must use "
                f"one of {allowed_snippets!r} rather than raw counter values"
            )
            assert all("last_over_time(" not in expr for expr in expressions), (
                f"Panel {panel_title!r} in {dashboard_name} must not use "
                "last_over_time() for counter-range KPIs"
            )


def test_dq_dashboard_contains_core_dq_metrics():
    """Ensure DQ dashboard visualizes key DQ metrics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_dq_validation_score",
        "bioetl_dq_validation_record_count",
        "bioetl_dq_records_quarantined_total",
        "bioetl_dq_anomaly_detected",
        "bioetl_dq_check_duration_ms_bucket",
        "bioetl_dq_soft_threshold_exceeded",
        "bioetl_data_freshness_seconds",
        "bioetl_silver_validation_failures_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"DQ dashboard missing metrics: {missing}"


def test_dq_freshness_panel_uses_age_from_timestamp_metric() -> None:
    """Freshness lag must show the stalest entity, not the freshest timestamp."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Worst Data Freshness Lag (seconds)"
        ),
        None,
    )
    assert panel is not None, "Freshness lag panel not found in bioetl-dq-v2.json"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any(
        "max(clamp_min(time() - bioetl_data_freshness_seconds" in expr
        for expr in expressions
    ), "Freshness panel must derive worst lag from the freshness timestamp metric"
    assert all(
        "time() - max(bioetl_data_freshness_seconds" not in expr for expr in expressions
    ), "Freshness lag must not collapse scope to the freshest entity"


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Latest Successful Data Timestamp"),
    ],
)
def test_latest_timestamp_panels_are_explicitly_success_timestamp_panels(
    dashboard_file: str, panel_title: str
) -> None:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel {panel_title!r} not found in {dashboard_file}"
    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("max(bioetl_data_freshness_seconds" in expr for expr in expressions)
    assert any("* 1000" in expr for expr in expressions)


def test_overview_dashboard_contains_control_plane_and_lineage_metrics():
    """Ensure overview dashboard keeps summary control-plane and lineage signals."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


def test_overview_dashboard_has_l0_primary_question() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    description = dashboard.get("description", "")
    scope_panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "L0 Overview Scope"
        ),
        None,
    )
    assert scope_panel is not None
    content = scope_panel.get("options", {}).get("content", "")

    expected_question = (
        "what is currently broken or degraded in BioETL, and where should the "
        "operator drill down first"
    )
    assert dashboard.get("title") == "1. BioETL Overview"
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "L0 Overview" in description
    assert expected_question.lower() in (description + content).lower()
    assert "sre-data-platform" in description + content


def test_overview_answer_row_has_max_seven_panels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    answer_panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("gridPos", {}).get("y") == 4
    ]
    answer_titles = {panel.get("title") for panel in answer_panels}

    assert 3 <= len(answer_panels) <= 7
    assert answer_titles == {
        "System Status",
        "Next Action",
        "Failed Runs in Range",
        "Worst Backlog Stage",
        "Worst Lag Stage",
        "Flow Balance",
    }


def test_overview_has_system_status_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("System Status")

    assert panel is not None
    assert panel.get("type") == "stat"
    mapping_text = json.dumps(
        panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    )
    for expected_status in ("OK", "DEGRADED", "BROKEN", "UNKNOWN"):
        assert expected_status in mapping_text

    expr = "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    for recording_rule in (
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m",
        "bioetl_runtime_alert_condition_stage_lag_high_15m",
        "bioetl_runtime_alert_condition_gold_write_missing_15m",
    ):
        assert recording_rule in expr, (
            f"System Status must use recording rule {recording_rule}"
        )
    for metric_name in (
        "bioetl_dq_validation_failures_total",
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
    ):
        assert metric_name in expr
    assert 'severity="hard_fail"' in expr
    assert "[$__range]" in expr
    assert "or vector(0)" in expr


def test_overview_has_next_action_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Next Action"
        ),
        None,
    )

    assert panel is not None
    assert panel.get("type") == "stat"
    serialized_panel = json.dumps(panel)
    for expected_target in (
        "Open 2. Runtime",
        "Open 4. Data Quality",
        "Open 3. Provider Health",
        "Open Control Plane v1",
        "Open 6. Workflow Overview",
    ):
        assert expected_target in serialized_panel
    assert "Runtime > CP > DQ > Provider > Workflow" in serialized_panel


def test_overview_does_not_render_yield_green_without_denominator() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    assert "Overall Yield" not in panels
    panel = panels.get("Flow Balance")
    assert panel is not None
    assert panel.get("type") == "table"
    assert "Bronze input is zero or missing" in panel.get("description", "")

    expr = "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    for expected_snippet in (
        'stage="bronze"',
        'stage="gold"',
        'stage="filtered_out"',
        "bioetl_dq_records_quarantined_total",
        "clamp_min(",
        "[$__range]",
    ):
        assert expected_snippet in expr


def test_overview_backlog_and_lag_panels_expose_stage() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expectations = {
        "Worst Backlog Stage": "bioetl_stage_backlog_records",
        "Worst Lag Stage": "bioetl_stage_lag_seconds",
    }
    for panel_title, metric_name in expectations.items():
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("type") == "table"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert metric_name in expr
        assert "topk(1" in expr
        assert "by (stage)" in expr
        assert "[$__range]" in expr


def test_overview_handoff_cards_show_status_and_reason() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected_status_cards = {
        "Runtime Status": "/d/bioetl-runtime/bioetl-runtime",
        "Data Quality Status": "/d/bioetl-dq-v2",
        "Control Plane Status": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
        "Provider Status": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
        "Workflow Status": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
    }
    for panel_title, expected_url in expected_status_cards.items():
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("type") == "stat"
        serialized_panel = json.dumps(panel)
        for expected_status in ("OK", "DEGRADED", "BROKEN", "UNKNOWN"):
            assert expected_status in serialized_panel
        assert "Reason:" in serialized_panel
        assert "Next:" in serialized_panel
        assert expected_url in serialized_panel


def test_overview_no_duplicate_green_zero_cards() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    titles = {
        panel.get("title")
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    removed_or_merged_titles = {
        "Overall Yield",
        "Active Stage Backlog",
        "Worst Stage Lag",
        "DQ Blocking",
        "Control Plane Unsafe",
        "Provider Degraded",
        "Runtime Handoff",
        "Data Quality Handoff",
        "Control Plane Handoff",
        "Provider Handoff",
        "Workflow Handoff",
        "Silver Filter Reject Rate",
    }
    assert titles.isdisjoint(removed_or_merged_titles)


def test_overview_does_not_use_forensic_variables() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    variables = {
        var.get("name")
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }
    serialized = json.dumps(dashboard)

    assert variables == {"pipeline", "run_type"}
    for forbidden in ("run_id", "payload_hash", "execution"):
        assert forbidden not in variables
        assert f"$${forbidden}" not in serialized
        assert f"${forbidden}" not in serialized


def test_overview_no_distribution_pie_panels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = get_dashboard_panels(dashboard)
    titles = {panel.get("title") for panel in panels}
    pie_titles = {
        panel.get("title") for panel in panels if panel.get("type") == "piechart"
    }

    assert "Stage Distribution in Range" not in titles
    assert "Pipeline Distribution in Range" not in titles
    assert not pie_titles


def test_overview_summary_queries_use_range_semantics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    count_panels = {
        "System Status",
        "Next Action",
        "Failed Runs in Range",
        "Recent Activity",
        "Runtime Status",
        "Data Quality Status",
        "Control Plane Status",
        "Provider Status",
        "Workflow Status",
        "DQ Hard Blockers",
        "Control-plane Blockers",
        "Global Provider Degradation",
        "Manifest / Ledger Failures",
        "Checkpoint Incompatibilities",
        "Lineage Refs Missing",
        "Silver Rejects Count + Rate",
    }

    for panel_title in count_panels:
        panel = panels.get(panel_title)
        assert panel is not None, f"Overview dashboard missing {panel_title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions
        assert any("increase(" in expr and "[$__range]" in expr for expr in expressions)

    trend_panels = {
        "Processing Volume by Stage",
        "Pipeline Run Outcomes",
        "Stage Backlog Trend",
        "Stage Lag Trend",
    }
    for panel_title in trend_panels:
        panel = panels.get(panel_title)
        assert panel is not None, f"Overview dashboard missing {panel_title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any("[$__interval]" in expr for expr in expressions)


def test_overview_links_are_target_scoped() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    links = {link.get("title"): link for link in dashboard.get("links", [])}

    assert links
    assert all(link.get("includeVars") is False for link in links.values())
    assert "includeVars=true" not in json.dumps(links)
    for title in ("2. Runtime", "Control Plane v1", "4. Data Quality"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=$pipeline" in url
        assert "var-run_type=$run_type" in url
        assert "${__url_time_range}" in url
    for title in ("3. Provider Health", "6. Workflow Overview"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=" not in url
        assert "var-run_type=" not in url
        assert "${__url_time_range}" in url


def test_overview_contains_runtime_dq_provider_control_workflow_status_cards() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected = {
        "Runtime Status": "/d/bioetl-runtime/bioetl-runtime",
        "Data Quality Status": "/d/bioetl-dq-v2",
        "Control Plane Status": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
        "Provider Status": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
        "Workflow Status": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
    }
    for title, expected_url in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Overview dashboard missing {title!r}"
        links = panel.get("fieldConfig", {}).get("defaults", {}).get("links", [])
        assert any(expected_url in link.get("url", "") for link in links)


def test_control_plane_dashboard_has_primary_question() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    description = str(dashboard.get("description", ""))

    assert "Primary question:" in description
    assert "safely replay/resume" in description
    assert "GLOBAL read-path panels are not pipeline-scoped" in description


def test_control_plane_answer_row_has_max_seven_panels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = get_dashboard_panels(dashboard)
    answer_row = next(
        panel
        for panel in panels
        if panel.get("type") == "row"
        and panel.get("title") == "Answer: Replay / Resume Safety"
    )
    next_row_y = min(
        panel["gridPos"]["y"]
        for panel in panels
        if panel.get("type") == "row"
        and panel["gridPos"]["y"] > answer_row["gridPos"]["y"]
    )
    answer_panels = [
        panel
        for panel in panels
        if panel.get("type") != "row"
        and answer_row["gridPos"]["y"]
        < panel.get("gridPos", {}).get("y", -1)
        < next_row_y
    ]

    assert 3 <= len(answer_panels) <= 7
    assert {panel.get("title") for panel in answer_panels} == {
        "Replay / Resume Blockers",
        "Manifest Write Failures",
        "Ledger Append Failures",
        "Checkpoint Incompatibilities",
        "Replay Not Reconstructable",
        "Replay Drift",
        "Lineage Refs Missing",
    }


def test_control_plane_has_replay_resume_blockers_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Replay / Resume Blockers")

    assert panel is not None
    expr = "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    for metric in (
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_replay_reconstructability_events_total",
        "bioetl_replay_drift_events_total",
        "bioetl_lineage_refs_missing_total",
    ):
        assert metric in expr


def test_control_plane_lookup_panels_disclose_global_scope() -> None:
    """Control-plane read panels must disclose that they are global, not pipeline-scoped."""
    expectations = {
        "bioetl-control-plane-v1.json": (
            "GLOBAL Control-Plane Read Failures",
            "GLOBAL Control-Plane Read Failure Ratio",
            "GLOBAL Control-Plane Read Latency p50/p95/p99",
            "GLOBAL Control-Plane Reads by Store / Operation / Status",
            "GLOBAL Checkpoint Operator Failures",
            "GLOBAL Checkpoint Operator Latency p50/p95/p99",
        ),
    }

    for dashboard_name, panel_titles in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for title in panel_titles:
            assert title in panels, (
                f"{dashboard_name} must expose {title!r} to avoid implying pipeline scope"
            )


def test_control_plane_read_panels_do_not_filter_on_missing_pipeline_label() -> None:
    """Control-plane read panels must not filter global metrics by pipeline."""
    expectations = {
        "bioetl-control-plane-v1.json": (
            "GLOBAL Control-Plane Read Failures",
            "GLOBAL Control-Plane Read Failure Ratio",
            "GLOBAL Control-Plane Read Latency p50/p95/p99",
            "GLOBAL Control-Plane Reads by Store / Operation / Status",
        ),
    }

    forbidden_metrics = (
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
    )

    for dashboard_name, panel_titles in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} missing control-plane panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            for expr in expressions:
                if any(metric in expr for metric in forbidden_metrics):
                    assert '{pipeline=~"$pipeline"' not in expr, (
                        f"{dashboard_name} panel {panel_title!r} filters a "
                        "global control-plane metric by nonexistent pipeline label:\n"
                        f"{expr}"
                    )
                    assert '{run_type=~"$run_type"' not in expr, (
                        f"{dashboard_name} panel {panel_title!r} filters a "
                        "global control-plane metric by nonexistent run_type label:\n"
                        f"{expr}"
                    )


def test_control_plane_global_panels_are_marked_global() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    global_metric_tokens = (
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds_bucket",
        "bioetl_checkpoint_operator_operations_total",
        "bioetl_checkpoint_operator_duration_seconds_bucket",
    )

    for panel in get_dashboard_panels(dashboard):
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        if any(token in expr for expr in expressions for token in global_metric_tokens):
            assert "GLOBAL" in str(panel.get("title", ""))


def test_control_plane_latency_panels_have_p50_p95_p99() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    latency_panels = (
        "Checkpoint Save Latency p50/p95/p99",
        "GLOBAL Checkpoint Operator Latency p50/p95/p99",
        "GLOBAL Control-Plane Read Latency p50/p95/p99",
        "Audit Write Latency p50/p95/p99",
        "Audit Query Latency p50/p95/p99",
    )

    for panel_title in latency_panels:
        panel = panels.get(panel_title)
        assert panel is not None, f"Control-plane dashboard missing {panel_title!r}"
        expressions = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "histogram_quantile(0.50" in expressions
        assert "histogram_quantile(0.95" in expressions
        assert "histogram_quantile(0.99" in expressions
        assert "or vector(0)" not in expressions


def test_control_plane_no_missing_metric_promql() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expressions = "\n".join(get_panel_expressions(dashboard))

    assert "bioetl_checkpoint_age_seconds" not in expressions
    assert "bioetl_replay_duplicate_records_total" not in expressions


def test_control_plane_missing_signals_text_panel_exists() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "Known Missing Replay-Safety Signals"
        ),
        None,
    )

    assert panel is not None
    content = panel.get("options", {}).get("content", "")
    assert "checkpoint_age <= recovery window / RPO" in content
    assert "replay does not create unexplained duplicate records" in content
    assert "bioetl_checkpoint_age_seconds" in content
    assert "bioetl_replay_duplicate_records_total" in content


def test_control_plane_dashboard_links_are_scoped() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    links = {
        link.get("title"): link
        for link in dashboard.get("links", [])
        if link.get("title")
    }

    assert links
    assert all(link.get("includeVars") is False for link in links.values())
    assert "includeVars=true" not in json.dumps(links)
    for title in ("Back to Overview", "2. Runtime", "4. Data Quality"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=$pipeline" in url
        assert "var-run_type=$run_type" in url
        assert "${__url_time_range}" in url


def test_silver_validation_panels_use_explicit_pipeline_label() -> None:
    """Silver validation queries should filter on a real pipeline label, not table-name regex."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Silver Validation Failures"
        ),
        None,
    )
    assert panel is not None, "DQ dashboard missing 'Silver Validation Failures' panel"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any('{pipeline=~"$pipeline"}' in expr for expr in expressions), (
        "Silver Validation Failures must filter on the explicit pipeline label"
    )
    assert all('{table=~"$pipeline"}' not in expr for expr in expressions), (
        "Silver Validation Failures must not rely on the table-to-pipeline naming convention"
    )


def test_provider_dashboard_uses_pipeline_filters():
    """Ensure provider dashboard uses pipeline variable directly (no provider regex hack)."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    all_expressions = get_panel_expressions(dashboard)
    assert all("$provider_.*" not in expr for expr in all_expressions), (
        "Provider dashboard still uses fragile $provider_.* regex in panel queries"
    )


def test_provider_dashboard_surfaces_current_health_status_panel() -> None:
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Current Provider Health Status"
        ),
        None,
    )
    assert panel is not None, (
        "Provider Health dashboard must expose current provider health status"
    )
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_provider_health_status" in expr for expr in expressions)
    assert all('{pipeline=~"$pipeline"}' not in expr for expr in expressions), (
        "Provider health status panel must stay provider-scoped only"
    )


def test_runtime_provider_alert_conditions_do_not_filter_on_missing_pipeline_labels():
    """Provider runtime alert summaries are fleet-wide and must not filter on pipeline."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "GLOBAL Provider Alert Conditions"
        ),
        None,
    )
    assert panel is not None
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions
    assert all('{pipeline=~"$pipeline"}' not in expr for expr in expressions), (
        "GLOBAL Provider Alert Conditions must not filter provider-only recording rules by pipeline."
    )


def test_workflow_step_panels_apply_status_variable() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))
    expected = {
        "Step Outcomes by Kind": 'status=~"$status"',
        "Step Duration p95": 'status=~"$status"',
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for title, required_snippet in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Workflow dashboard missing panel {title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any(required_snippet in expr for expr in expressions), (
            f"{title!r} must apply the workflow status variable"
        )


def test_overview_dashboard_exposes_workflow_overview_handoff() -> None:
    """Overview should expose workflow dashboard in shipped operator navigation."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    workflow_link = next(
        (
            link
            for link in dashboard.get("links", [])
            if str(link.get("url", "")).startswith(
                "/d/bioetl-workflow-overview/bioetl-workflow-overview"
            )
        ),
        None,
    )
    assert workflow_link is not None, (
        "Overview dashboard must expose a Workflow Overview handoff"
    )
    assert workflow_link.get("title") == "6. Workflow Overview"
    assert workflow_link.get("includeVars") is False, (
        "Workflow Overview handoff must not pass unrelated dashboard variables"
    )
    url = str(workflow_link.get("url", ""))
    assert "${__url_time_range}" in url, (
        "Workflow Overview handoff must preserve the active Grafana time range"
    )
    assert "var-pipeline=" not in url and "var-run_type=" not in url, (
        "Workflow Overview handoff must not leak pipeline/run_type into workflow scope"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "variable_name"),
    [
        ("bioetl-runtime.json", "stage"),
        ("bioetl-dq-v2.json", "stage"),
    ],
)
def test_stage_drilldown_variable_is_available_for_runtime_and_dq_dashboards(
    dashboard_file: str, variable_name: str
) -> None:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    variable_map = {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }
    stage_var = variable_map.get(variable_name)
    assert stage_var is not None, f"{dashboard_file} must expose stage drill-down"
    query = stage_var.get("query", {})
    query_text = query.get("query", "") if isinstance(query, dict) else ""
    assert "label_values(bioetl_records_processed_total" in query_text
    assert "stage" in query_text


def test_control_plane_dashboard_uses_control_plane_native_variable_sources() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    variable_map = {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }

    pipeline_var = variable_map.get("pipeline")
    run_type_var = variable_map.get("run_type")
    assert pipeline_var is not None
    assert run_type_var is not None

    pipeline_query = pipeline_var.get("query", {})
    run_type_query = run_type_var.get("query", {})
    pipeline_query_text = (
        pipeline_query.get("query", "") if isinstance(pipeline_query, dict) else ""
    )
    run_type_query_text = (
        run_type_query.get("query", "") if isinstance(run_type_query, dict) else ""
    )

    assert "bioetl_control_plane_manifest_writes_total" in pipeline_query_text
    assert "bioetl_control_plane_manifest_writes_total" in run_type_query_text
    assert "bioetl_records_processed_total" not in pipeline_query_text
    assert "bioetl_records_processed_total" not in run_type_query_text


def test_runtime_dashboard_contains_runtime_hygiene_and_alert_condition_metrics():
    """Ensure runtime dashboard stays anchored to L2 runtime triage metrics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_pipeline_runs_total",
        "bioetl_pipeline_duration_seconds_bucket",
        "bioetl_phase_duration_seconds_bucket",
        "bioetl_errors_total",
        "bioetl_records_processed_total",
        "bioetl_memory_pressure_state",
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
        "bioetl_shutdown_initiated",
        "bioetl_shutdown_completed",
        "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
        "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m",
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_alert_condition_runtime_error_rate_high_30m",
        "bioetl_runtime_alert_condition_record_flow_invariant_violated_15m",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m",
        "bioetl_runtime_alert_condition_stage_lag_high_15m",
        "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
        "bioetl_runtime_alert_condition_dq_hard_fail_15m",
        "bioetl_runtime_alert_condition_dq_critical_anomaly_30m",
        "bioetl_runtime_alert_condition_silver_validation_failures_30m",
        "bioetl_runtime_alert_condition_manifest_write_failed_15m",
        "bioetl_runtime_alert_condition_ledger_append_failed_15m",
        "bioetl_runtime_alert_condition_checkpoint_incompatible_30m",
        "bioetl_runtime_alert_condition_replay_lag_high_15m",
        "bioetl_runtime_alert_condition_replay_drift_detected_30m",
        "bioetl_runtime_alert_condition_lineage_refs_missing_15m",
        "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
        "bioetl_runtime_alert_condition_provider_retries_exhausted_1h",
        "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m",
        "bioetl_runtime_alert_condition_provider_http_error_rate_high_15m",
        "bioetl_runtime_alert_condition_provider_rate_limiter_wait_high_30m",
        "bioetl_runtime_alert_condition_provider_rate_limiter_tokens_depleted_15m",
        "bioetl_data_freshness_seconds",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Runtime dashboard missing metrics: {missing}"

    loki_exprs = [
        target.get("expr", "")
        for panel in get_dashboard_panels(dashboard)
        for target in panel.get("targets", [])
        if panel.get("datasource") == "Loki"
    ]
    assert any("| json" in expr for expr in loki_exprs), (
        "Runtime dashboard Loki panels must parse structured JSON logs"
    )
    assert any('__error__!=""' in expr for expr in loki_exprs), (
        "Runtime dashboard must expose unstructured-log hygiene signal"
    )


def test_overview_dashboard_surfaces_backlog_and_stage_lag_metrics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_records_processed_total",
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


def test_dq_dashboard_surfaces_record_flow_invariant_metrics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_records_processed_total",
        "bioetl_record_flow_invariants_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"DQ dashboard missing metrics: {missing}"


def test_runtime_dashboard_keeps_loki_log_hygiene_in_collapsed_tracing_row() -> None:
    """Runtime should stay Prometheus-first when tracing datasources are disabled."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    row_panel = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title")
            == "Tracing-only Log Hygiene (requires optional tracing profile)"
        ),
        None,
    )
    assert row_panel is not None, (
        "Runtime dashboard must group Loki-only panels under an explicit tracing row"
    )
    assert row_panel.get("type") == "row"
    assert row_panel.get("collapsed") is True, (
        "Tracing-only log hygiene row must stay collapsed by default"
    )
    nested_titles = {
        panel.get("title")
        for panel in row_panel.get("panels", [])
        if isinstance(panel.get("title"), str)
    }
    assert nested_titles == {
        "Warnings",
        "Unstructured Logs",
        "Top Warning Events",
        "Log Hygiene Trend",
    }


def test_runtime_dashboard_describes_tracing_optional_mode() -> None:
    """Runtime dashboard should explain the tracing-off degradation path."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    description = dashboard.get("description", "")
    assert "Prometheus-first" in description
    assert "optional tracing profile" in description

    note_panel = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title") == "Diagnostic Scope Note"
        ),
        None,
    )
    assert note_panel is not None, (
        "Runtime dashboard must expose a tracing-mode guidance note"
    )
    content = note_panel.get("options", {}).get("content", "")
    assert "L2 diagnostic flow" in content
    assert "Prometheus-first mode" in content
    assert "Tracing-only Log Hygiene" in content
    assert "DQ / Control Plane / Provider Health" in content


def test_control_plane_dashboard_contains_checkpoint_and_replay_metrics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
        "bioetl_checkpoint_load_events_total",
        "bioetl_checkpoint_save_events_total",
        "bioetl_checkpoint_operator_operations_total",
        "bioetl_checkpoint_save_duration_seconds_bucket",
        "bioetl_checkpoint_operator_duration_seconds_bucket",
        "bioetl_lineage_fragments_emitted_total",
        "bioetl_replay_reconstructability_events_total",
        "bioetl_replay_drift_events_total",
        "bioetl_replay_lag_seconds",
        "bioetl_audit_write_events_total",
        "bioetl_audit_query_events_total",
        "bioetl_audit_write_duration_seconds_bucket",
        "bioetl_audit_query_duration_seconds_bucket",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Control-plane dashboard missing metrics: {missing}"


def test_provider_dashboard_contains_operator_surface_metrics() -> None:
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    all_expressions = "\n".join(get_panel_expressions(dashboard))
    required_metrics = [
        "bioetl_adapter_request_duration_seconds",
        "bioetl_http_request_errors_total",
        "bioetl_rate_limiter_wait_seconds",
        "bioetl_rate_limiter_tokens_available",
        "bioetl_circuit_breaker_state",
        "bioetl_circuit_breaker_trips_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Provider dashboard missing metrics: {missing}"


def test_dq_dashboard_contains_gold_specific_validation_surface() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Gold Strict Validation Failures"
        ),
        None,
    )
    assert panel is not None
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any('stage="gold"' in expr for expr in expressions)
    assert any('severity="hard_fail"' in expr for expr in expressions)


def test_overview_failed_runs_uses_run_metric_and_selected_time_range() -> None:
    """Overview failure indicator must use bounded failed-run events."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Failed Runs in Range"
        ),
        None,
    )
    assert panel is not None, "Panel 'Failed Runs in Range' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_pipeline_runs_total" in expr for expr in expressions), (
        "Failed Runs in Range must use bioetl_pipeline_runs_total"
    )
    assert any('status="failed"' in expr for expr in expressions)
    assert any("[$__range]" in expr for expr in expressions), (
        "Failed Runs in Range must use the selected Grafana time range"
    )


def test_runtime_pipeline_errors_panel_uses_runtime_error_metric_and_selected_time_range() -> (
    None
):
    """Runtime error-rate panel must use shipped runtime errors over its fixed window."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Runtime Error Rate / 30m"
        ),
        None,
    )
    assert panel is not None, "Panel 'Runtime Error Rate / 30m' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Runtime Error Rate / 30m must use bioetl_errors_total"
    )
    assert any("[30m]" in expr for expr in expressions), (
        "Runtime Error Rate / 30m must use the shipped 30-minute window"
    )


def test_runtime_pipeline_error_code_breakdown_uses_bounded_runtime_error_metric() -> (
    None
):
    """Runtime error breakdown must stay on bounded stage/error_code labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Errors by Stage / Error Code / Range"
        ),
        None,
    )
    assert panel is not None, "Panel 'Errors by Stage / Error Code / Range' not found"

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, (
        "Panel 'Errors by Stage / Error Code / Range' must define a query target"
    )
    expressions = [
        target.get("expr", "")
        for target in targets
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Errors by Stage / Error Code / Range must use bioetl_errors_total"
    )
    assert any(
        "by(stage, error_code)" in expr or "by (stage, error_code)" in expr
        for expr in expressions
    ), "Errors by Stage / Error Code / Range must group by stage and error_code"
    assert any("[$__range]" in expr for expr in expressions), (
        "Errors by Stage / Error Code / Range must use the selected Grafana time range"
    )
    assert all(target.get("instant") is True for target in targets), (
        "Errors by Stage / Error Code / Range must use instant Prometheus queries"
    )


@pytest.mark.parametrize(
    ("panel_title", "expected_snippet"),
    [
        ("Healthy Checks", "[$__range]"),
        ("Degraded Checks", "[$__range]"),
        ("Provider Failure Rate", "[$__range]"),
        ("Health Checks Total", "[$__range]"),
        ("Adapter Request Latency by Endpoint (p95)", "[$__interval]"),
        ("HTTP Errors by Method / Error Type", "[$__interval]"),
        ("Rate Limiter Wait by Provider (p95)", "[$__interval]"),
        ("Minimum Rate Limiter Tokens Available", "[$__range]"),
    ],
)
def test_provider_health_summary_panels_use_selected_time_range(
    panel_title: str, expected_snippet: str
) -> None:
    """Provider summary panels must respect the active Grafana time range."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any(expected_snippet in expr for expr in expressions), (
        f"Panel '{panel_title}' must use the selected Grafana time range"
    )


def test_provider_circuit_breaker_panels_use_adapter_variable() -> None:
    """Circuit-breaker metrics expose adapter labels, not provider labels."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )

    for panel_title in (
        "Circuit Breaker State (max)",
        "Circuit Breaker Trips by Provider",
    ):
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, f"Panel '{panel_title}' not found"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions, f"Panel '{panel_title}' has no PromQL expressions"
        assert any('adapter=~"$adapter"' in expr for expr in expressions), (
            f"Panel '{panel_title}' must filter circuit-breaker metrics via adapter"
        )
        assert all('adapter=~"$provider"' not in expr for expr in expressions), (
            f"Panel '{panel_title}' must not assume provider equals adapter"
        )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title", "expected_snippet"),
    [
        (
            "bioetl-runtime.json",
            "Pipeline Phase Duration p50/p95/p99",
            "[$__rate_interval]",
        ),
        ("bioetl-runtime.json", "Pipeline Duration p50/p95/p99", "[$__rate_interval]"),
        (
            "bioetl-runtime.json",
            "Shutdown Initiated by Reason / Interval",
            "[$__interval]",
        ),
        (
            "bioetl-runtime.json",
            "Shutdown Completed by Reason / Interval",
            "[$__interval]",
        ),
        ("bioetl-control-plane-v1.json", "Audit Write Outcomes", "[$__interval]"),
        ("bioetl-control-plane-v1.json", "Audit Query Outcomes", "[$__interval]"),
        (
            "bioetl-control-plane-v1.json",
            "Audit Write Latency p50/p95/p99",
            "[$__range]",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Audit Query Latency p50/p95/p99",
            "[$__range]",
        ),
    ],
)
def test_runtime_and_control_plane_operator_panels_use_active_time_windows(
    dashboard_file: str, panel_title: str, expected_snippet: str
) -> None:
    """Operator observability panels must respect active Grafana time windows."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any(expected_snippet in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use the active Grafana time window"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-overview-v2.json", "Manifest / Ledger Failures"),
        ("bioetl-overview-v2.json", "Checkpoint Incompatibilities"),
        ("bioetl-overview-v2.json", "Lineage Refs Missing"),
        ("bioetl-overview-v2.json", "Failed Runs in Range"),
        ("bioetl-overview-v2.json", "DQ Hard Blockers"),
        ("bioetl-overview-v2.json", "Control-plane Blockers"),
        ("bioetl-overview-v2.json", "Global Provider Degradation"),
        ("bioetl-overview-v2.json", "Workflow Status"),
        ("bioetl-control-plane-v1.json", "GLOBAL Control-Plane Read Failures"),
        (
            "bioetl-control-plane-v1.json",
            "GLOBAL Control-Plane Read Latency p50/p95/p99",
        ),
        ("bioetl-dq-v2.json", "Records Quarantined"),
        ("bioetl-dq-v2.json", "Soft Threshold Exceeded"),
        ("bioetl-dq-v2.json", "Quarantine by Error Type"),
        ("bioetl-dq-v2.json", "Silver Validation Failures"),
        ("bioetl-dq-v2.json", "Lineage Refs Missing"),
        ("bioetl-runtime.json", "Warnings"),
        ("bioetl-runtime.json", "Unstructured Logs"),
        ("bioetl-runtime.json", "Errors by Stage / Error Code / Range"),
        ("bioetl-runtime.json", "Records by Stage / Run Type / Range"),
        ("bioetl-runtime.json", "Top Warning Events"),
    ],
)
def test_range_aware_summary_panels_use_selected_time_range(
    dashboard_file: str, panel_title: str
) -> None:
    """Summary and triage panels should follow the active Grafana time range."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("[$__range]" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use the selected Grafana time range"
    )


@pytest.mark.parametrize(
    ("panel_title", "expected_recording_metrics"),
    [
        (
            "Pipeline Alert Conditions",
            [
                "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
                "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m",
                "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
                "bioetl_runtime_alert_condition_runtime_error_rate_high_30m",
            ],
        ),
        (
            "DQ Alert Conditions",
            [
                "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
                "bioetl_runtime_alert_condition_dq_hard_fail_15m",
                "bioetl_runtime_alert_condition_dq_critical_anomaly_30m",
                "bioetl_runtime_alert_condition_silver_validation_failures_30m",
            ],
        ),
        (
            "Control-plane Alert Conditions",
            [
                "bioetl_runtime_alert_condition_manifest_write_failed_15m",
                "bioetl_runtime_alert_condition_ledger_append_failed_15m",
                "bioetl_runtime_alert_condition_checkpoint_incompatible_30m",
                "bioetl_runtime_alert_condition_lineage_refs_missing_15m",
            ],
        ),
        (
            "GLOBAL Provider Alert Conditions",
            [
                "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
                "bioetl_runtime_alert_condition_provider_retries_exhausted_1h",
                "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m",
                "bioetl_runtime_alert_condition_provider_http_error_rate_high_15m",
                "bioetl_runtime_alert_condition_provider_rate_limiter_wait_high_30m",
                "bioetl_runtime_alert_condition_provider_rate_limiter_tokens_depleted_15m",
            ],
        ),
    ],
)
def test_runtime_alert_condition_panels_use_recording_rules(
    panel_title: str, expected_recording_metrics: list[str]
) -> None:
    """Runtime alert-summary panels should consume shipped recording rules."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in bioetl-runtime.json"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions, f"Panel '{panel_title}' must define an expression"
    for metric_name in expected_recording_metrics:
        assert any(metric_name in expr for expr in expressions), (
            f"Panel '{panel_title}' must include recording rule metric {metric_name!r}"
        )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-control-plane-v1.json", "Lineage Fragment Outcomes"),
        ("bioetl-dq-v2.json", "DQ Check Duration (p95)"),
        ("bioetl-dq-v2.json", "Anomalies Detected"),
        ("bioetl-runtime.json", "Records by Stage / Interval"),
        ("bioetl-runtime.json", "Log Hygiene Trend"),
    ],
)
def test_adaptive_trend_panels_use_selected_interval(
    dashboard_file: str, panel_title: str
) -> None:
    """Trend panels should adapt to the active Grafana window via $__interval."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("[$__interval]" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use $__interval"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title", "expected_snippet"),
    [
        (
            "bioetl-runtime.json",
            "Top Warning Events",
            'label_replace(vector(0), "event", "none", "", "")',
        ),
        (
            "bioetl-runtime.json",
            "Errors by Stage / Error Code / Range",
            'label_replace(label_replace(vector(0), "stage", "none", "", ""), "error_code", "none", "", "")',
        ),
        (
            "bioetl-control-plane-v1.json",
            "Checkpoint Compatibility Outcomes",
            'label_replace(vector(0), "disposition", "no_events", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Quarantine by Error Type",
            'label_replace(vector(0), "error_type", "none", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Anomalies Detected",
            'label_replace(label_replace(vector(0), "severity", "none", "", ""), "anomaly_type", "none", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Silver Filter Rejects by Pipeline",
            'label_replace(vector(0), "pipeline", "no_events", "", "")',
        ),
    ],
)
def test_empty_state_distribution_panels_use_explicit_placeholder_series(
    dashboard_file: str, panel_title: str, expected_snippet: str
) -> None:
    """Distribution panels should render an explicit zero placeholder instead of empty canvas."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any(expected_snippet in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must include "
        f"{expected_snippet!r} to avoid empty-state no-data rendering"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_titles_do_not_expose_fixed_window_suffixes(
    dashboard_path: Path,
) -> None:
    """Shipped dashboards should rely on Grafana window controls, not fixed time suffixes."""
    dashboard = load_dashboard(dashboard_path)
    titles = [
        panel.get("title", "")
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("title"), str)
    ]
    offenders = [title for title in titles if re.search(r"\((24h|15m|1h|5m)\)$", title)]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} still contains fixed-window titles: {offenders}"
    )


def test_overview_processing_volume_panel_splits_units() -> None:
    """Processing-volume panel must stay record-only; backlog and lag must be separate."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    processing = panels.get("Processing Volume by Stage")
    assert processing is not None
    processing_expr = "\n".join(
        target.get("expr", "")
        for target in processing.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_records_processed_total" in processing_expr
    assert "bioetl_stage_backlog_records" not in processing_expr
    assert "bioetl_stage_lag_seconds" not in processing_expr

    worst_backlog = panels.get("Worst Backlog Stage")
    assert worst_backlog is not None
    worst_backlog_expr = "\n".join(
        target.get("expr", "")
        for target in worst_backlog.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_backlog_records" in worst_backlog_expr
    assert "topk(1" in worst_backlog_expr
    assert "by (stage)" in worst_backlog_expr
    assert "[$__range]" in worst_backlog_expr

    backlog = panels.get("Stage Backlog Trend")
    assert backlog is not None
    backlog_expr = "\n".join(
        target.get("expr", "")
        for target in backlog.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_backlog_records" in backlog_expr
    assert "[$__interval]" in backlog_expr

    worst_lag = panels.get("Worst Lag Stage")
    assert worst_lag is not None
    worst_lag_expr = "\n".join(
        target.get("expr", "")
        for target in worst_lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_lag_seconds" in worst_lag_expr
    assert "topk(1" in worst_lag_expr
    assert "by (stage)" in worst_lag_expr
    assert "[$__range]" in worst_lag_expr

    lag = panels.get("Stage Lag Trend")
    assert lag is not None
    lag_expr = "\n".join(
        target.get("expr", "")
        for target in lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_lag_seconds" in lag_expr
    assert "[$__interval]" in lag_expr
    assert lag.get("fieldConfig", {}).get("defaults", {}).get("unit") == "s"


def test_runtime_alert_condition_breakdown_panels_exist() -> None:
    """Runtime must expose localization panels in addition to summary cards."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected = {
        "Stage Backlog Trend": "bioetl_stage_backlog_records",
        "Errors by Stage / Error Code / Range": "bioetl_errors_total",
        "Records by Stage / Run Type / Range": "bioetl_records_processed_total",
        "Pipeline Phase Duration p50/p95/p99": "bioetl_phase_duration_seconds_bucket",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for panel_title, required_metric in expected.items():
        panel = panels.get(panel_title)
        assert panel is not None, f"Runtime dashboard missing {panel_title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert required_metric in expr


@pytest.mark.parametrize("dashboard_file", ["bioetl-control-plane-v1.json"])
def test_replay_panels_are_split_by_semantics(dashboard_file: str) -> None:
    """Control-plane replay diagnostics must keep reconstructability, drift, and lag separate."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    reconstruct = panels.get("Replay Not Reconstructable")
    assert reconstruct is not None
    reconstruct_expr = "\n".join(
        target.get("expr", "")
        for target in reconstruct.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_reconstructability_events_total" in reconstruct_expr
    assert "bioetl_replay_drift_events_total" not in reconstruct_expr
    assert "bioetl_replay_lag_seconds" not in reconstruct_expr

    drift = panels.get("Replay Drift Events")
    if dashboard_file == "bioetl-control-plane-v1.json":
        drift = panels.get("Replay Drift")
    assert drift is not None
    drift_expr = "\n".join(
        target.get("expr", "")
        for target in drift.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_drift_events_total" in drift_expr

    lag = panels.get("Replay Lag Seconds")
    assert lag is not None
    lag_expr = "\n".join(
        target.get("expr", "")
        for target in lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_lag_seconds" in lag_expr
    assert lag.get("fieldConfig", {}).get("defaults", {}).get("unit") == "s"


def test_dashboard_default_time_from_policy_by_uid() -> None:
    """Shipped dashboards must keep canonical default time.from policy by UID."""
    expected_time_from_by_uid = {
        "bioetl-overview-v2": "now-12h",
        "bioetl-runtime": "now-12h",
        "bioetl-dq-v2": "now-12h",
        "bioetl-provider-health-v2": "now-12h",
        "bioetl-workflow-overview": "now-12h",
        "bioetl-control-plane-v1": "now-12h",
        "bioetl-silver-reject-explorer": "now-24h",
    }

    for uid, expected_time_from in expected_time_from_by_uid.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        actual_uid = dashboard.get("uid")
        assert actual_uid == uid, f"Dashboard UID mismatch for {uid}.json"

        time_cfg = dashboard.get("time", {})
        assert isinstance(time_cfg, dict), f"{uid} time config must be an object"
        assert time_cfg.get("from") == expected_time_from, (
            f"{uid} must keep time.from={expected_time_from!r}, "
            f"got {time_cfg.get('from')!r}"
        )


def test_provider_health_selected_provider_detail_row_is_collapsed() -> None:
    """Provider detail repeat row should be explicit and collapsed by default."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panels = get_dashboard_panels(dashboard)
    detail_row = next(
        (
            panel
            for panel in panels
            if panel.get("type") == "row"
            and panel.get("title") == "Selected Provider Detail"
        ),
        None,
    )
    assert detail_row is not None
    assert detail_row.get("collapsed") is True

    repeated_panel = next(
        (panel for panel in panels if panel.get("repeat") == "provider"),
        None,
    )
    assert repeated_panel is not None
    assert repeated_panel.get("gridPos", {}).get("y", 0) >= detail_row.get(
        "gridPos", {}
    ).get("y", 0)
