"""Integration tests for Grafana dashboard configurations.

Ensures that dashboards are synchronized with the application metrics
and follow the project's observability standards.
"""

import io
import json
import logging
from collections import Counter
from functools import cache
from pathlib import Path
import re
from urllib.parse import unquote

import pytest

# Import metrics module to get all defined metric names
from bioetl.infrastructure.observability import metrics
from bioetl.infrastructure.observability.logging_config import configure_logging
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger


@cache
def get_all_valid_metric_names() -> set[str]:
    """Extract all valid Prometheus metric names including suffixes for Histograms."""
    base_names = set()
    all_valid_names = set()

    for item_name in dir(metrics):
        item = getattr(metrics, item_name)
        if hasattr(item, "_name"):
            base_name = item._name
            base_names.add(base_name)
            all_valid_names.add(base_name)

            # Histograms and Summaries have auto-generated suffixes
            # We check the type by looking at the class name or internal structure
            class_name = type(item).__name__

            # Prometheus client auto-creates _created timestamp for all metric types
            all_valid_names.add(f"{base_name}_created")

            if "Histogram" in class_name or "Summary" in class_name:
                all_valid_names.add(f"{base_name}_bucket")
                all_valid_names.add(f"{base_name}_sum")
                all_valid_names.add(f"{base_name}_count")
            elif "Counter" in class_name:
                all_valid_names.add(
                    f"{base_name}_total"
                )  # Prometheus client often adds _total
                all_valid_names.add(
                    f"{base_name}_created"
                )  # Prometheus auto-creates _created timestamp

            # All metric types can have a _created suffix (OpenMetrics)
            all_valid_names.add(f"{base_name}_created")

    return all_valid_names


@cache
def get_dashboard_files() -> tuple[Path, ...]:
    """Get all Grafana dashboard JSON files."""
    dashboard_dir = Path("grafana/dashboards")
    return tuple(dashboard_dir.glob("*.json"))


@cache
def load_dashboard(dashboard_path: Path) -> dict:
    """Load dashboard JSON."""
    with open(dashboard_path, encoding="utf-8-sig") as f:
        return json.load(f)


def get_dashboard_panels(dashboard: dict) -> list[dict]:
    """Get all panels, including nested row panels."""
    panels = list(dashboard.get("panels", []))
    for row in dashboard.get("rows", []):
        panels.extend(row.get("panels", []))
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


def _collect_dashboard_links(dashboard: dict) -> list[dict]:
    """Collect top-level dashboard links and panel data links."""
    links = list(dashboard.get("links", []))
    for panel in get_dashboard_panels(dashboard):
        options = panel.get("options", {})
        links.extend(options.get("dataLinks", []))
    return links


def _emit_sample_structured_log(*, pipeline: str, provider: str) -> str:
    """Emit one JSON log line through the shipped structlog pipeline."""
    configure_logging(json_format=True, force=True)
    stream = io.StringIO()
    root = logging.getLogger()
    for handler in root.handlers:
        try:
            handler.setStream(stream)
        except AttributeError:
            continue

    logger = UnifiedLogger(
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

            # Regex to find potential bioetl metric names
            # Matches strings starting with bioetl_ and containing letters, numbers, underscores
            found_metrics = re.findall(r"(bioetl_[a-z0-9_]+)", query)
            for m in found_metrics:
                # Basic check: is this exact name or base name valid?
                if m not in valid_metrics:
                    # Also check without common suffixes
                    base = re.sub(r"(_total|_bucket|_sum|_count|_created)$", "", m)
                    if base not in valid_metrics:
                        errors.append(
                            f"Panel '{panel.get('title')}' uses unknown metric: {m}"
                        )

    assert not errors, f"Metric mismatch in {dashboard_path.name}:\n" + "\n".join(
        errors
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_has_required_variables(dashboard_path):
    """Check dashboard variables match the current contract."""
    expected_vars_by_dashboard = {
        "bioetl-overview-v2.json": {"pipeline", "run_type"},
        "bioetl-dq-v2.json": {"pipeline", "run_type"},
        "bioetl-runtime.json": {"pipeline", "run_type"},
        "bioetl-provider-health-v2.json": {"provider"},
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

    assert "run_id" not in variable_map, (
        f"Dashboard {dashboard_path.name} must not define deprecated 'run_id' variable"
    )

    if dashboard_path.name == "bioetl-provider-health-v2.json":
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
        assert "pipeline" not in variable_map, (
            f"Dashboard {dashboard_path.name} must not expose misleading 'pipeline' variable"
        )
    else:
        pipeline_var = variable_map.get("pipeline")
        assert pipeline_var is not None, (
            f"Dashboard {dashboard_path.name} must define 'pipeline' variable"
        )
        pipeline_query = pipeline_var.get("query", {})
        pipeline_query_text = (
            pipeline_query.get("query", "") if isinstance(pipeline_query, dict) else ""
        )
        assert "bioetl_records_processed_total" in pipeline_query_text, (
            f"Dashboard {dashboard_path.name} 'pipeline' query must use "
            "bioetl_records_processed_total"
        )
        run_type_var = variable_map.get("run_type")
        assert run_type_var is not None, (
            f"Dashboard {dashboard_path.name} must define 'run_type' variable"
        )
        run_type_query = run_type_var.get("query", {})
        run_type_query_text = (
            run_type_query.get("query", "") if isinstance(run_type_query, dict) else ""
        )
        assert "bioetl_records_processed_total" in run_type_query_text, (
            f"Dashboard {dashboard_path.name} 'run_type' query must use "
            "bioetl_records_processed_total"
        )
        assert "run_type" in run_type_query_text, (
            f"Dashboard {dashboard_path.name} 'run_type' query must select run_type label"
        )


def test_summary_queries_use_zero_fallbacks() -> None:
    """Runtime/provider summary panels should show zero instead of no-data."""
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Manifest Write Failures": "or vector(0)",
            "Ledger Append Failures": "or vector(0)",
            "Checkpoint Incompatibilities": "or vector(0)",
            "Lineage Refs Missing": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
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
            "Silver Filter Rejects": "or vector(0)",
            "Log Hygiene Trend": 'label_replace(vector(0), "series",',
        },
        "bioetl-provider-health-v2.json": {
            "Healthy Checks": "or vector(0)",
            "Degraded Checks": "or vector(0)",
            "Provider Failure Rate": "or vector(0)",
            "Health Checks Total": "or vector(0)",
        },
        "bioetl-dq-v2.json": {
            "Records Quarantined": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
            "Soft Threshold Exceeded": "or vector(0)",
            "Silver Validation Failures": "or vector(0)",
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
            "Pipeline Alert Conditions": "> bool 0",
            "DQ Alert Conditions": "> bool 0",
            "Control-plane Alert Conditions": "> bool 0",
            "Trace-enabled Runs": "round(",
            "Silver Filter Rejects": "round(",
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
    expected_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Processing Volume by Stage": "increase(",
            "Stage Distribution in Range": "increase(",
            "Pipeline Distribution in Range": "increase(",
            "Overall Yield (Selected Range)": "increase(",
        },
        "bioetl-dq-v2.json": {
            "Data Flow in Range: Bronze -> Silver -> Gold": "increase(",
            "Source Records in Range (Bronze)": "increase(",
            "Clean Records in Range (Gold)": "increase(",
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
                f"Panel {panel_title!r} in {dashboard_name} must use "
                f"{expected_snippet!r} rather than raw counter values"
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


def test_runtime_dashboard_contains_runtime_hygiene_and_alert_condition_metrics():
    """Ensure runtime dashboard stays anchored to log hygiene and alert-condition metrics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_records_processed_total",
        "bioetl_dq_soft_threshold_exceeded",
        "bioetl_dq_validation_failures_total",
        "bioetl_dq_anomaly_detected",
        "bioetl_silver_validation_failures_total",
        "bioetl_data_freshness_seconds",
        "bioetl_pipeline_health_check_passed",
        "bioetl_infrastructure_validated",
        "bioetl_pipeline_runs_total",
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
        "bioetl_traced_runs_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
        "bioetl_health_check_failures_total",
        "bioetl_health_check_degraded_total",
        "bioetl_health_check_success_total",
        "bioetl_data_source_retry_exhausted_total",
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


@pytest.mark.parametrize(
    ("panel_title", "expected_snippet"),
    [
        ("Healthy Checks", "[$__range]"),
        ("Degraded Checks", "[$__range]"),
        ("Provider Failure Rate", "[$__range]"),
        ("Health Checks Total", "[$__range]"),
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
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-overview-v2.json", "Manifest Write Failures"),
        ("bioetl-overview-v2.json", "Ledger Append Failures"),
        ("bioetl-overview-v2.json", "Checkpoint Incompatibilities"),
        ("bioetl-overview-v2.json", "Lineage Refs Missing"),
        ("bioetl-overview-v2.json", "Global Control-plane Lookup Failures"),
        ("bioetl-overview-v2.json", "Global Control-plane Lookup p95"),
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
        ("bioetl-runtime.json", "Global Control-plane Lookup p95"),
        ("bioetl-runtime.json", "Top Warning Events"),
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
    ("panel_title", "expected_snippets"),
    [
        (
            "Pipeline Alert Conditions",
            ["[15m]", 'component="data_source"', 'status="failed"'],
        ),
        (
            "DQ Alert Conditions",
            ["[15m]", "[30m]", 'severity="critical"'],
        ),
        (
            "Control-plane Alert Conditions",
            ["[15m]", "[30m]", 'status="failed"'],
        ),
        (
            "Provider Alert Conditions",
            ["[15m]", "[1h]", "0.2"],
        ),
    ],
)
def test_runtime_alert_condition_panels_use_rule_windows(
    panel_title: str, expected_snippets: list[str]
) -> None:
    """Runtime rule-summary panels should mirror shipped alert windows."""
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
    for expected_snippet in expected_snippets:
        assert any(expected_snippet in expr for expr in expressions), (
            f"Panel '{panel_title}' must include {expected_snippet!r} to stay aligned "
            "with shipped alert-rule windows"
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
        "bioetl-provider-health-v2.json",
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
        assert any("/explore" in url and "loki" in url for url in urls), (
            f"{dashboard_name} must point logs drilldown to Loki Explore"
        )
        assert any("/explore" in url and "tempo" in url for url in urls), (
            f"{dashboard_name} must point traces drilldown to Tempo Explore"
        )
        assert any("/explore?left=" in url and "loki" in url for url in urls), (
            f"{dashboard_name} Loki drilldown must use a Loki Explore payload"
        )


def test_explore_links_decode_to_valid_queries() -> None:
    """Explore links should decode to valid Loki/Tempo query payloads."""
    expectations = {
        "bioetl-overview-v2.json": {
            "tempo_terms": ('span."bioetl.pipeline"', 'span."bioetl.run_type"'),
        },
        "bioetl-dq-v2.json": {
            "tempo_terms": ('span."bioetl.pipeline"', 'span."bioetl.run_type"'),
        },
        "bioetl-runtime.json": {
            "tempo_terms": ('span."bioetl.pipeline"', 'span."bioetl.run_type"'),
        },
        "bioetl-provider-health-v2.json": {
            "tempo_terms": ('span."bioetl.provider"',),
        },
    }

    for dashboard_name, config in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            if "/explore?left=" not in url:
                continue
            encoded = url.split("left=", 1)[1]
            payload = json.loads(unquote(encoded))
            assert payload["datasource"] in {"loki", "tempo"}
            assert payload["range"]["from"] == "${__from}"
            assert payload["range"]["to"] == "${__to}"
            if payload["datasource"] == "loki":
                expr = payload["queries"][0]["expr"]
                assert expr == '{job="bioetl"}'
                continue

            assert payload["queries"][0]["queryType"] == "traceqlSearch"
            query = payload["queries"][0]["query"]
            assert query != "{}", (
                f"{dashboard_name} Tempo drilldown must be scoped to the current dashboard selection"
            )
            for term in config["tempo_terms"]:
                assert term in query, (
                    f"{dashboard_name} Tempo drilldown must include {term!r}"
                )


def test_tempo_drilldown_uses_contextual_traceql_filters() -> None:
    """Tempo drilldown should preserve current dashboard scope via TraceQL."""
    expectations = {
        "bioetl-overview-v2.json": ("${pipeline:regex}", "${run_type:regex}"),
        "bioetl-dq-v2.json": ("${pipeline:regex}", "${run_type:regex}"),
        "bioetl-runtime.json": ("${pipeline:regex}", "${run_type:regex}"),
        "bioetl-provider-health-v2.json": ("${provider:regex}",),
    }

    for dashboard_name, fragments in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        tempo_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if "/explore?left=" in link.get("url", "")
            and "tempo" in link.get("url", "")
        ]
        assert tempo_links, (
            f"{dashboard_name} must expose at least one Tempo drilldown link"
        )

        for link in tempo_links:
            payload = json.loads(unquote(link["url"].split("left=", 1)[1]))
            query = payload["queries"][0]["query"]
            for fragment in fragments:
                assert fragment in query, (
                    f"{dashboard_name} Tempo drilldown must preserve {fragment} in TraceQL"
                )


def test_explore_drilldown_titles_disclose_tracing_profile_dependency() -> None:
    """Loki/Tempo drilldown titles should warn that tracing profile is required."""
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            title = link.get("title", "")
            if "/explore" not in url or ("loki" not in url and "tempo" not in url):
                continue
            assert "tracing" in title.lower(), (
                f"{dashboard_name} Explore drilldown title must disclose tracing profile dependency"
            )


def test_loki_drilldown_uses_safe_generic_entrypoint() -> None:
    """Loki drilldown should avoid broken variable interpolation inside Explore."""
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
        "bioetl-provider-health-v2.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        loki_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if "/explore?left=" in link.get("url", "") and "loki" in link.get("url", "")
        ]
        assert loki_links, (
            f"{dashboard_name} must expose at least one Loki drilldown link"
        )

        for link in loki_links:
            payload = json.loads(unquote(link["url"].split("left=", 1)[1]))
            expr = payload["queries"][0]["expr"]
            assert expr == '{job="bioetl"}'
