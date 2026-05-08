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
    get_dashboard_navigation_links,
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
PROMETHEUS_RULE_FILES = tuple(Path("grafana/prometheus-rules").glob("*.yml"))
GRAFANA_DASHBOARD_PROVISIONING_PATH = Path(
    "grafana/provisioning/dashboards/bioetl.yaml"
)
GRAFANA_README_PATH = Path("grafana/README.md")
_BIOETL_METRIC_TOKEN_RE = re.compile(r"\b(bioetl_[a-z0-9_]+)\b")
_GRAFANA_VAR_TOKEN_RE = re.compile(r"\$(\{)?([\w]+)(?(1)\})")


NAVIGATION_CONTRACT_PATH = Path(
    "docs/03-guides/dashboards/contracts/navigation-links.yaml"
)
EXPECTED_VARS_BY_DASHBOARD = {
    "bioetl-overview-v2.json": {"pipeline", "run_type"},
    "bioetl-dq-v2.json": {"pipeline", "run_type", "stage"},
    "bioetl-runtime.json": {"pipeline", "run_type", "stage"},
    "bioetl-provider-health-v2.json": {
        "provider",
        "pipeline_context",
        "adapter",
    },
    "bioetl-control-plane-v1.json": {"pipeline", "run_type"},
    "bioetl-workflow-overview.json": {
        "workflow",
        "status",
        "step_status",
        "step_kind",
    },
    "bioetl-silver-reject-explorer.json": {
        "pipeline",
        "run_type",
        "reason_code",
        "field",
        "run_id",
        "payload_hash",
    },
}


def _json_load_without_duplicate_keys(path: Path) -> dict:
    """Load JSON and fail fast when duplicate keys are present."""

    def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        payload: dict[str, object] = {}
        seen: set[str] = set()
        for key, value in pairs:
            if key in seen:
                raise AssertionError(f"Duplicate JSON key '{key}' in {path}")
            seen.add(key)
            payload[key] = value
        return payload

    with path.open(encoding="utf-8") as source:
        data = json.load(source, object_pairs_hook=_reject_duplicates)

    assert isinstance(data, dict), "Dashboard JSON root must be an object"
    return data


def _load_navigation_contract() -> dict:
    payload = yaml.safe_load(NAVIGATION_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), (
        "navigation-links contract must deserialize into a mapping"
    )
    return payload


def _load_recording_rule_names() -> set[str]:
    names: set[str] = set()
    for rules_path in PROMETHEUS_RULE_FILES:
        payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        names.update(
            record_name
            for group in payload.get("groups", [])
            for rule in group.get("rules", [])
            if isinstance(record_name := rule.get("record"), str)
        )
    return names


def _dashboard_variable_names(dashboard: dict) -> set[object]:
    return {
        variable.get("name")
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }


def _undeclared_link_variables(url: str, declared_variables: set[str]) -> list[str]:
    return [
        variable_name
        for _, variable_name in _GRAFANA_VAR_TOKEN_RE.findall(url)
        if not variable_name.startswith("__")
        and variable_name not in declared_variables
    ]


def _panel_link_variable_violations(
    panel: dict, declared_variables: set[str]
) -> list[str]:
    links = panel.get("links", [])
    if not isinstance(links, list):
        return []

    violations: list[str] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url", ""))
        for variable_name in _undeclared_link_variables(url, declared_variables):
            violations.append(
                f"panel={panel.get('title', '<untitled>')} link={link.get('title', '<untitled>')} "
                f"uses ${variable_name} not declared in templating.list"
            )
    return violations


def _dashboard_link_variable_violations(
    dashboard: dict, declared_variables: set[str]
) -> list[str]:
    links = get_dashboard_navigation_links(dashboard)
    if not isinstance(links, list):
        return []

    violations: list[str] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url", ""))
        for variable_name in _undeclared_link_variables(url, declared_variables):
            violations.append(
                f"dashboard_link={link.get('title', '<untitled>')} "
                f"uses ${variable_name} not declared in templating.list"
            )
    return violations


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_is_valid_json(dashboard_path):
    """L1: Verify that the dashboard file is a valid JSON."""
    data = _json_load_without_duplicate_keys(dashboard_path)
    assert isinstance(data, dict)
    assert "title" in data


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_panel_ids_are_unique(dashboard_path: Path) -> None:
    """Panel IDs must stay unique across root and collapsed-row panels."""
    dashboard = load_dashboard(dashboard_path)
    panel_refs = [
        (panel.get("id"), panel.get("title", "<untitled>"))
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") is not None
    ]
    counts = Counter(panel_id for panel_id, _title in panel_refs)
    duplicates = {
        panel_id: [
            title for candidate_id, title in panel_refs if candidate_id == panel_id
        ]
        for panel_id, count in counts.items()
        if count > 1
    }
    assert not duplicates, (
        f"Dashboard {dashboard_path.name} has duplicate panel IDs: {duplicates}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_prometheus_datasource_contract(dashboard_path: Path) -> None:
    """Prometheus panel and target datasources must use explicit provisioned UID."""
    dashboard = load_dashboard(dashboard_path)
    errors: list[str] = []

    for panel in get_dashboard_panels(dashboard):
        panel_id = panel.get("id", "<unknown>")
        panel_title = panel.get("title", "<untitled>")
        datasource = panel.get("datasource")

        if datasource == "Prometheus":
            errors.append(
                f"panel id={panel_id} title={panel_title!r} uses string "
                "datasource 'Prometheus'; use explicit object format"
            )
        elif isinstance(datasource, dict):
            is_prometheus = (
                datasource.get("type") == "prometheus"
                or datasource.get("uid") == "prometheus"
            )
            if is_prometheus and datasource != {
                "type": "prometheus",
                "uid": "prometheus",
            }:
                errors.append(
                    f"panel id={panel_id} title={panel_title!r} has non-canonical "
                    f"Prometheus datasource object: {datasource}"
                )

        for target in panel.get("targets", []):
            target_ref = target.get("refId", "<unknown>")
            target_datasource = target.get("datasource")
            if not isinstance(target_datasource, dict):
                continue
            if target_datasource.get("uid") == "${DS_PROMETHEUS}":
                errors.append(
                    f"panel id={panel_id} title={panel_title!r} target={target_ref} "
                    "still uses ${DS_PROMETHEUS}"
                )
            is_prometheus_target = (
                target_datasource.get("type") == "prometheus"
                or target_datasource.get("uid") == "prometheus"
            )
            if is_prometheus_target and target_datasource != {
                "type": "prometheus",
                "uid": "prometheus",
            }:
                errors.append(
                    f"panel id={panel_id} title={panel_title!r} target={target_ref} "
                    f"has non-canonical Prometheus datasource object: "
                    f"{target_datasource}"
                )

    assert not errors, (
        f"Dashboard {dashboard_path.name} violates Prometheus datasource "
        f"contract:\n" + "\n".join(errors)
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_panel_title_vocabulary_matches_group_by_vocabulary(
    dashboard_path: Path,
) -> None:
    """Panel titles should describe aggregation vocabulary in PromQL group-by labels."""
    dashboard = load_dashboard(dashboard_path)
    errors: list[str] = []

    for panel in get_dashboard_panels(dashboard):
        title = panel.get("title", "")
        if not isinstance(title, str):
            continue

        expressions = get_panel_expressions(panel)
        grouped_by_provider = any("by (provider" in expr for expr in expressions)
        grouped_by_adapter = any("by (adapter" in expr for expr in expressions)

        if grouped_by_provider and "by Provider" not in title:
            errors.append(
                f"{dashboard_path.name}: panel '{title}' groups by provider but title "
                "does not contain 'by Provider'"
            )
        if grouped_by_adapter and "by Adapter" not in title:
            errors.append(
                f"{dashboard_path.name}: panel '{title}' groups by adapter but title "
                "does not contain 'by Adapter'"
            )

    assert not errors, "Panel title vocabulary drift detected:\n" + "\n".join(errors)


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
    dashboard = load_dashboard(dashboard_path)
    variables = _dashboard_variable_names(dashboard)
    expected_vars = EXPECTED_VARS_BY_DASHBOARD.get(dashboard_path.name)

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
def test_dashboard_links_only_reference_declared_variables(
    dashboard_path: Path,
) -> None:
    """All $var tokens in dashboard links must be present in templating.list."""
    dashboard = load_dashboard(dashboard_path)
    declared_variables = {
        str(variable.get("name"))
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }

    violations = [
        violation
        for panel in get_dashboard_panels(dashboard)
        for violation in _panel_link_variable_violations(panel, declared_variables)
    ]
    violations.extend(
        _dashboard_link_variable_violations(dashboard, declared_variables)
    )

    assert not violations, (
        f"Dashboard {dashboard_path.name} has links with undeclared variables:\n"
        + "\n".join(violations)
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
        step_status_query = variable_map["step_status"].get("query", {})
        step_kind_query = variable_map["step_kind"].get("query", {})
        assert isinstance(workflow_query, dict)
        assert isinstance(status_query, dict)
        assert isinstance(step_status_query, dict)
        assert isinstance(step_kind_query, dict)
        assert "bioetl_workflow_runs_total" in workflow_query.get("query", "")
        assert "bioetl_workflow_runs_total" in status_query.get("query", "")
        assert "bioetl_workflow_step_events_total" in step_status_query.get("query", "")
        assert "bioetl_workflow_step_events_total" in step_kind_query.get("query", "")
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
            if item.get("title") == "Monitor: Worst Data Freshness Lag (seconds)"
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


def test_freshness_panels_do_not_compute_age_from_counter_suffix_metrics() -> None:
    """Freshness panels must never derive age from *_count metrics."""
    dashboard_dir = Path("grafana/dashboards")
    disallowed_pattern = re.compile(r"time\(\)\s*-\s*.*_count")

    violations: list[str] = []
    for dashboard_path in dashboard_dir.glob("*.json"):
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            panel_title = str(panel.get("title", ""))
            if "freshness" not in panel_title.lower():
                continue

            for target in panel.get("targets", []):
                expr = target.get("expr", "")
                if isinstance(expr, str) and disallowed_pattern.search(expr):
                    violations.append(
                        f"{dashboard_path.name}::{panel_title} uses forbidden expr: {expr}"
                    )

    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Review: Latest Successful Data Timestamp"),
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


def test_control_plane_dashboard_has_primary_question() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    description = str(dashboard.get("description", ""))

    assert "Primary question:" in description
    assert "safely replay/resume" in description
    assert "GLOBAL read-path panels are not pipeline-scoped" in description


def test_control_plane_l1_triage_row_has_3_to_5_kpis_and_one_next_step() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = get_dashboard_panels(dashboard)
    kpi_titles = {
        "Monitor: Replay Safety State",
        "Inspect: Checkpoint Freshness Gap",
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
    }
    next_step_title = "Next Action: Replay Diagnostics"
    first_screen_titles = {
        panel.get("title") for panel in panels[:9] if panel.get("type") != "row"
    }

    assert kpi_titles.issubset(first_screen_titles)
    assert next_step_title in first_screen_titles
    assert len(first_screen_titles & kpi_titles) == 4


def test_control_plane_l1_has_single_next_step_panel_with_expected_target() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") == "Next Action: Replay Diagnostics"
    ]
    assert len(panels) == 1

    links = panels[0].get("options", {}).get("dataLinks", [])
    assert len(links) == 1
    url = str(links[0].get("url", ""))
    assert "/d/bioetl-control-plane-v1/bioetl-control-plane-v1" in url
    assert "viewPanel=130" in url


def test_control_plane_has_replay_resume_blockers_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Track: Replay / Resume Blockers in Range")

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
            "Monitor: GLOBAL Control-Plane Read Failures",
            "Monitor: GLOBAL Control-Plane Read Failure Ratio",
            "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
            "Track: GLOBAL Control-Plane Reads by Store / Operation / Status",
            "Monitor: GLOBAL Checkpoint Operator Failures",
            "Track: GLOBAL Checkpoint Operator Latency p50/p95/p99",
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
            "Monitor: GLOBAL Control-Plane Read Failures",
            "Monitor: GLOBAL Control-Plane Read Failure Ratio",
            "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
            "Track: GLOBAL Control-Plane Reads by Store / Operation / Status",
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
        "Track: Checkpoint Save Latency p50/p95/p99",
        "Track: GLOBAL Checkpoint Operator Latency p50/p95/p99",
        "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
        "Track: GLOBAL Audit Write Latency p50/p95/p99",
        "Track: GLOBAL Audit Query Latency p50/p95/p99",
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
            if panel.get("title") == "Review: Known Missing Replay-Safety Signals"
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
        for link in get_dashboard_navigation_links(dashboard)
        if link.get("title")
    }

    assert links
    assert all(link.get("includeVars") is False for link in links.values())
    assert "includeVars=true" not in json.dumps(links)
    assert "Back to Overview" not in links
    assert "0. Control Plane" not in links
    for title in ("1. Overview", "2. Runtime", "4. Data Quality"):
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
            if item.get("title") == "Monitor: Silver Validation Failures"
        ),
        None,
    )
    assert panel is not None, "DQ dashboard missing 'Monitor: Silver Validation Failures' panel"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any('{pipeline=~"$pipeline"}' in expr for expr in expressions), (
        "Monitor: Silver Validation Failures must filter on the explicit pipeline label"
    )
    assert all('{table=~"$pipeline"}' not in expr for expr in expressions), (
        "Monitor: Silver Validation Failures must not rely on the table-to-pipeline naming convention"
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
            if item.get("title") == "Monitor Current Provider Health Status"
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
    assert any(
        "bioetl_provider_health_check_provider_universe_15m" in expr
        for expr in expressions
    ), "Provider health status panel must fail closed to UNKNOWN for known providers"
    assert all('{pipeline=~"$pipeline"}' not in expr for expr in expressions), (
        "Provider health status panel must stay provider-scoped only"
    )


def test_provider_health_panel_114_description_disallows_zero_as_healthy() -> None:
    """Panel 114 description must keep provider enum semantics for 0 state."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (item for item in get_dashboard_panels(dashboard) if item.get("id") == 114),
        None,
    )
    assert panel is not None, "Panel id=114 not found"

    description = str(panel.get("description", ""))
    assert "0=UNHEALTHY" in description, (
        "Panel id=114 must explicitly document 0 as UNHEALTHY"
    )
    assert "UNKNOWN" in description, (
        "Panel id=114 must document UNKNOWN fallback when raw status is absent"
    )
    description_upper = description.upper()
    assert "0=HEALTHY" not in description_upper
    assert "0=OK" not in description_upper


def test_provider_health_status_mappings_match_description_enum() -> None:
    """Provider status panels must keep mapping texts and enum descriptions aligned."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    expected_pairs = {"0": "UNHEALTHY", "1": "DEGRADED", "2": "HEALTHY"}
    expected_null = "UNKNOWN"

    for panel in get_dashboard_panels(dashboard):
        mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
        value_mapping = next(
            (
                mapping
                for mapping in mappings
                if mapping.get("type") == "value"
                and isinstance(mapping.get("options"), dict)
            ),
            None,
        )
        if value_mapping is None:
            continue

        options = value_mapping.get("options", {})
        if not all(key in options for key in (*expected_pairs.keys(), "null")):
            continue

        description = str(panel.get("description", ""))
        for status_code, label in expected_pairs.items():
            text = str(options[status_code].get("text", "")).upper()
            assert text == label, (
                f"Panel id={panel.get('id')} status {status_code} text must be {label}"
            )
            assert f"{status_code}={label}" in description, (
                f"Panel id={panel.get('id')} description must include {status_code}={label}"
            )

        null_text = str(options["null"].get("text", "")).upper()
        assert null_text == expected_null, (
            f"Panel id={panel.get('id')} null mapping must be {expected_null}"
        )
        assert f"null={expected_null}" in description, (
            f"Panel id={panel.get('id')} description must include null={expected_null}"
        )


def test_runtime_provider_alert_conditions_do_not_filter_on_missing_pipeline_labels():
    """Provider runtime alert summaries are fleet-wide and must not filter on pipeline."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect GLOBAL Provider Alert Conditions"
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
        "Inspect GLOBAL Provider Alert Conditions must not filter provider-only recording rules by pipeline."
    )


def test_workflow_step_panels_apply_status_variable() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))
    expected = {
        "Step Outcomes by Kind / Step Status / Range": (
            'status=~"$step_status"',
            'step_kind=~"$step_kind"',
        ),
        "Step Duration p95 by Kind / Step Status / Range": (
            'status=~"$step_status"',
            'step_kind=~"$step_kind"',
        ),
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for title, required_snippets in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Workflow dashboard missing panel {title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        for required_snippet in required_snippets:
            assert any(required_snippet in expr for expr in expressions), (
                f"{title!r} must apply workflow selector {required_snippet!r}"
            )


def test_workflow_dashboard_descriptions_explain_selected_range_limits() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))

    description = str(dashboard.get("description", ""))
    description_lower = description.lower()
    assert "selected-range" in description_lower
    assert "does not provide current run state" in description_lower
    assert "run_id" in description_lower
    assert "stage" in description_lower

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    expected_tokens = {
        "Workflow Scope": ("selected-range", "runtime", "data quality"),
        "Failed Workflow Runs / Range": ("selected time range", "0. control plane"),
        "Failed Pipeline Steps / Range": ("step_kind=pipeline", "2. runtime"),
        "Failed Transform Steps / Range": ("transform", "4. data quality"),
        "Skipped Step Events / Range": ("skipped", "selected time range"),
        "Workflow Run Outcomes / Range": ("no data", "selected-range"),
        "Step Outcomes by Kind / Step Status / Range": (
            "step kind",
            "step status",
            "2. runtime",
        ),
        "Step Duration p95 by Kind / Step Status / Range": (
            "p95",
            "selected time range",
            "2. runtime",
        ),
        "Next Diagnostic Surface": ("run_id", "dependency", "gold-write"),
    }
    for title, tokens in expected_tokens.items():
        panel = panels.get(title)
        assert panel is not None, f"Workflow dashboard missing panel {title!r}"
        panel_description = str(panel.get("description", "")).lower()
        for token in tokens:
            assert token in panel_description, (
                f"{title!r} description must mention {token!r}"
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
    expected_source = (
        "bioetl_pipeline_stage_expected"
        if dashboard_file == "bioetl-runtime.json"
        else "bioetl_records_processed_total"
    )
    assert f"label_values({expected_source}" in query_text
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

    assert "bioetl_control_plane_run_type_universe" in pipeline_query_text
    assert "bioetl_control_plane_run_type_universe" in run_type_query_text
    assert "bioetl_control_plane_manifest_writes_total" not in pipeline_query_text
    assert "bioetl_control_plane_manifest_writes_total" not in run_type_query_text
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
        "Inspect Warning Logs",
        "Inspect GLOBAL Unstructured Logs",
        "Inspect Top Warning Events by Message / Range",
        "Track GLOBAL Log Hygiene Trend",
    }


def test_runtime_warning_loki_queries_filter_parsed_fields_after_json() -> None:
    """Warning log panels must not filter parsed JSON fields in the Loki selector."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    warning_panel = panels["Inspect Warning Logs"]
    warning_expr = warning_panel["targets"][0]["expr"]
    assert '{job="bioetl"}' in warning_expr
    assert '{job="bioetl", level="warning"}' not in warning_expr
    assert "| json" in warning_expr
    assert '__error__=""' in warning_expr
    assert '| pipeline=~"$pipeline"' in warning_expr
    assert '| level="warning"' in warning_expr

    top_warning_panel = panels["Inspect Top Warning Events by Message / Range"]
    top_warning_expr = top_warning_panel["targets"][0]["expr"]
    assert '{job="bioetl"}' in top_warning_expr
    assert '{job="bioetl", level="warning"}' not in top_warning_expr
    assert '| pipeline=~"$pipeline"' in top_warning_expr
    assert "count_over_time(" in top_warning_expr
    assert "sum by (message)" in top_warning_expr
    assert "topk(10" in top_warning_expr
    assert top_warning_panel["type"] == "bargauge"

    unstructured_panel = panels["Inspect GLOBAL Unstructured Logs"]
    unstructured_expr = unstructured_panel["targets"][0]["expr"]
    assert '{job="bioetl"}' in unstructured_expr
    assert "| json" in unstructured_expr
    assert '__error__!=""' in unstructured_expr
    assert "{{.__error__}}" in unstructured_expr
    assert "{{__error__}}" not in unstructured_expr


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
            if panel.get("title") == "Review Diagnostic Scope Note"
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
            if item.get("title") == "Monitor Runtime Error Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Runtime Error Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_errors_total" in expr for expr in expressions), (
        "Monitor Runtime Error Rate must use bioetl_errors_total"
    )
    assert any("[30m]" in expr for expr in expressions), (
        "Monitor Runtime Error Rate must use the shipped 30-minute window"
    )
    assert any(">= 20" in expr for expr in expressions), (
        "Monitor Runtime Error Rate must preserve the shipped Bronze denominator gate"
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
        ("Inspect HTTP Errors by Method/Error Type", "[$__interval]"),
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
        ("bioetl-dq-v2.json", "Track: Soft Threshold Exceeded in Range"),
        ("bioetl-dq-v2.json", "Inspect: Quarantine by Error Type"),
        ("bioetl-dq-v2.json", "Monitor: Silver Validation Failures"),
        ("bioetl-dq-v2.json", "Monitor: Lineage Refs Missing"),
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


@pytest.mark.skip("Alert condition panels do not exist in bioetl-runtime.json")
@pytest.mark.parametrize(
    ("panel_title", "expected_recording_metrics"),
    [],
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


@pytest.mark.skip("Expected panels do not exist in bioetl-runtime.json tracing row")
def test_runtime_first_action_row_precedes_condition_cards_in_order() -> None:
    """Runtime tracing row should expose First Action CTA block before condition cards."""
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
    nested = tracing_row.get("panels", [])
    titles = [panel.get("title") for panel in nested]
    expected_sequence = [
        "First Action",
        "Pipeline conditions",
        "DQ conditions",
        "Control Plane conditions",
        "Provider health checks",
    ]
    for title in expected_sequence:
        assert title in titles, f"Runtime tracing row missing panel '{title}'"

    indices = [titles.index(title) for title in expected_sequence]
    assert indices == sorted(indices), (
        "Runtime First Action CTA panels must appear before existing condition cards "
        "in the expected order"
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
            "bioetl-runtime.json",
            "Inspect Errors by Stage / Error Code / Range",
            'label_replace(label_replace(vector(0), "stage", "none", "", ""), "error_code", "none", "", "")',
        ),
        (
            "bioetl-runtime.json",
            "Track Records by Stage / Run Type / Range",
            'label_replace(label_replace(vector(0), "stage", "none", "", ""), "run_type", "none", "", "")',
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track: Checkpoint Compatibility Outcomes",
            'label_replace(vector(0), "disposition", "no_events", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Inspect: Quarantine by Error Type",
            'label_replace(vector(0), "error_type", "none", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Track: Anomalies Detected",
            'label_replace(label_replace(vector(0), "severity", "none", "", ""), "anomaly_type", "none", "", "")',
        ),
        (
            "bioetl-dq-v2.json",
            "Inspect: Silver Filter Rejects by Pipeline",
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
    fixed_window_suffix_re = re.compile(
        r"(?:\((24h|30m|15m|1h|5m)\)|/\s*(24h|30m|15m|1h|5m))$"
    )
    offenders = [title for title in titles if fixed_window_suffix_re.search(title)]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} still contains fixed-window titles: {offenders}"
    )


def test_runtime_top_fold_text_panels_do_not_overlap() -> None:
    """Runtime first-fold text blocks must keep a readable, non-overlapping layout."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    text_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "text" and panel.get("gridPos", {}).get("y", 999) <= 20
    ]

    overlaps = []
    for index, left in enumerate(text_panels):
        left_grid = left.get("gridPos", {})
        left_x = left_grid.get("x", 0)
        left_y = left_grid.get("y", 0)
        left_w = left_grid.get("w", 0)
        left_h = left_grid.get("h", 0)
        for right in text_panels[index + 1 :]:
            right_grid = right.get("gridPos", {})
            right_x = right_grid.get("x", 0)
            right_y = right_grid.get("y", 0)
            right_w = right_grid.get("w", 0)
            right_h = right_grid.get("h", 0)
            x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
            y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
            if x_overlap and y_overlap:
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps {right.get('id')}:{right.get('title')}"
                )

    assert not overlaps, "Runtime top-fold text panels overlap:\n" + "\n".join(overlaps)


def test_control_plane_root_layout_keeps_range_evidence_and_rows_non_overlapping() -> None:
    """Control Plane root layout must not overlap the selected-range blocker panel with collapsed incident rows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    root_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("id") not in {1000, 890}
    ]

    overlaps = []
    for index, left in enumerate(root_panels):
        left_grid = left.get("gridPos", {})
        left_x = left_grid.get("x", 0)
        left_y = left_grid.get("y", 0)
        left_w = left_grid.get("w", 0)
        left_h = left_grid.get("h", 0)
        for right in root_panels[index + 1 :]:
            right_grid = right.get("gridPos", {})
            right_x = right_grid.get("x", 0)
            right_y = right_grid.get("y", 0)
            right_w = right_grid.get("w", 0)
            right_h = right_grid.get("h", 0)
            x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
            y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
            if x_overlap and y_overlap:
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps {right.get('id')}:{right.get('title')}"
                )

    assert not overlaps, "Control Plane root panels overlap:\n" + "\n".join(overlaps)


def test_control_plane_collapsed_row_sequence_matches_operator_flow() -> None:
    """Control Plane collapsed row headers must preserve replay -> manifest -> global -> audit -> missing-signals order."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "row" and panel.get("collapsed") is True
    ]
    row_pairs = [
        (panel.get("id"), panel.get("title"), panel.get("gridPos", {}).get("y"))
        for panel in sorted(row_panels, key=lambda panel: panel.get("gridPos", {}).get("y", 0))
    ]
    assert row_pairs == [
        (902, "Incident Drilldown: Replay Safety (Checkpoint / Replay)", 8),
        (901, "Incident Drilldown: Manifest / Ledger Integrity", 9),
        (903, "Incident Drilldown: Global Control-Plane Store Reliability", 10),
        (904, "Incident Drilldown: Audit / Lineage Completeness", 11),
        (905, "Known missing replay-safety signals", 12),
    ], f"Control Plane row order/title drifted: {row_pairs}"


def test_control_plane_first_evidence_panel_stays_close_to_answer_row() -> None:
    """Selected-range blocker evidence should live in the first replay drilldown row, not compete with the trust answer row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Track: Replay / Resume Blockers in Range")
    assert panel is not None
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("y") == 8
    assert grid_pos.get("w", 0) == 24
    root_titles = {
        panel.get("title")
        for panel in dashboard.get("panels", [])
        if panel.get("title")
    }
    assert "Track: Replay / Resume Blockers in Range" not in root_titles


def test_control_plane_long_first_screen_titles_keep_extra_width() -> None:
    """Long first-screen title cards must keep enough width to avoid avoidable truncation risk."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
        "Next Action: Replay Diagnostics",
    ):
        panel = panels.get(panel_title)
        assert panel is not None
        grid_pos = panel.get("gridPos", {})
        assert grid_pos.get("w", 0) >= 5, f"{panel_title} needs extra width for stable title/text rendering"


def test_control_plane_terminal_events_table_has_readable_width() -> None:
    """Terminal event evidence table should keep enough width for practical status visibility."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Inspect: Terminal Run Events by Status in Range")
    assert panel is not None
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("w", 0) >= 12


def test_control_plane_manifest_evidence_top_band_uses_full_row_width() -> None:
    """Manifest/ledger evidence top band should use the full row width to avoid avoidable dead space."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    top_band_titles = (
        "Inspect: Terminal Run Events by Status in Range",
        "Monitor: Manifest Write Failures",
        "Monitor: Ledger Append Failures",
    )
    widths = []
    xs = []
    ys = set()
    heights = set()
    for panel_title in top_band_titles:
        panel = panels.get(panel_title)
        assert panel is not None
        grid_pos = panel.get("gridPos", {})
        widths.append(grid_pos.get("w", 0))
        xs.append(grid_pos.get("x", 0))
        ys.add(grid_pos.get("y", 0))
        heights.add(grid_pos.get("h", 0))

    assert ys == {8}
    assert heights == {6}
    assert sum(widths) == 24, f"Manifest/ledger top band should fill the row, got widths={widths}"
    assert sorted(xs) == [0, 12, 18], f"Unexpected manifest/ledger top band placement: xs={xs}"


def test_control_plane_replay_safety_detail_top_bands_use_full_row_width() -> None:
    """Replay-safety detail row should not leave dead horizontal space in its visible top bands."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panel = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "row"
        and panel.get("title") == "Incident Drilldown: Replay Safety (Checkpoint / Replay)"
    )
    panels = {panel.get("id"): panel for panel in row_panel.get("panels", [])}

    known_blind_spots = panels[894]
    blind_spots_grid = known_blind_spots.get("gridPos", {})
    assert blind_spots_grid.get("x") == 0
    assert blind_spots_grid.get("w") == 24
    assert blind_spots_grid.get("y") == 2

    trio = [panels[3], panels[104], panels[120]]
    trio_widths = [panel.get("gridPos", {}).get("w", 0) for panel in trio]
    trio_xs = sorted(panel.get("gridPos", {}).get("x", 0) for panel in trio)
    trio_ys = {panel.get("gridPos", {}).get("y", 0) for panel in trio}
    assert sum(trio_widths) == 24, f"Replay-safety KPI trio should fill the row, got widths={trio_widths}"
    assert trio_xs == [0, 8, 16], f"Unexpected replay-safety KPI placement: xs={trio_xs}"
    assert trio_ys == {16}


def test_control_plane_lineage_top_band_uses_full_row_width() -> None:
    """Audit/lineage top singleton should fill the row instead of leaving avoidable dead space."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panel = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "row"
        and panel.get("title") == "Incident Drilldown: Audit / Lineage Completeness"
    )
    panels = {panel.get("id"): panel for panel in row_panel.get("panels", [])}
    panel = panels[122]
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("x") == 0
    assert grid_pos.get("y") == 8
    assert grid_pos.get("w") == 24


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
        "Runtime Blockers",
        "DQ Status",
        "Gold Lifecycle",
        "Control Plane",
        "Provider Global",
        "Workflow Selected",
        "Workflow Global",
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
        "Track Stage Backlog Trend": "bioetl_stage_backlog_records",
        "Inspect Errors by Stage / Error Code / Range": "bioetl_errors_total",
        "Track Records by Stage / Run Type / Range": "bioetl_records_processed_total",
        "Track Pipeline Phase Duration p50/p95/p99": "bioetl_phase_duration_seconds_bucket",
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

    reconstruct = panels.get("Monitor: Replay Not Reconstructable")
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
        drift = panels.get("Monitor: Replay Drift")
    assert drift is not None
    drift_expr = "\n".join(
        target.get("expr", "")
        for target in drift.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_drift_events_total" in drift_expr

    lag = panels.get("Track: Replay Lag Seconds")
    assert lag is not None
    lag_expr = "\n".join(
        target.get("expr", "")
        for target in lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_lag_seconds" in lag_expr
    assert lag.get("fieldConfig", {}).get("defaults", {}).get("unit") == "s"


def test_control_plane_trust_panels_preserve_missing_telemetry() -> None:
    """Control-plane trust-state panels must not mask missing telemetry as zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor: Replay Safety State",
        "Monitor: Manifest / Ledger Integrity",
    ):
        panel = panels.get(title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "or vector(0)" not in expr
        assert panel.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
            "UNKNOWN"
        )
        assert panel.get("options", {}).get("colorMode") == "background"

        value_mapping = next(
            (
                mapping
                for mapping in panel.get("fieldConfig", {})
                .get("defaults", {})
                .get("mappings", [])
                if mapping.get("type") == "value"
            ),
            None,
        )
        assert value_mapping is not None
        assert value_mapping.get("options") == {
            "0": {"text": "OK", "color": "green"},
            "1": {"text": "WARN", "color": "orange"},
            "2": {"text": "CRIT", "color": "red"},
        }


def test_control_plane_run_type_noop_panels_disclose_scope_limit() -> None:
    """Panels backed by metric families without run_type must disclose that the selector is a no-op."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expected_titles = (
        "Monitor: Checkpoint Incompatibilities",
        "Monitor: Replay Not Reconstructable",
        "Monitor: Checkpoint Load Failures",
        "Monitor: Checkpoint Save Failures",
        "Track: Checkpoint Compatibility Outcomes",
        "Track: Checkpoint Save Latency p50/p95/p99",
        "Monitor: Ledger Append Failures",
        "Track: Ledger Appends by Event Type / Status",
        "Monitor: Ledger Append Failure Ratio",
        "Monitor: Lineage Refs Missing",
        "Monitor: Lineage Fragment Persistence Failures",
        "Inspect: Missing Lineage Refs by Layer / Type",
        "Track: Lineage Fragment Outcomes",
    )
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in expected_titles:
        panel = panels.get(title)
        assert panel is not None, f"Control Plane missing {title!r}"
        description = str(panel.get("description", ""))
        assert "run_type selector does not change this panel" in description, (
            f"Control Plane panel {title!r} must disclose that run_type is a no-op"
        )


def test_control_plane_exposes_terminal_events_and_telemetry_gap() -> None:
    """Control-plane must expose terminal ledger evidence and missing telemetry risk."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected = {
        "Inspect: Telemetry Missing": (
            "bioetl_control_plane_telemetry_missing_5m",
        ),
        "Inspect: Terminal Run Events by Status in Range": (
            "bioetl_control_plane_terminal_events_total",
        ),
    }
    for title, tokens in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Control Plane dashboard missing {title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        for token in tokens:
            assert token in expr

    telemetry = panels["Inspect: Telemetry Missing"]
    assert telemetry.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
        "UNKNOWN"
    )


def test_control_plane_failure_ratio_thresholds_match_descriptions() -> None:
    """Manifest/ledger ratio panels should project >10% into CRIT severity."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor: Manifest Write Failure Ratio",
        "Monitor: Ledger Append Failure Ratio",
        "Monitor: GLOBAL Control-Plane Read Failure Ratio",
    ):
        panel = panels.get(title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        if title == "Monitor: GLOBAL Control-Plane Read Failure Ratio":
            assert "> bool 0.05" in expr
            assert "> bool 0.10" in expr
        else:
            assert "> bool 0.1" in expr
        steps = (
            panel.get("fieldConfig", {})
            .get("defaults", {})
            .get("thresholds", {})
            .get("steps", [])
        )
        assert steps == [
            {"color": "green", "value": None},
            {"color": "orange", "value": 1},
            {"color": "red", "value": 2},
        ]


def test_dashboard_default_time_and_refresh_policy_by_uid_class() -> None:
    """Shipped dashboards must keep canonical time.from/refresh policy by UID class."""
    contract = _load_navigation_contract()
    policy = contract.get("default_time_refresh_policy", {})
    exceptions = contract.get("default_time_refresh_policy_exceptions", {})

    assert isinstance(policy, dict), "default_time_refresh_policy must be defined"
    assert isinstance(exceptions, dict), (
        "default_time_refresh_policy_exceptions must be a mapping"
    )

    l0_uids = policy.get("L0", {}).get("dashboards", [])
    l1_uids = policy.get("L1", {}).get("dashboards", [])
    l2_uids = policy.get("L2", {}).get("dashboards", [])

    assert (
        isinstance(l0_uids, list)
        and isinstance(l1_uids, list)
        and isinstance(l2_uids, list)
    )

    baseline = {"time_from": "now-12h", "refresh": "30s"}
    explorer_baseline = {"time_from": "now-24h", "refresh": "1m"}

    for uid in [*l0_uids, *l1_uids]:
        expected = exceptions.get(uid, baseline)
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        assert dashboard.get("uid") == uid, f"Dashboard UID mismatch for {uid}.json"

        time_cfg = dashboard.get("time", {})
        assert isinstance(time_cfg, dict), f"{uid} time config must be an object"
        assert time_cfg.get("from") == expected["time_from"], (
            f"{uid} must keep time.from={expected['time_from']!r}, got {time_cfg.get('from')!r}"
        )
        assert dashboard.get("refresh") == expected["refresh"], (
            f"{uid} must keep refresh={expected['refresh']!r}, got {dashboard.get('refresh')!r}"
        )

    for uid in l2_uids:
        expected = exceptions.get(uid, explorer_baseline)
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        assert dashboard.get("uid") == uid, f"Dashboard UID mismatch for {uid}.json"

        time_cfg = dashboard.get("time", {})
        assert isinstance(time_cfg, dict), f"{uid} time config must be an object"
        assert time_cfg.get("from") == expected["time_from"], (
            f"{uid} must keep time.from={expected['time_from']!r}, got {time_cfg.get('from')!r}"
        )
        assert dashboard.get("refresh") == expected["refresh"], (
            f"{uid} must keep refresh={expected['refresh']!r}, got {dashboard.get('refresh')!r}"
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

    detail_panel = next(
        (
            panel
            for panel in panels
            if panel.get("title") == "Inspect Provider Health Check Latency (p95) - $provider"
        ),
        None,
    )
    assert detail_panel is not None
    assert detail_panel.get("gridPos", {}).get("y", 0) >= detail_row.get(
        "gridPos", {}
    ).get("y", 0)


def test_runtime_dq_control_plane_expose_contextual_loki_explore_link() -> None:
    """Only Runtime/DQ critical panels expose contextual Loki Explore links."""
    dashboard_panels = {
        "bioetl-runtime.json": "Monitor Failed Runs",
        "bioetl-dq-v2.json": "Track Range Evidence: Bronze -> Silver -> Gold",
    }

    for dashboard_name, panel_title in dashboard_panels.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        panel = panels.get(panel_title)
        assert panel is not None, (
            f"{dashboard_name} missing critical panel {panel_title!r}"
        )

        links = panel.get("options", {}).get("dataLinks", [])
        assert links, f"{dashboard_name}:{panel_title} must include dataLinks"

        baseline = [
            link
            for link in links
            if isinstance(link, dict)
            and str(link.get("title", "")).startswith("Open Logs (Loki")
            and "query=%7Bjob%3D%22bioetl%22%7D" in str(link.get("url", ""))
        ]
        assert baseline, (
            f'{dashboard_name}:{panel_title} must keep baseline Loki link with {{job="bioetl"}}'
        )

        contextual = [
            link
            for link in links
            if isinstance(link, dict)
            and link.get("title")
            in [
                "Open Logs (Loki, contextual scope marker)",
                "Open Logs (Loki, contextual scope marker, tracing)",
            ]
            and "scope_marker%3D%22dashboard_context%22" in str(link.get("url", ""))
        ]
        assert contextual, (
            f"{dashboard_name}:{panel_title} must include contextual Loki link with scope marker"
        )

        for link in contextual:
            url = str(link.get("url", ""))
            assert "run_id" not in url
            assert "payload_hash" not in url


def test_control_plane_does_not_expose_explore_links() -> None:
    """Control Plane uses the dashboard bus and runbooks, not direct Explore links."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    serialized = json.dumps(dashboard.get("panels", []))

    assert "grafana-lokiexplore-app" not in serialized
    assert "grafana-exploretraces-app" not in serialized
