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
        assert "bioetl_health_check_success_total" in provider_query_text, (
            f"Dashboard {dashboard_path.name} 'provider' query must use "
            "bioetl_health_check_success_total"
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


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Data Quality Score"),
    ],
)
def test_quality_ratio_uses_clamp_min(dashboard_file, panel_title):
    """Ensure quality ratio panels are protected from division by zero."""
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
    assert any("clamp_min(" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use clamp_min for bronze denominator"
    )
    assert any('stage="quarantined"' in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must include quarantined records"
    )


def test_dq_dashboard_contains_core_dq_metrics():
    """Ensure DQ dashboard visualizes key DQ metrics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_dq_validation_score",
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
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_fragments_emitted_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


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
        "bioetl_dq_soft_threshold_exceeded",
        "bioetl_dq_validation_failures_total",
        "bioetl_dq_anomaly_detected",
        "bioetl_silver_validation_failures_total",
        "bioetl_data_freshness_seconds",
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
        "bioetl_health_check_failures_total",
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
    assert any("__error__!=\"\"" in expr for expr in loki_exprs), (
        "Runtime dashboard must expose unstructured-log hygiene signal"
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
        "bioetl-overview-v2.json": ("pipeline", "loki"),
        "bioetl-dq-v2.json": ("pipeline", "loki"),
        "bioetl-runtime.json": ("pipeline", "loki"),
        "bioetl-provider-health-v2.json": ("provider", "loki"),
    }

    for dashboard_name, (token, datasource_uid) in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            if "/explore?left=" not in url or datasource_uid not in url:
                continue
            encoded = url.split("left=", 1)[1]
            payload = json.loads(unquote(encoded))
            assert payload["datasource"] in {"loki", "tempo"}
            assert payload["range"]["from"] == "${__from}"
            assert payload["range"]["to"] == "${__to}"
            if payload["datasource"] == "loki":
                expr = payload["queries"][0]["expr"]
                assert expr == '{job="bioetl"}'

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
        assert loki_links, f"{dashboard_name} must expose at least one Loki drilldown link"

        for link in loki_links:
            payload = json.loads(unquote(link["url"].split("left=", 1)[1]))
            expr = payload["queries"][0]["expr"]
            assert expr == '{job="bioetl"}'
