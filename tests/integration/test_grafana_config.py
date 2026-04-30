"""Integration tests for Grafana dashboard configurations and observability contracts."""

from collections import Counter
from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import (
    _PROMQL_METRIC_SELECTOR_RE,
    _assert_provider_health_variable_contract,
    _assert_silver_reject_explorer_variable_contract,
    _assert_standard_variable_contract,
    _collect_dashboard_links,
    _emit_sample_structured_log,
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
        "bioetl-provider-health-v2.json": {"provider"},
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


def test_summary_queries_use_zero_fallbacks() -> None:
    """Runtime/provider summary panels should show zero instead of no-data."""
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Manifest Write Failures": "or vector(0)",
            "Ledger Append Failures": "or vector(0)",
            "Checkpoint Incompatibilities": "or vector(0)",
            "Lineage Refs Missing": "or vector(0)",
            "Composite Source Selections": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
            "Pipeline Error Rate": "or vector(0)",
        },
        "bioetl-runtime.json": {
            "Warnings": "or vector(0)",
            "Unstructured Logs": "or vector(0)",
            "Pipeline Alert Conditions": "or vector(0)",
            "DQ Alert Conditions": "or vector(0)",
            "Control-plane Alert Conditions": "or vector(0)",
            "Provider Alert Conditions": "or vector(0)",
            "Freshness Alert Conditions": "or vector(0)",
            "Trace-enabled Runs": "or vector(0)",
            "Pipeline Errors": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
            "Metrics Endpoint Up": "or vector(0)",
            "Prometheus Up": "or vector(0)",
            "Grafana Up": "or vector(0)",
            "Pushgateway Up": "or vector(0)",
            "No-Records Processed Runs": "or vector(0)",
            "Replay Not Reconstructable": "or vector(0)",
            "Phase Duration by Phase (p95)": "or vector(0)",
            "Postrun Phase Duration by Phase (p95)": "or vector(0)",
            "Shutdown Initiated by Reason": "or vector(0)",
            "Shutdown Completed by Reason": "or vector(0)",
            "Log Hygiene Trend": 'label_replace(vector(0), "series",',
        },
        "bioetl-provider-health-v2.json": {
            "Healthy Checks": "or vector(0)",
            "Degraded Checks": "or vector(0)",
            "Provider Failure Rate": "or vector(0)",
            "Health Checks Total": "or vector(0)",
            "Adapter Request Latency by Endpoint (p95)": "or vector(0)",
            "HTTP Errors by Method / Error Type": "or vector(0)",
            "Rate Limiter Wait by Provider (p95)": "or vector(0)",
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
            "Manifest Write Failures": "or vector(0)",
            "Ledger Append Failures": "or vector(0)",
            "Checkpoint Compatibility Incompatibilities": "or vector(0)",
            "Control-Plane Read Failures": "or vector(0)",
            "Checkpoint Load Failures": "or vector(0)",
            "Checkpoint Save Failures": "or vector(0)",
            "Checkpoint Operator Failures": "or vector(0)",
            "Replay Not Reconstructable": "or vector(0)",
            "Checkpoint Save Latency (p95)": "or vector(0)",
            "Checkpoint Operator Latency (p95)": "or vector(0)",
            "Audit Write Outcomes": "or vector(0)",
            "Audit Query Outcomes": "or vector(0)",
            "Audit Write Latency (p95)": "or vector(0)",
            "Audit Query Latency (p95)": "or vector(0)",
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


def test_count_like_summary_panels_use_rounding_or_boolean_conditions() -> None:
    """Count-like summary panels should avoid fractional event semantics."""
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Manifest Write Failures": "round(",
            "Ledger Append Failures": "round(",
            "Checkpoint Incompatibilities": "round(",
            "Lineage Refs Missing": "round(",
            "Composite Source Selections": "round(",
            "Silver Filter Rejects": "round(",
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
            "Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
            "Trace-enabled Runs": "round(",
            "Pipeline Errors": "round(",
            "Silver Filter Rejects": "round(",
            "Shutdown Initiated by Reason": "round(",
            "Shutdown Completed by Reason": "round(",
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
            "Stage Distribution in Range": ("increase(", "last_over_time("),
            "Pipeline Distribution in Range": ("increase(", "last_over_time("),
            "Overall Yield (Selected Range)": ("increase(", "last_over_time("),
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
            "Silver Filter Rejects": ("increase(",),
            "Shutdown Initiated by Reason": ("increase(",),
            "Shutdown Completed by Reason": ("increase(",),
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
    """Guard against rendering raw Unix timestamps as freshness lag."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Data Freshness Lag (seconds)"
        ),
        None,
    )
    assert panel is not None, "Freshness lag panel not found in bioetl-dq-v2.json"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any(
        "clamp_min(time() - max(bioetl_data_freshness_seconds" in expr
        for expr in expressions
    ), "Freshness panel must derive lag from the last-ingestion timestamp metric"


def test_overview_dashboard_contains_control_plane_and_lineage_metrics():
    """Ensure overview dashboard exposes control-plane and lineage health signals."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_fragments_emitted_total",
        "bioetl_lineage_refs_missing_total",
        "bioetl_composite_source_selection_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


def test_control_plane_lookup_panels_disclose_global_scope() -> None:
    """Control-plane read panels must disclose that they are global, not pipeline-scoped."""
    expectations = {
        "bioetl-overview-v2.json": (
            "Global Control-plane Lookup Failures",
            "Global Control-plane Lookup p95",
        ),
        "bioetl-runtime.json": (
            "Global Control-plane Lookup Outcomes",
            "Global Control-plane Lookup p95",
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
        "bioetl-overview-v2.json": (
            "Global Control-plane Lookup Failures",
            "Global Control-plane Lookup p95",
        ),
        "bioetl-runtime.json": (
            "Global Control-plane Lookup Outcomes",
            "Global Control-plane Lookup p95",
        ),
        "bioetl-control-plane-v1.json": (
            "Control-Plane Read Failures",
            "Control-Plane Reads by Store and Status",
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


def test_runtime_provider_alert_conditions_do_not_filter_on_missing_pipeline_labels():
    """Provider runtime alert summaries are fleet-wide and must not filter on pipeline."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Provider Alert Conditions"
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
        "Provider Alert Conditions must not filter provider-only recording rules by pipeline."
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
    """Ensure runtime dashboard stays anchored to log hygiene and alert-condition metrics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_errors_total",
        "bioetl_records_processed_total",
        "bioetl_memory_pressure_events_total",
        "bioetl_memory_batch_resize_events_total",
        "bioetl_memory_monitor_fallback_events_total",
        "bioetl_memory_pressure_state",
        "bioetl_phase_duration_seconds",
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_shutdown_initiated",
        "bioetl_shutdown_completed",
        "bioetl_replay_reconstructability_events_total",
        "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
        "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m",
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_alert_condition_runtime_error_rate_high_30m",
        "bioetl_runtime_alert_condition_record_flow_invariant_violated_15m",
        "bioetl_runtime_alert_condition_ingestion_throughput_degraded_15m",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m",
        "bioetl_runtime_alert_condition_stage_lag_high_15m",
        "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
        "bioetl_runtime_alert_condition_dq_hard_fail_15m",
        "bioetl_runtime_alert_condition_dq_critical_anomaly_30m",
        "bioetl_runtime_alert_condition_silver_validation_failures_30m",
        "bioetl_runtime_alert_condition_manifest_write_failed_15m",
        "bioetl_runtime_alert_condition_ledger_append_failed_15m",
        "bioetl_runtime_alert_condition_checkpoint_incompatible_30m",
        "bioetl_runtime_alert_condition_lineage_refs_missing_15m",
        "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
        "bioetl_runtime_alert_condition_provider_retries_exhausted_1h",
        "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m",
        "bioetl_runtime_alert_condition_provider_http_error_rate_high_15m",
        "bioetl_runtime_alert_condition_provider_rate_limiter_wait_high_30m",
        "bioetl_runtime_alert_condition_provider_rate_limiter_tokens_depleted_15m",
        "bioetl_data_freshness_seconds",
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
        "bioetl_traced_runs_total",
        'up{job="bioetl"}',
        'up{job="prometheus"}',
        'up{job="grafana"}',
        'up{job="pushgateway"}',
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
            if panel.get("title") == "Tracing Mode Note"
        ),
        None,
    )
    assert note_panel is not None, (
        "Runtime dashboard must expose a tracing-mode guidance note"
    )
    content = note_panel.get("options", {}).get("content", "")
    assert "Prometheus-first mode" in content
    assert "Tracing-only Log Hygiene" in content
    assert "Overview, Control Plane, and Data Quality" in content


def test_control_plane_dashboard_contains_checkpoint_and_replay_metrics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_checkpoint_load_events_total",
        "bioetl_checkpoint_save_events_total",
        "bioetl_checkpoint_operator_operations_total",
        "bioetl_checkpoint_save_duration_seconds_bucket",
        "bioetl_checkpoint_operator_duration_seconds_bucket",
        "bioetl_replay_reconstructability_events_total",
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


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-overview-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects by Pipeline"),
        ("bioetl-runtime.json", "Silver Filter Rejects"),
    ],
)
def test_silver_filter_reject_panels_use_filtered_out_stage(
    dashboard_file: str, panel_title: str
) -> None:
    """Silver filter rejects must stay separate from DQ quarantine semantics."""
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
    assert expressions, f"Panel '{panel_title}' in {dashboard_file} has no expressions"
    assert any("bioetl_records_processed_total" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use "
        "bioetl_records_processed_total"
    )
    assert any('stage="filtered_out"' in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must filter on stage=\"filtered_out\""
    )
    assert any("[$__range]" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use the selected Grafana time range"
    )


def test_silver_filter_reject_rate_uses_selected_time_range() -> None:
    """Silver filter reject rate must follow the active dashboard time range."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Silver Filter Reject Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Silver Filter Reject Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("[$__range]" in expr for expr in expressions), (
        "Silver Filter Reject Rate must use the selected Grafana time range"
    )


def test_pipeline_error_rate_uses_runtime_error_metric_and_selected_time_range() -> (
    None
):
    """Pipeline error rate must use bounded runtime errors over the active range."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Pipeline Error Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Pipeline Error Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Pipeline Error Rate must use bioetl_errors_total"
    )
    assert any('stage="bronze"' in expr for expr in expressions), (
        "Pipeline Error Rate must normalize against bronze-stage processed volume"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        "Pipeline Error Rate must use the selected Grafana time range"
    )


def test_runtime_pipeline_errors_panel_uses_runtime_error_metric_and_selected_time_range() -> (
    None
):
    """Runtime Pipeline Errors must use shipped runtime errors over the active range."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Pipeline Errors"
        ),
        None,
    )
    assert panel is not None, "Panel 'Pipeline Errors' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Pipeline Errors must use bioetl_errors_total"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        "Pipeline Errors must use the selected Grafana time range"
    )


def test_runtime_pipeline_error_code_breakdown_uses_bounded_runtime_error_metric() -> (
    None
):
    """Top Pipeline Error Codes must stay on bounded runtime error labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Top Pipeline Error Codes"
        ),
        None,
    )
    assert panel is not None, "Panel 'Top Pipeline Error Codes' not found"

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, "Panel 'Top Pipeline Error Codes' must define a query target"
    expressions = [
        target.get("expr", "")
        for target in targets
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Top Pipeline Error Codes must use bioetl_errors_total"
    )
    assert any("by (error_code)" in expr for expr in expressions), (
        "Top Pipeline Error Codes must group by error_code"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        "Top Pipeline Error Codes must use the selected Grafana time range"
    )
    assert all(target.get("instant") is True for target in targets), (
        "Top Pipeline Error Codes must use instant Prometheus queries"
    )


@pytest.mark.parametrize(
    ("panel_title", "label_name"),
    [
        ("Top Silver Reject Reasons", "reason_code"),
        ("Top Silver Reject Fields", "field"),
    ],
)
def test_silver_filter_breakdown_panels_use_bounded_breakdown_metric(
    panel_title: str, label_name: str
) -> None:
    """Reason/field breakdown panels must use the bounded Silver breakdown metric."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in bioetl-dq-v2.json"

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, f"Panel '{panel_title}' must define at least one query target"
    expressions = [
        target.get("expr", "")
        for target in targets
        if isinstance(target.get("expr"), str)
    ]
    assert any(
        "bioetl_silver_filter_rejections_total" in expr for expr in expressions
    ), f"Panel '{panel_title}' must use bioetl_silver_filter_rejections_total"
    assert any(f"by ({label_name})" in expr for expr in expressions), (
        f"Panel '{panel_title}' must group by {label_name}"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        f"Panel '{panel_title}' must use the selected Grafana time range"
    )
    assert all(target.get("instant") is True for target in targets), (
        f"Panel '{panel_title}' must use instant Prometheus queries"
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


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title", "expected_snippet"),
    [
        ("bioetl-runtime.json", "Phase Duration by Phase (p95)", "[$__interval]"),
        (
            "bioetl-runtime.json",
            "Postrun Phase Duration by Phase (p95)",
            "[$__interval]",
        ),
        ("bioetl-runtime.json", "Shutdown Initiated by Reason", "[$__interval]"),
        ("bioetl-runtime.json", "Shutdown Completed by Reason", "[$__interval]"),
        ("bioetl-control-plane-v1.json", "Audit Write Outcomes", "[$__interval]"),
        ("bioetl-control-plane-v1.json", "Audit Query Outcomes", "[$__interval]"),
        ("bioetl-control-plane-v1.json", "Audit Write Latency (p95)", "[$__interval]"),
        ("bioetl-control-plane-v1.json", "Audit Query Latency (p95)", "[$__interval]"),
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
        ("bioetl-overview-v2.json", "Manifest Write Failures"),
        ("bioetl-overview-v2.json", "Ledger Append Failures"),
        ("bioetl-overview-v2.json", "Checkpoint Incompatibilities"),
        ("bioetl-overview-v2.json", "Lineage Refs Missing"),
        ("bioetl-overview-v2.json", "Composite Source Selections"),
        ("bioetl-overview-v2.json", "Global Control-plane Lookup Failures"),
        ("bioetl-overview-v2.json", "Global Control-plane Lookup p95"),
        ("bioetl-overview-v2.json", "Pipeline Error Rate"),
        ("bioetl-dq-v2.json", "Records Quarantined"),
        ("bioetl-dq-v2.json", "Soft Threshold Exceeded"),
        ("bioetl-dq-v2.json", "Quarantine by Error Type"),
        ("bioetl-dq-v2.json", "Silver Validation Failures"),
        ("bioetl-dq-v2.json", "Lineage Refs Missing"),
        ("bioetl-runtime.json", "Warnings"),
        ("bioetl-runtime.json", "Unstructured Logs"),
        ("bioetl-runtime.json", "DQ Context Failures"),
        ("bioetl-runtime.json", "DQ Reports Skipped"),
        ("bioetl-runtime.json", "DQ Reports Generated"),
        ("bioetl-runtime.json", "Pipeline Errors"),
        ("bioetl-runtime.json", "Memory Pressure Events"),
        ("bioetl-runtime.json", "Batch Resize Events"),
        ("bioetl-runtime.json", "Fallback Monitor Decisions"),
        ("bioetl-runtime.json", "Memory Pressure Active"),
        ("bioetl-runtime.json", "Global Control-plane Lookup p95"),
        ("bioetl-runtime.json", "Top Warning Events"),
        ("bioetl-runtime.json", "Top Pipeline Error Codes"),
        ("bioetl-runtime.json", "Trace-enabled Runs"),
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
            "Provider Alert Conditions",
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
        ("bioetl-overview-v2.json", "Lineage Fragment Outcomes"),
        ("bioetl-dq-v2.json", "DQ Check Duration (p95)"),
        ("bioetl-dq-v2.json", "Anomalies Detected"),
        ("bioetl-runtime.json", "Global Control-plane Lookup Outcomes"),
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
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-overview-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects"),
        ("bioetl-runtime.json", "Silver Filter Rejects"),
    ],
)
def test_silver_filter_rejects_summary_panels_use_instant_queries(
    dashboard_file: str, panel_title: str
) -> None:
    """Selected-range reject totals should be evaluated as instant summaries."""
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

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, (
        f"Panel '{panel_title}' in {dashboard_file} must define a query target"
    )
    assert all(target.get("instant") is True for target in targets), (
        f"Panel '{panel_title}' in {dashboard_file} must use instant Prometheus queries"
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
            "Top Pipeline Error Codes",
            'label_replace(vector(0), "error_code", "none", "", "")',
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
            "bioetl-runtime.json",
            "Global Control-plane Lookup Outcomes",
            'label_replace(label_replace(vector(0), "store", "none", "", ""), "status", "none", "", "")',
        ),
        (
            "bioetl-control-plane-v1.json",
            "Checkpoint Compatibility Outcomes by Disposition",
            'label_replace(vector(0), "disposition", "no_events", "", "")',
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


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_queries_do_not_filter_by_run_id_label(dashboard_path):
    """Dashboards must avoid run_id label filters to prevent high cardinality usage."""
    dashboard = load_dashboard(dashboard_path)
    expressions = get_panel_expressions(dashboard)

    offenders = [
        expr
        for expr in expressions
        if re.search(r"\brun_id\s*(=|=~|!=|!~)\s*", expr) is not None
    ]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} must not filter by run_id label.\n"
        + "\n".join(offenders[:10])
    )

    variables = [
        var.get("name") for var in dashboard.get("templating", {}).get("list", [])
    ]
    if dashboard_path.name == "bioetl-provider-health-v2.json":
        assert "provider" in variables, (
            "Provider dashboard must define 'provider' template variable"
        )
    elif dashboard_path.name == "bioetl-workflow-overview.json":
        assert "workflow" in variables, (
            "Workflow dashboard must define 'workflow' template variable"
        )
    else:
        assert "pipeline" in variables, (
            f"Dashboard {dashboard_path.name} must define 'pipeline' template variable"
        )


def test_overview_and_provider_dashboards_expose_explore_drilldown_links() -> None:
    """Operational dashboards should offer Loki and Tempo drilldown."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-provider-health-v2.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        links = _collect_dashboard_links(dashboard)
        titles = {link.get("title") for link in links if link.get("title")}
        urls = [link.get("url", "") for link in links]

        assert any("Logs" in title for title in titles), (
            f"{dashboard_name} must expose a logs drilldown link"
        )
        assert any("Traces" in title for title in titles), (
            f"{dashboard_name} must expose a traces drilldown link"
        )
        assert any("/a/grafana-lokiexplore-app/" in url for url in urls), (
            f"{dashboard_name} must point logs drilldown to Logs Drilldown app"
        )
        assert any("/a/grafana-exploretraces-app/" in url for url in urls), (
            f"{dashboard_name} must point traces drilldown to Traces Drilldown app"
        )
        drilldown_urls = [
            url
            for url in urls
            if "/a/grafana-lokiexplore-app/" in url
            or "/a/grafana-exploretraces-app/" in url
        ]
        assert drilldown_urls, (
            f"{dashboard_name} must expose Grafana Drilldown app URLs"
        )
        for url in drilldown_urls:
            assert "from=${__from}" in url and "to=${__to}" in url, (
                f"{dashboard_name} drilldown URL must preserve dashboard time range"
            )
            assert "/explore?left=" not in url, (
                f"{dashboard_name} drilldown URL must not use legacy /explore payload links"
            )


def _is_logs_drilldown_url(url: str) -> bool:
    return "/a/grafana-lokiexplore-app/" in url


def _is_traces_drilldown_url(url: str) -> bool:
    return "/a/grafana-exploretraces-app/" in url


def test_explore_links_use_drilldown_routes_and_time_range() -> None:
    """Explore links should target Drilldown apps and preserve current time range."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-provider-health-v2.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        drilldown_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if _is_logs_drilldown_url(link.get("url", ""))
            or _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert drilldown_links, (
            f"{dashboard_name} must expose at least one Drilldown app link"
        )

        for link in drilldown_links:
            url = link.get("url", "")
            assert "from=${__from}" in url and "to=${__to}" in url, (
                f"{dashboard_name} drilldown link must preserve current time range"
            )
            assert "/explore?left=" not in url, (
                f"{dashboard_name} drilldown link must not use legacy Explore payload URL"
            )


def test_tempo_drilldown_routes_to_traces_drilldown_app() -> None:
    """Tempo drilldown links should route to Grafana Traces Drilldown app."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-provider-health-v2.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        tempo_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert tempo_links, (
            f"{dashboard_name} must expose at least one Traces Drilldown link"
        )
        for link in tempo_links:
            url = link.get("url", "")
            assert "from=${__from}" in url and "to=${__to}" in url


def test_explore_drilldown_titles_disclose_tracing_profile_dependency() -> None:
    """Loki/Tempo drilldown titles should warn that tracing profile is required."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-provider-health-v2.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            title = link.get("title", "")
            if not (_is_logs_drilldown_url(url) or _is_traces_drilldown_url(url)):
                continue
            assert "tracing" in title.lower(), (
                f"{dashboard_name} Drilldown title must disclose tracing profile dependency"
            )


def test_loki_drilldown_uses_grafana_logs_drilldown_entrypoint() -> None:
    """Loki drilldown should route to Grafana Logs Drilldown app entrypoint."""
    sample_line = _emit_sample_structured_log(
        pipeline="chembl_activity",
        provider="chembl",
    )
    assert re.search(r'"pipeline"\s*:\s*"chembl_activity"', sample_line)
    assert re.search(r'"provider"\s*:\s*"chembl"', sample_line)
    assert re.search(r'"stage"\s*:\s*"extract"', sample_line)

    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-provider-health-v2.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        loki_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if _is_logs_drilldown_url(link.get("url", ""))
        ]
        assert loki_links, (
            f"{dashboard_name} must expose at least one Logs Drilldown link"
        )
        assert all(
            "/explore?left=" not in link.get("url", "") for link in loki_links
        ), f"{dashboard_name} must not keep legacy Loki Explore payload links"


def test_overview_and_runtime_dashboards_expose_data_quality_handoff() -> None:
    """Overview and Runtime should offer an explicit handoff into DQ triage."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        titles = {
            link.get("title")
            for link in dashboard.get("links", [])
            if link.get("title")
        }
        urls = [link.get("url", "") for link in dashboard.get("links", [])]

        assert "4. Data Quality" in titles, (
            f"{dashboard_name} must expose a Data Quality dashboard handoff"
        )
        assert any(url == "/d/bioetl-dq-v2" for url in urls), (
            f"{dashboard_name} Data Quality handoff must target /d/bioetl-dq-v2"
        )


def test_runtime_and_dq_dashboards_expose_control_plane_handoff() -> None:
    """Runtime and DQ should offer an explicit handoff into control-plane triage."""
    expectations = (
        "bioetl-runtime.json",
        "bioetl-dq-v2.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        titles = {
            link.get("title")
            for link in dashboard.get("links", [])
            if link.get("title")
        }
        urls = [link.get("url", "") for link in dashboard.get("links", [])]

        assert "Control Plane v1" in titles, (
            f"{dashboard_name} must expose a Control Plane dashboard handoff"
        )
        assert any(
            url == "/d/bioetl-control-plane-v1/bioetl-control-plane-v1" for url in urls
        ), (
            f"{dashboard_name} Control Plane handoff must target /d/bioetl-control-plane-v1/bioetl-control-plane-v1"
        )


def test_data_quality_dashboard_exposes_silver_reject_explorer_handoff() -> None:
    """Data Quality dashboard should expose an explicit handoff to Silver explorer."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    links = dashboard.get("links", [])
    titles = {link.get("title") for link in links if link.get("title")}
    urls = [link.get("url", "") for link in links]

    assert "5. Silver Reject Explorer" in titles, (
        "Data Quality dashboard must expose a Silver Reject Explorer handoff"
    )
    assert any(url == "/d/bioetl-silver-reject-explorer" for url in urls), (
        "Data Quality handoff must target /d/bioetl-silver-reject-explorer"
    )
    silver_link = next(
        (
            link
            for link in links
            if link.get("url") == "/d/bioetl-silver-reject-explorer"
        ),
        None,
    )
    assert silver_link is not None, "Silver Reject Explorer link must exist"
    assert silver_link.get("includeVars") is False, (
        "Data Quality handoff must not pass Prometheus variables into "
        "Silver Reject Explorer"
    )


def test_runtime_incident_panels_link_to_control_plane_dashboard() -> None:
    """Runtime incident panels should hand off directly into control-plane triage."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expectations = {
        "Control-plane Alert Conditions": "Open Control Plane v1 (manifest/checkpoint)",
        "No-Records Processed Runs": "Open Control Plane v1 (checkpoint/replay)",
        "Replay Not Reconstructable": "Open Control Plane v1 (replay/lineage)",
    }

    for panel_title, expected_link_title in expectations.items():
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, (
            f"Panel '{panel_title}' not found in bioetl-runtime.json"
        )
        data_links = panel.get("options", {}).get("dataLinks", [])
        link = next(
            (item for item in data_links if item.get("title") == expected_link_title),
            None,
        )
        assert link is not None, (
            f"Panel '{panel_title}' must expose control-plane incident handoff"
        )
        url = link.get("url", "")
        assert url.startswith("/d/bioetl-control-plane-v1/bioetl-control-plane-v1"), (
            f"Panel '{panel_title}' must hand off into control-plane dashboard"
        )
        assert "from=${__from}" in url and "to=${__to}" in url, (
            f"Panel '{panel_title}' handoff must preserve current time range"
        )
        assert "var-pipeline=$pipeline" in url and "var-run_type=$run_type" in url, (
            f"Panel '{panel_title}' handoff must preserve runtime pipeline scope"
        )


def test_data_quality_incident_panels_link_to_control_plane_dashboard() -> None:
    """DQ panels should link into control-plane investigation for replay/lineage paths."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expectations = {
        "Data Flow in Range: Bronze -> Silver -> Gold": "Open Control Plane v1 (replay/checkpoint)",
        "Lineage Refs Missing": "Open Control Plane v1 (lineage/traceability)",
        "Gold Strict Validation Failures": "Open Control Plane v1 (gold hard-fail context)",
    }

    for panel_title, expected_link_title in expectations.items():
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None, (
            f"Panel '{panel_title}' not found in bioetl-dq-v2.json"
        )
        data_links = panel.get("options", {}).get("dataLinks", [])
        link = next(
            (item for item in data_links if item.get("title") == expected_link_title),
            None,
        )
        assert link is not None, (
            f"Panel '{panel_title}' must expose control-plane incident handoff"
        )
        url = link.get("url", "")
        assert url.startswith("/d/bioetl-control-plane-v1/bioetl-control-plane-v1"), (
            f"Panel '{panel_title}' must hand off into control-plane dashboard"
        )
        assert "from=${__from}" in url and "to=${__to}" in url, (
            f"Panel '{panel_title}' handoff must preserve current time range"
        )
        assert "var-pipeline=$pipeline" in url and "var-run_type=$run_type" in url, (
            f"Panel '{panel_title}' handoff must preserve DQ pipeline scope"
        )


def test_silver_reject_explorer_record_level_panels_do_not_use_prometheus() -> None:
    """Record-level explorer panels must use the Quarantine Explorer datasource."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    expected_titles = {"Filtered Records Table", "Selected Record Details"}
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_titles
    }
    assert panels.keys() == expected_titles, (
        "Silver Reject Explorer must define both table and detail panels"
    )
    for title, panel in panels.items():
        datasource = panel.get("datasource")
        assert datasource == "Quarantine Explorer", (
            f"Panel {title!r} must use Quarantine Explorer datasource"
        )


def test_silver_reject_explorer_summary_panels_use_distinct_projections() -> None:
    """Summary trio should expose total, reject-rate view, and full scope summary separately."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel_map = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
        in {
            "Filtered Records Total",
            "Reject Rate vs Bronze",
            "Run Scope Summary",
        }
    }
    assert panel_map.keys() == {
        "Filtered Records Total",
        "Reject Rate vs Bronze",
        "Run Scope Summary",
    }, "Silver Reject Explorer must define all three scoped summary panels"

    total_panel = panel_map["Filtered Records Total"]
    total_transformations = total_panel.get("transformations", [])
    assert total_transformations, (
        "Filtered Records Total must project only total field, not full raw payload"
    )
    total_organize = next(
        (
            transformation
            for transformation in total_transformations
            if transformation.get("id") == "organize"
        ),
        None,
    )
    assert total_organize is not None, (
        "Filtered Records Total must use organize transform to isolate total"
    )
    total_options = total_organize.get("options", {})
    assert (
        total_options.get("renameByName", {}).get("total") == "filtered_records_total"
    )
    assert total_options.get("excludeByName", {}).get("reject_ratio") is True

    ratio_panel = panel_map["Reject Rate vs Bronze"]
    ratio_transformations = ratio_panel.get("transformations", [])
    ratio_organize = next(
        (
            transformation
            for transformation in ratio_transformations
            if transformation.get("id") == "organize"
        ),
        None,
    )
    assert ratio_organize is not None, (
        "Reject Rate vs Bronze must use organize transform for ratio/bronze/total view"
    )
    ratio_options = ratio_organize.get("options", {})
    assert ratio_options.get("renameByName", {}).get("reject_ratio") == (
        "reject_rate_vs_bronze"
    )
    assert ratio_options.get("excludeByName", {}).get("by_reason_code") is True

    ratio_overrides = ratio_panel.get("fieldConfig", {}).get("overrides", [])
    assert any(
        override.get("matcher", {}).get("options") == "reject_ratio"
        and any(prop.get("id") == "unit" for prop in override.get("properties", []))
        for override in ratio_overrides
        if isinstance(override, dict)
    ), "Reject Rate vs Bronze must format reject_ratio as percentage"

    summary_panel = panel_map["Run Scope Summary"]
    assert not summary_panel.get("transformations"), (
        "Run Scope Summary must remain full payload panel for forensic context"
    )


def test_silver_reject_explorer_selected_record_details_uses_safe_payload_filter() -> (
    None
):
    """Selected Record Details should not depend on path-bound payload hash."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            candidate
            for candidate in get_dashboard_panels(dashboard)
            if candidate.get("title") == "Selected Record Details"
        ),
        None,
    )
    assert panel is not None, (
        "Silver Reject Explorer must include Selected Record Details"
    )

    targets = panel.get("targets", [])
    assert targets, "Selected Record Details must define at least one query target"
    target = targets[0]
    url = target.get("url", "")
    assert isinstance(url, str), "Selected Record Details query URL must be a string"
    assert "/ops/quarantine/filtered-records" in url, (
        "Selected Record Details must query list endpoint to avoid hard failure "
        "when payload_hash is blank"
    )
    assert "/ops/quarantine/filtered-record/${payload_hash}" not in url, (
        "Selected Record Details must not use strict path payload hash endpoint"
    )
    assert "payload_hash=${payload_hash}" in url, (
        "Selected Record Details must filter by payload_hash via query parameter"
    )
    assert target.get("root_selector") == "items", (
        "Selected Record Details must parse list payload via items root selector"
    )


def test_control_plane_dashboard_exposes_working_runbook_link() -> None:
    """Control-plane dashboard should link to a stable, published runbook target."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    runbook_link = next(
        (
            link
            for link in dashboard.get("links", [])
            if link.get("title") == "Observability Checklist (runbook)"
        ),
        None,
    )

    assert runbook_link is not None, (
        "Control-plane dashboard must expose an Observability Checklist runbook link"
    )
    assert runbook_link.get("url") == (
        "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
        "docs/05-operations/runbooks/observability-checklist.md"
    ), "Control-plane dashboard runbook link must target the canonical GitHub doc"
    assert runbook_link.get("targetBlank") is True, (
        "External runbook link should open in a new tab"
    )
