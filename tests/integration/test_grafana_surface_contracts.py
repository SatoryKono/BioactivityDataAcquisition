"""Integration tests for Grafana dashboard surface-level observability contracts."""

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_row_child_panels,
    get_panel_expressions,
    load_dashboard,
)


pytestmark = pytest.mark.integration


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

    def is_loki_datasource(panel: dict[str, object]) -> bool:
        datasource = panel.get("datasource")
        if datasource == "Loki":
            return True
        return isinstance(datasource, dict) and datasource.get("type") == "loki"

    loki_exprs = [
        target.get("expr", "")
        for panel in get_dashboard_panels(dashboard)
        for target in panel.get("targets", [])
        if is_loki_datasource(panel)
    ]
    assert any("| json" in expr for expr in loki_exprs), (
        "Runtime dashboard Loki panels must parse structured JSON logs"
    )
    assert any('__error__!=""' in expr for expr in loki_exprs), (
        "Runtime dashboard must expose unstructured-log hygiene signal"
    )


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
        "Tracing-only log hygiene row must stay collapsed by default because "
        "Loki/Tempo datasources are optional in the default runtime profile"
    )
    nested_titles = {
        panel.get("title")
        for panel in get_row_child_panels(
            dashboard, "Tracing-only Log Hygiene (requires optional tracing profile)"
        )
        if isinstance(panel.get("title"), str)
    }
    assert nested_titles == {
        "Inspect Warning Logs",
        "Inspect GLOBAL Unstructured Logs",
        "Inspect Top Warning Events by Event / Logger / Range",
        "Track GLOBAL Log Hygiene Trend",
    }


def test_runtime_warning_loki_queries_filter_parsed_fields_after_json() -> None:
    """Warning log panels must not filter parsed JSON fields in the Loki selector."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    assert dashboard["version"] == 3
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    warning_panel = panels["Inspect Warning Logs"]
    warning_expr = warning_panel["targets"][0]["expr"]
    assert warning_panel["timeFrom"] == "1h"
    assert '{job="bioetl"}' in warning_expr
    assert '{job="bioetl", level="warning"}' not in warning_expr
    assert "| json" in warning_expr
    assert '__error__=""' in warning_expr
    assert '| pipeline=~"$pipeline"' in warning_expr
    assert '| level="warning"' in warning_expr

    top_warning_panel = panels["Inspect Top Warning Events by Event / Logger / Range"]
    top_warning_expr = top_warning_panel["targets"][0]["expr"]
    assert top_warning_panel["timeFrom"] == "1h"
    assert '{job="bioetl"}' in top_warning_expr
    assert '{job="bioetl", level="warning"}' not in top_warning_expr
    assert '| pipeline=~"$pipeline"' in top_warning_expr
    assert "count_over_time(" in top_warning_expr
    assert "sum by (event, logger)" in top_warning_expr
    assert "sum by (message)" not in top_warning_expr
    assert "topk(10" in top_warning_expr
    assert "[1h]" in top_warning_expr
    assert "$__range" not in top_warning_expr
    assert top_warning_panel["type"] == "table"

    unstructured_panel = panels["Inspect GLOBAL Unstructured Logs"]
    unstructured_expr = unstructured_panel["targets"][0]["expr"]
    assert unstructured_panel["timeFrom"] == "1h"
    assert '{job="bioetl"}' in unstructured_expr
    assert "| json" in unstructured_expr
    assert '__error__!=""' in unstructured_expr
    assert "{{.__error__}}" in unstructured_expr
    assert "{{__error__}}" not in unstructured_expr
    assert "__line__" not in unstructured_expr


def test_runtime_loki_panel_fixtures_cover_warning_and_malformed_paths() -> None:
    fixture_path = Path("tests/fixtures/grafana/loki_runtime_panel_events.jsonl")
    fixtures = [
        json.loads(line)
        for line in fixture_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    warning = next(item for item in fixtures if item["kind"] == "warning")
    malformed = next(item for item in fixtures if item["kind"] == "malformed")
    empty = next(item for item in fixtures if item["kind"] == "empty")
    assert warning["expected_panel_ids"] == [250, 257]
    assert set(warning["line"]) >= {"pipeline", "level", "event", "logger"}
    assert warning["line"]["pipeline"] == "chembl_activity"
    assert warning["line"]["level"] == "warning"
    assert set(warning["panel_results"]) == {"250", "257"}
    warning_stream = warning["panel_results"]["250"]
    assert warning_stream["resultType"] == "streams"
    assert warning_stream["result"][0]["stream"]["event"] == warning["line"]["event"]
    assert (
        json.loads(warning_stream["result"][0]["values"][0][1])["event"]
        == warning["line"]["event"]
    )
    warning_vector = warning["panel_results"]["257"]
    assert warning_vector["resultType"] == "vector"
    assert warning_vector["result"][0]["metric"]["event"] == warning["line"]["event"]
    assert warning_vector["result"][0]["value"][1] == "1"
    assert malformed["expected_panel_ids"] == [251]
    assert set(malformed["panel_results"]) == {"251"}
    with pytest.raises(json.JSONDecodeError):
        json.loads(malformed["line"])
    malformed_stream = malformed["panel_results"]["251"]
    assert malformed_stream["resultType"] == "streams"
    assert malformed_stream["result"][0]["values"][0][1] == "JSONParserErr"
    assert empty["expected_panel_ids"] == [250, 251, 257]
    assert empty["line"] is None
    assert set(empty["panel_results"]) == {"250", "251", "257"}
    assert {
        panel_id: panel_result["resultType"]
        for panel_id, panel_result in empty["panel_results"].items()
    } == {"250": "streams", "251": "streams", "257": "vector"}
    assert all(
        panel_result["result"] == [] for panel_result in empty["panel_results"].values()
    )


def test_runtime_dashboard_describes_tracing_optional_mode() -> None:
    """Runtime dashboard should keep tracing guidance in dashboard/row metadata."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    description = dashboard.get("description", "")
    assert "Prometheus-first" in description
    assert "optional tracing profile" in description

    note_panel = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title") == "Review Diagnostic Scope Note"
        ),
        None,
    )
    assert note_panel is None, (
        "Runtime tracing guidance must not consume first-screen panel space"
    )

    tracing_row = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title")
            == "Tracing-only Log Hygiene (requires optional tracing profile)"
        ),
        None,
    )
    assert tracing_row is not None, (
        "Runtime dashboard must expose optional tracing diagnostics as a collapsed row"
    )
    assert tracing_row.get("collapsed") is True


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

    checkpoint_panel = next(
        (panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 892),
        None,
    )
    assert checkpoint_panel is not None
    assert checkpoint_panel.get("datasource") == "Quarantine Explorer"
    target = checkpoint_panel.get("targets", [])[0]
    assert target.get("parser") == "backend"
    assert (
        str(target.get("url", ""))
        == "/ops/control-plane/checkpoint-freshness?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}"
    )


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
            if item.get("title") == "Monitor: Gold Strict Validation Failures"
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


def test_runtime_pipeline_errors_panel_uses_runtime_error_metric_and_selected_time_range() -> (
    None
):
    """Runtime error-rate panel must use shipped runtime errors over its fixed window."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Runtime Error Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Runtime Error Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Runtime Error Rate must use bioetl_errors_total"
    )
    assert any("[30m]" in expr for expr in expressions), (
        "Runtime Error Rate must use the shipped 30-minute window"
    )
    assert any(">= 20" in expr for expr in expressions), (
        "Runtime Error Rate must preserve the shipped Bronze denominator gate"
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
            if item.get("title") == "Inspect Errors by Stage / Error Code / Range"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Inspect Errors by Stage / Error Code / Range' not found"
    )

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, (
        "Panel 'Inspect Errors by Stage / Error Code / Range' must define a query target"
    )
    expressions = [
        target.get("expr", "")
        for target in targets
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Inspect Errors by Stage / Error Code / Range must use bioetl_errors_total"
    )
    assert any(
        "by(stage, error_code)" in expr or "by (stage, error_code)" in expr
        for expr in expressions
    ), "Inspect Errors by Stage / Error Code / Range must group by stage and error_code"
    assert any("[$__range]" in expr for expr in expressions), (
        "Inspect Errors by Stage / Error Code / Range must use the selected Grafana time range"
    )
    assert all(target.get("instant") is True for target in targets), (
        "Inspect Errors by Stage / Error Code / Range must use instant Prometheus queries"
    )


@pytest.mark.parametrize(
    ("panel_title", "expected_snippet"),
    [
        ("Monitor Healthy Checks (Selected Range)", "[$__range]"),
        ("Monitor Degraded Checks (Selected Range)", "[$__range]"),
        ("Track Provider Failure Rate (Selected Range)", "[$__range]"),
        ("Track Health Checks Total (Selected Range)", "[$__range]"),
        ("Inspect Adapter Request Latency by Endpoint (p95)", "[$__interval]"),
        ("Inspect Rate Limit Errors by Method", "[$__interval]"),
        ("Inspect Network Timeout Errors by Method", "[$__interval]"),
        ("Track Rate Limiter Wait by Provider (p95)", "[$__interval]"),
        ("Monitor Minimum Rate Limiter Tokens Available", "[$__range]"),
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
        "Monitor Cross-Scope Adapter Circuit Breaker State (max)",
        "Track Cross-Scope Adapter Circuit Breaker Trips",
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
            "Track Pipeline Phase Duration p50/p95/p99",
            "[$__rate_interval]",
        ),
        (
            "bioetl-runtime.json",
            "Track Pipeline Duration p50/p95/p99",
            "[$__rate_interval]",
        ),
        (
            "bioetl-runtime.json",
            "Track GLOBAL Shutdown Initiated by Reason / Interval",
            "[$__interval]",
        ),
        (
            "bioetl-runtime.json",
            "Track GLOBAL Shutdown Completed by Reason / Interval",
            "[$__interval]",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track: GLOBAL Audit Write Outcomes",
            "[$__interval]",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track: GLOBAL Audit Query Outcomes",
            "[$__interval]",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track: GLOBAL Audit Write Latency p50/p95/p99",
            "[$__range]",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track: GLOBAL Audit Query Latency p50/p95/p99",
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
        ("bioetl-overview-v2.json", "Historical Failures"),
        ("bioetl-overview-v2.json", "Recent Terminal Runs"),
        ("bioetl-control-plane-v1.json", "Monitor: GLOBAL Control-Plane Read Failures"),
        (
            "bioetl-control-plane-v1.json",
            "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
        ),
        ("bioetl-dq-v2.json", "Track: Records Quarantined in Range"),
        ("bioetl-dq-v2.json", "Track: Silver Validation Failures in Range"),
        ("bioetl-dq-v2.json", "Inspect: Quarantine by Error Type"),
        ("bioetl-dq-v2.json", "Monitor: Silver Validation Failures"),
        ("bioetl-runtime.json", "Track Records by Stage / Run Type / Range"),
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
        ("Runtime Blockers", ["bioetl_runtime_current_blocker_reason"]),
        (
            "Monitor Runtime Blockers",
            [
                "bioetl_runtime_current_blocker_reason",
                "bioetl_runtime_current_status",
            ],
        ),
    ],
)
def test_runtime_alert_condition_panels_use_recording_rules(
    panel_title: str, expected_recording_metrics: list[str]
) -> None:
    """Runtime blocker panels should consume shipped recording-rule metrics."""
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


def test_runtime_tracing_row_orders_log_hygiene_panels() -> None:
    """Runtime tracing row should keep log-hygiene panels in canonical order."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    tracing_row = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("type") == "row"
            and panel.get("title")
            == "Tracing-only Log Hygiene (requires optional tracing profile)"
        ),
        None,
    )
    assert tracing_row is not None, "Runtime tracing row not found"
    nested = get_row_child_panels(
        dashboard, "Tracing-only Log Hygiene (requires optional tracing profile)"
    )
    titles = [panel.get("title") for panel in nested]
    expected_sequence = [
        "Inspect Warning Logs",
        "Inspect GLOBAL Unstructured Logs",
        "Inspect Top Warning Events by Event / Logger / Range",
        "Track GLOBAL Log Hygiene Trend",
    ]
    for title in expected_sequence:
        assert title in titles, f"Runtime tracing row missing panel '{title}'"

    indices = [titles.index(title) for title in expected_sequence]
    assert indices == sorted(indices), (
        "Runtime tracing row log-hygiene panels must appear in the canonical order"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-control-plane-v1.json", "Track: Lineage Fragment Outcomes"),
        ("bioetl-dq-v2.json", "Track: DQ Check Duration (p95)"),
        ("bioetl-dq-v2.json", "Track: Anomalies Detected"),
        ("bioetl-runtime.json", "Track Records by Stage / Interval"),
        ("bioetl-runtime.json", "Track GLOBAL Log Hygiene Trend"),
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
            "bioetl-control-plane-v1.json",
            "Track: Checkpoint Compatibility Outcomes",
            'label_replace(vector(0), "disposition", "no_events", "", "")',
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
