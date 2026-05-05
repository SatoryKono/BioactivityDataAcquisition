"""Integration timing and runtime assertion tests for Grafana dashboard contracts."""

import re
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


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
        ("bioetl-overview-v2.json", "Historical Failures (range evidence)"),
        ("bioetl-overview-v2.json", "Recent terminal runs (range evidence)"),
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
        ("bioetl-runtime.json", "Errors by Stage / Error Code / Range"),
        ("bioetl-runtime.json", "Records by Stage / Run Type / Range"),
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


def test_runtime_first_action_row_precedes_condition_cards_in_order() -> None:
    """Runtime Escalate row should expose alert condition cards in expected order."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    escalate_row = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("type") == "row"
            and panel.get("title") == "Escalate (collapsed)"
        ),
        None,
    )
    assert escalate_row is not None, "Runtime Escalate row not found"
    nested = escalate_row.get("panels", [])
    titles = [panel.get("title") for panel in nested]
    expected_sequence = [
        "Pipeline Alert Conditions",
        "DQ Alert Conditions",
        "Control-plane Alert Conditions",
        "GLOBAL Provider Alert Conditions",
        "Freshness Alert Conditions",
        "No-Records Runs",
        "Memory Pressure Active",
    ]
    for title in expected_sequence:
        assert title in titles, f"Runtime Escalate row missing panel '{title}'"

    indices = [titles.index(title) for title in expected_sequence]
    assert indices == sorted(indices), (
        "Runtime Escalate row alert condition panels must appear in the expected order"
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


def test_overview_current_panels_stay_out_of_selected_range_semantics() -> None:
    """Overview L0/L1 current-answer panels must not use $__range windows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "System Status",
        "Next Action",
        "L0 Inputs",
        "Runtime Blockers Current",
        "DQ Status Current",
        "Gold Lifecycle Current",
        "Control Plane Current",
        "Provider GLOBAL Scope",
        "Workflow Selected Scope",
        "Workflow GLOBAL Scope",
    ):
        panel = panels.get(panel_title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "$__range" not in expr


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
