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
"""Integration tests for Grafana dashboard configurations and observability contracts."""

from collections import Counter
from collections.abc import Iterator
from html import unescape
import json
from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import (
    _PROMQL_METRIC_SELECTOR_RE,
    _assert_operator_context_shell_contract,
    _assert_provider_health_variable_contract,
    _assert_standard_variable_contract,
    _extract_selector_labels,
    _unknown_metrics_for_query,
    get_dashboard_navigation_links,
    get_all_valid_metric_names,
    get_dashboard_files,
    get_dashboard_panels,
    get_dashboard_prometheus_queries,
    get_row_child_panels,
    get_metric_label_sets,
    get_panel_expressions,
    load_dashboard,
    panel_display_title,
)


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


from tests.integration.grafana_contract_specs import (
    CONTROL_PLANE_GLOBAL_READ_PANEL_TITLES,
    CONTROL_PLANE_GLOBAL_SCOPE_EXPECTATIONS,
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
    "bioetl-alerts-slo.json": {"workflow", "pipeline", "run_type"},
    "bioetl-overview-v2.json": {"workflow", "pipeline", "run_type", "run_id"},
    "bioetl-dq-v2.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "stage",
    },
    "bioetl-runtime.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "stage",
        "provider_hint",
    },
    "bioetl-provider-health-v2.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "provider",
        "pipeline_context",
        "adapter",
    },
    "bioetl-control-plane-v1.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
    },
    "bioetl-incident-v1.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "provider",
    },
    "bioetl-run-explorer-v1.json": {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
    },
    "bioetl-workflow-overview.json": {
        "workflow",
        "workflow_context",
        "pipeline",
        "run_type",
        "run_id",
        "status",
        "pipeline_context",
        "pipeline_context_exact",
        "run_type_context",
        "run_type_context_exact",
        "provider_context",
        "provider_context_exact",
        "step_status",
        "step_kind",
    },
}
_OPTIONAL_LOCAL_PANEL_TYPES = {"bioetl-selectorshell-panel"}


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
    panel_title = panel.get("title", "<untitled>")
    if not isinstance(links, list):
        return [f"panel={panel_title} links must be a list, got {type(links).__name__}"]

    violations: list[str] = []
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            violations.append(
                f"panel={panel_title} links[{index}] must be a mapping, "
                f"got {type(link).__name__}"
            )
            continue
        url = str(link.get("url", ""))
        for variable_name in _undeclared_link_variables(url, declared_variables):
            violations.append(
                f"panel={panel_title} link={link.get('title', '<untitled>')} "
                f"uses ${variable_name} not declared in templating.list"
            )
    return violations


def _dashboard_link_variable_violations(
    dashboard: dict, declared_variables: set[str]
) -> list[str]:
    # Fail-closed navigation bus validation lives in get_dashboard_navigation_links.
    links = get_dashboard_navigation_links(dashboard)

    violations: list[str] = []
    for link in links:
        url = str(link.get("url", ""))
        for variable_name in _undeclared_link_variables(url, declared_variables):
            violations.append(
                f"dashboard_link={link.get('title', '<untitled>')} "
                f"uses ${variable_name} not declared in templating.list"
            )
    return violations


def _canonical_prometheus_datasource() -> dict[str, str]:
    return {"type": "prometheus", "uid": "prometheus"}


def _is_prometheus_datasource(datasource: object) -> bool:
    if not isinstance(datasource, dict):
        return False
    return (
        datasource.get("type") == "prometheus" or datasource.get("uid") == "prometheus"
    )


def _panel_prometheus_datasource_errors(panel: dict) -> list[str]:
    errors: list[str] = []
    panel_id = panel.get("id", "<unknown>")
    panel_title = panel.get("title", "<untitled>")
    datasource = panel.get("datasource")

    if datasource == "Prometheus":
        errors.append(
            f"panel id={panel_id} title={panel_title!r} uses string "
            "datasource 'Prometheus'; use explicit object format"
        )
    elif _is_prometheus_datasource(datasource) and datasource != (
        _canonical_prometheus_datasource()
    ):
        errors.append(
            f"panel id={panel_id} title={panel_title!r} has non-canonical "
            f"Prometheus datasource object: {datasource}"
        )

    errors.extend(_target_prometheus_datasource_errors(panel))
    return errors


def _target_prometheus_datasource_errors(panel: dict) -> list[str]:
    errors: list[str] = []
    panel_id = panel.get("id", "<unknown>")
    panel_title = panel.get("title", "<untitled>")
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
        if _is_prometheus_datasource(target_datasource) and target_datasource != (
            _canonical_prometheus_datasource()
        ):
            errors.append(
                f"panel id={panel_id} title={panel_title!r} target={target_ref} "
                f"has non-canonical Prometheus datasource object: "
                f"{target_datasource}"
            )
    return errors


def _iter_structured_urls(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        url = value.get("url")
        if isinstance(url, str):
            yield url
        for child in value.values():
            yield from _iter_structured_urls(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from _iter_structured_urls(child)


def _collect_explore_traces_urls(dashboard: dict) -> list[str]:
    trace_urls = [
        unescape(url)
        for url in _iter_structured_urls(dashboard)
        if "grafana-exploretraces-app" in url
    ]
    for panel in dashboard.get("panels", []):
        nav_content = unescape(str(panel.get("options", {}).get("content", "")))
        trace_urls.extend(
            re.findall(r'href="([^"]*grafana-exploretraces-app[^"]*)"', nav_content)
        )
    return trace_urls


def _assert_safe_explore_traces_url(dashboard_name: str, url: str) -> None:
    assert "/a/grafana-exploretraces-app/explore?actionView=search" in url, (
        f"{dashboard_name} must use the explicit Explore Traces route: {url}"
    )
    assert "from=${__from}" in url and "to=${__to}" in url, (
        f"{dashboard_name} must preserve the active dashboard range: {url}"
    )
    assert "var-ds=tempo" in url, (
        f"{dashboard_name} must pin the Tempo datasource: {url}"
    )
    assert "var-groupBy=resource.service.name" in url, (
        f"{dashboard_name} must use a safe default groupBy: {url}"
    )
    assert "span.%22bioetl.run_type%22%20%3D~%20%22${run_type:regex}%22" not in url, (
        f"{dashboard_name} must not couple Explore Traces to ${{run_type:regex}}: {url}"
    )
    assert (
        "span.%22bioetl.run_type%22%20%3D~%20%22${run_type_context:regex}%22" not in url
    ), (
        f"{dashboard_name} must not couple Explore Traces to "
        f"${{run_type_context:regex}}: {url}"
    )
    assert "/a/grafana-exploretraces-app/?from=" not in url
    assert "from=now-150m&to=now" not in url
    assert "var-groupBy=undefined" not in url


def _panel_title_vocabulary_errors(dashboard_path: Path, panel: dict) -> list[str]:
    if panel.get("type") == "row":
        return []
    title = panel.get("title", "")
    if not isinstance(title, str):
        return []

    expressions = get_panel_expressions(panel)
    errors: list[str] = []
    if (
        any("by (provider" in expr for expr in expressions)
        and "by Provider" not in title
    ):
        errors.append(
            f"{dashboard_path.name}: panel '{title}' groups by provider but title "
            "does not contain 'by Provider'"
        )
    if any("by (adapter" in expr for expr in expressions) and "by Adapter" not in title:
        errors.append(
            f"{dashboard_path.name}: panel '{title}' groups by adapter but title "
            "does not contain 'by Adapter'"
        )
    return errors


def _collect_recording_rule_usage_errors(
    recording_rules: set[str],
) -> tuple[set[str], list[str]]:
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
    return used_recording_rules, errors


def _variable_map(dashboard: dict) -> dict[str, dict]:
    return {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }


def _assert_alerts_slo_variable_sources(variable_map: dict[str, dict]) -> None:
    assert variable_map["workflow"].get("type") == "textbox"
    assert "bioetl_overview_pipeline_run_type_universe" in str(
        variable_map["pipeline"].get("query", {})
    )
    assert "bioetl_overview_pipeline_run_type_universe" in str(
        variable_map["run_type"].get("query", {})
    )


def _require_dict_query(variable_map: dict[str, dict], name: str) -> dict:
    query = variable_map[name].get("query", {})
    assert isinstance(query, dict)
    return query


def _assert_workflow_overview_prom_queries(variable_map: dict[str, dict]) -> None:
    workflow_query = _require_dict_query(variable_map, "workflow")
    pipeline_query = _require_dict_query(variable_map, "pipeline")
    run_type_query = _require_dict_query(variable_map, "run_type")
    status_query = _require_dict_query(variable_map, "status")
    pipeline_context_query = _require_dict_query(variable_map, "pipeline_context")
    run_type_context_query = _require_dict_query(variable_map, "run_type_context")
    provider_context_query = _require_dict_query(variable_map, "provider_context")
    step_status_query = _require_dict_query(variable_map, "step_status")
    step_kind_query = _require_dict_query(variable_map, "step_kind")

    assert "bioetl_workflow_universe" in workflow_query.get("query", "")
    assert "bioetl_overview_pipeline_run_type_universe" in pipeline_query.get(
        "query", ""
    )
    assert "bioetl_overview_pipeline_run_type_universe" in run_type_query.get(
        "query", ""
    )
    assert "bioetl_workflow_runs_total" in status_query.get("query", "")
    assert "bioetl_workflow_runs_total" in pipeline_context_query.get("query", "")
    assert "bioetl_workflow_runs_total" in run_type_context_query.get("query", "")
    assert "bioetl_workflow_runs_total" in provider_context_query.get("query", "")
    assert "bioetl_workflow_step_events_total" in step_status_query.get("query", "")
    assert "bioetl_workflow_step_events_total" in step_kind_query.get("query", "")


def _assert_filter_options_dimension(
    infinity_query: object, *, dimension: str, require_exact_run: bool = True
) -> None:
    url = str(infinity_query.get("url", "") if isinstance(infinity_query, dict) else "")
    assert "/ops/control-plane/filter-options" in url
    assert f"dimension={dimension}" in url
    if require_exact_run:
        assert "exact_run_only=1" in url


def _assert_workflow_overview_context_queries(variable_map: dict[str, dict]) -> None:
    workflow_context_query = _require_dict_query(variable_map, "workflow_context")
    pipeline_context_exact_query = _require_dict_query(
        variable_map, "pipeline_context_exact"
    )
    run_type_context_exact_query = _require_dict_query(
        variable_map, "run_type_context_exact"
    )
    provider_context_exact_query = _require_dict_query(
        variable_map, "provider_context_exact"
    )

    assert workflow_context_query.get("queryType") == "infinity"
    workflow_context_infinity = workflow_context_query.get("infinityQuery", {})
    _assert_filter_options_dimension(workflow_context_infinity, dimension="workflow")
    assert "fallback_value=${workflow:text}" in str(
        workflow_context_infinity.get("url", "")
        if isinstance(workflow_context_infinity, dict)
        else ""
    )
    _assert_filter_options_dimension(
        pipeline_context_exact_query.get("infinityQuery", {}), dimension="pipeline"
    )
    _assert_filter_options_dimension(
        run_type_context_exact_query.get("infinityQuery", {}), dimension="run_type"
    )
    _assert_filter_options_dimension(
        provider_context_exact_query.get("infinityQuery", {}), dimension="provider"
    )


def _assert_workflow_overview_variable_sources(
    dashboard_path: Path, variable_map: dict[str, dict]
) -> None:
    _assert_operator_context_shell_contract(dashboard_path, variable_map)
    _assert_workflow_overview_prom_queries(variable_map)
    _assert_workflow_overview_context_queries(variable_map)


def _assert_overview_run_id_variable_flags(run_id_var: dict) -> None:
    assert run_id_var.get("type") == "query"
    assert run_id_var.get("datasource") == "BioETL Ops HTTP"
    assert run_id_var.get("includeAll") is False
    assert run_id_var.get("multi") is False
    assert run_id_var.get("current", {}).get("text") == "-"
    assert run_id_var.get("current", {}).get("value") == "-"


def _assert_overview_run_id_query_url(run_id_query_url: str) -> None:
    assert "/ops/control-plane/filter-options" in run_id_query_url
    assert "dimension=run_id" in run_id_query_url
    assert "response_shape=list" in run_id_query_url
    assert "workflow=${workflow}" in run_id_query_url
    assert "pipeline=${pipeline}" in run_id_query_url
    assert "run_type=${run_type:csv}" in run_id_query_url


def _assert_overview_run_id_infinity_query(run_id_query: dict) -> None:
    assert run_id_query.get("queryType") == "infinity"
    assert run_id_query.get("refId") == "variable"
    infinity_query = run_id_query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict)
    assert infinity_query.get("format") == "table"
    assert infinity_query.get("parser") == "backend"
    assert infinity_query.get("root_selector") == "$.items"
    assert infinity_query.get("url_options", {}).get("method") == "GET"
    _assert_overview_run_id_query_url(str(infinity_query.get("url", "")))


def _assert_overview_run_id_variable(run_id_var: dict) -> None:
    _assert_overview_run_id_variable_flags(run_id_var)
    run_id_query = run_id_var.get("query", {})
    assert isinstance(run_id_query, dict)
    _assert_overview_run_id_infinity_query(run_id_query)


def _assert_overview_identity_panel(dashboard: dict) -> None:
    identity_panel = next(
        (panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 9300),
        None,
    )
    assert identity_panel is not None
    assert identity_panel.get("datasource") == "BioETL Ops HTTP"
    identity_targets = identity_panel.get("targets", [])
    assert isinstance(identity_targets, list) and len(identity_targets) == 1
    identity_target = identity_targets[0]
    assert identity_target.get("parser") == "backend"
    assert identity_target.get("root_selector") == "rows"
    assert (
        str(identity_target.get("url", ""))
        == "/ops/control-plane/identity-table?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}"
    )


def _assert_overview_variable_sources(
    dashboard: dict, variable_map: dict[str, dict]
) -> None:
    workflow_var = variable_map["workflow"]
    workflow_query = workflow_var.get("query", {})
    workflow_query_text = (
        workflow_query.get("query", "") if isinstance(workflow_query, dict) else ""
    )
    assert workflow_var.get("datasource") == _canonical_prometheus_datasource()
    assert "bioetl_workflow_universe" in workflow_query_text

    pipeline_var = variable_map["pipeline"]
    pipeline_query = pipeline_var.get("query", {})
    assert isinstance(pipeline_query, dict)
    infinity = pipeline_query.get("infinityQuery", {})
    assert isinstance(infinity, dict)
    pipeline_url = str(infinity.get("url", ""))
    assert "/ops/control-plane/filter-options" in pipeline_url
    assert "dimension=pipeline" in pipeline_url
    assert pipeline_var.get("datasource") == "BioETL Ops HTTP"

    run_type_var = variable_map["run_type"]
    run_type_query = run_type_var.get("query", {})
    run_type_query_text = (
        run_type_query.get("query", "") if isinstance(run_type_query, dict) else ""
    )
    assert "bioetl_overview_pipeline_run_type_universe" in run_type_query_text
    assert "run_type" in run_type_query_text

    _assert_overview_run_id_variable(variable_map["run_id"])
    _assert_overview_identity_panel(dashboard)


def _assert_global_metric_expr_unscoped(
    dashboard_name: str,
    panel_title: str,
    expr: str,
    forbidden_metrics: tuple[str, ...],
) -> None:
    if not any(metric in expr for metric in forbidden_metrics):
        return
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


def _assert_control_plane_read_panel_no_pipeline_filter(
    dashboard_name: str,
    panel_title: str,
    panel: dict | None,
    forbidden_metrics: tuple[str, ...],
) -> None:
    assert panel is not None, (
        f"{dashboard_name} missing control-plane panel {panel_title!r}"
    )
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    for expr in expressions:
        _assert_global_metric_expr_unscoped(
            dashboard_name, panel_title, expr, forbidden_metrics
        )


def _assert_latency_panel_has_quantiles(panel_title: str, panel: dict | None) -> None:
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


def _assert_identity_evidence_panel(panels: dict, title: str, view: str) -> None:
    panel = panels.get(title)
    assert panel is not None, f"Control-plane dashboard missing {title!r}"
    assert panel.get("datasource") == "BioETL Ops HTTP"
    targets = panel.get("targets", [])
    assert len(targets) == 1
    target = targets[0]
    assert target.get("parser") == "backend"
    assert target.get("root_selector") == "rows"
    url = str(target.get("url", ""))
    assert "/ops/control-plane/identity-evidence?" in url
    assert view in url
    assert "run_id=${run_id}" in url


def _assert_scoped_control_plane_nav_link(title: str, link: dict) -> None:
    url = str(link.get("url", ""))
    assert "var-workflow=$workflow" in url
    assert "var-pipeline=$pipeline" in url
    assert "var-run_type=$run_type" in url
    assert "var-run_id=$run_id" in url
    assert "${__url_time_range}" in url


def _assert_provider_health_value_mappings(
    options: dict, description: str, expected_pairs: dict[str, str]
) -> None:
    assert set(options) == set(expected_pairs)
    for status_code, label in expected_pairs.items():
        text = str(options[status_code].get("text", "")).upper()
        assert text == label
        assert f"{status_code}={label}" in description


def _assert_provider_health_null_mapping(
    mappings: list, description: str, expected_null: str
) -> None:
    null_mappings = [
        mapping
        for mapping in mappings
        if mapping.get("type") == "special"
        and mapping.get("options", {}).get("match") == "null"
    ]
    assert len(null_mappings) == 1, "panel id=114 must map null exactly once"
    assert (
        str(null_mappings[0]["options"]["result"].get("text", "")).upper()
        == expected_null
    )
    assert expected_null in description
    assert "null/NaN=UNKNOWN" in description or "null=UNKNOWN" in description
    assert "raw status is absent" in description


def _assert_workflow_step_panel_selectors(
    panels: dict, title: str, required_snippets: tuple[str, ...]
) -> None:
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


_WORKFLOW_STEP_DIAGNOSTIC_TITLES = (
    "Step Outcomes by Kind / Step Status / Range",
    "Step Duration p95 by Kind / Step Status / Range",
)


def _assert_workflow_step_diagnostics_row(row_panel: dict | None) -> dict:
    assert row_panel is not None, "Workflow dashboard must expose step diagnostics row"
    assert row_panel.get("type") == "row"
    assert row_panel.get("collapsed") is False
    return row_panel


def _assert_workflow_step_diagnostics_children(
    dashboard: dict, panels: list, row_panel: dict
) -> None:
    row_titles = {
        panel.get("title")
        for panel in get_row_child_panels(dashboard, "Step Diagnostics")
        if panel.get("title")
    }
    for title in _WORKFLOW_STEP_DIAGNOSTIC_TITLES:
        assert title in row_titles

    root_titles = {
        panel.get("title") for panel in panels if isinstance(panel.get("title"), str)
    }
    for title in _WORKFLOW_STEP_DIAGNOSTIC_TITLES:
        assert title not in root_titles

    row_y = row_panel.get("gridPos", {}).get("y", 0)
    assert all(
        panel.get("gridPos", {}).get("y", 0) > row_y
        for panel in get_row_child_panels(dashboard, "Step Diagnostics")
    )


def _assert_workflow_step_diagnostics_layout(dashboard: dict) -> None:
    panels = dashboard.get("panels", [])
    row_panel = _assert_workflow_step_diagnostics_row(
        next(
            (panel for panel in panels if panel.get("title") == "Step Diagnostics"),
            None,
        )
    )
    _assert_workflow_step_diagnostics_children(dashboard, panels, row_panel)


_WORKFLOW_FIRST_ACTION_LINK_TITLES = {
    "Open 2. Runtime",
    "Open 4. Data Quality",
    "Open 3. Provider Health",
    "Open 0. Control Plane",
    "Open 1. Overview",
}


def _assert_workflow_first_action_links(data_links: list) -> None:
    assert data_links, "Workflow First Action must expose actionable dataLinks"
    observed_titles = {
        str(link.get("title"))
        for link in data_links
        if isinstance(link, dict) and link.get("title")
    }
    assert _WORKFLOW_FIRST_ACTION_LINK_TITLES <= observed_titles
    for link in data_links:
        assert link.get("targetBlank") is False
        assert "${__url_time_range}" in str(link.get("url", ""))


def _assert_workflow_first_action_panel(dashboard: dict) -> None:
    panels = dashboard.get("panels", [])
    next_panel = next(
        (panel for panel in panels if panel.get("title") == "First Action"),
        None,
    )
    assert next_panel is not None
    assert next_panel.get("gridPos", {}) == {"x": 0, "y": 17, "w": 24, "h": 5}
    _assert_workflow_first_action_links(
        next_panel.get("options", {}).get("dataLinks", [])
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_is_valid_json(dashboard_path):
    """L1: Verify that the dashboard file is a valid JSON."""
    data = _json_load_without_duplicate_keys(dashboard_path)
    assert isinstance(data, dict)
    assert "title" in data


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_panel_ids_are_unique(dashboard_path: Path) -> None:
    """Panel IDs must stay unique across root and row-nested panels."""
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
def test_shipped_dashboards_do_not_require_optional_local_plugins(
    dashboard_path: Path,
) -> None:
    """Primary shipped dashboards must not depend on local unsigned pilot plugins."""
    dashboard = load_dashboard(dashboard_path)
    plugin_panels = [
        f"id={panel.get('id', '<unknown>')} title={panel.get('title', '<untitled>')} type={panel.get('type')}"
        for panel in get_dashboard_panels(dashboard)
        if panel.get("type") in _OPTIONAL_LOCAL_PANEL_TYPES
    ]
    assert not plugin_panels, (
        f"{dashboard_path.name} must not reference optional local plugin panels yet: "
        f"{plugin_panels}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_prometheus_datasource_contract(dashboard_path: Path) -> None:
    """Prometheus panel and target datasources must use explicit provisioned UID."""
    dashboard = load_dashboard(dashboard_path)
    errors: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        errors.extend(_panel_prometheus_datasource_errors(panel))

    assert not errors, (
        f"Dashboard {dashboard_path.name} violates Prometheus datasource "
        f"contract:\n" + "\n".join(errors)
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_explore_traces_links_absent_after_tempo_removal(
    dashboard_path: Path,
) -> None:
    """Tempo was removed from the shipping stack; dashboards must not require it."""
    dashboard = load_dashboard(dashboard_path)
    trace_urls = _collect_explore_traces_urls(dashboard)
    assert not trace_urls, (
        f"{dashboard_path.name} still exposes Tempo Explore Traces URLs after removal: "
        f"{trace_urls}"
    )


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_panel_title_vocabulary_matches_group_by_vocabulary(
    dashboard_path: Path,
) -> None:
    """Panel titles should describe aggregation vocabulary in PromQL group-by labels."""
    dashboard = load_dashboard(dashboard_path)
    errors: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        errors.extend(_panel_title_vocabulary_errors(dashboard_path, panel))
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
    used_recording_rules, errors = _collect_recording_rule_usage_errors(
        _load_recording_rule_names()
    )
    assert not errors, "Dashboard recording-rule drift:\n" + "\n".join(errors)
    assert used_recording_rules, (
        "At least one shipped dashboard must consume recording rules; otherwise "
        "runtime dashboard parity checks are no longer exercising the rule pack."
    )


def test_overview_exposes_actual_alert_state_triage_surface() -> None:
    """Overview should include a dashboard-as-code alert-state triage surface."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {panel.get("id"): panel for panel in get_dashboard_panels(dashboard)}

    alert_panel = panels.get(9601)

    assert alert_panel is not None
    assert alert_panel["title"] == "Review Active Alerts"
    expressions = [target.get("expr", "") for target in alert_panel.get("targets", [])]
    assert any("ALERTS" in expr for expr in expressions)
    assert any("alertstate" in expr for expr in expressions)


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
    variable_map = _variable_map(dashboard)
    name = dashboard_path.name

    if name == "bioetl-alerts-slo.json":
        _assert_alerts_slo_variable_sources(variable_map)
        return
    if name == "bioetl-workflow-overview.json":
        _assert_workflow_overview_variable_sources(dashboard_path, variable_map)
        return
    if name == "bioetl-overview-v2.json":
        _assert_overview_variable_sources(dashboard, variable_map)
        return
    if name == "bioetl-provider-health-v2.json":
        _assert_provider_health_variable_contract(dashboard_path, variable_map)
        return
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
    """Freshness age must show the stalest entity in explicit operator hours."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Worst Freshness Age"
        ),
        None,
    )
    assert panel is not None, "Freshness lag panel not found in bioetl-dq-v2.json"
    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any(
        "max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds" in expr
        and "/ 3600" in expr
        for expr in expressions
    ), "Freshness panel must derive worst age in hours from range timestamp evidence"
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
        ("bioetl-dq-v2.json", "Inspect Latest Successful Data"),
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
    assert any(
        "max(max_over_time(bioetl_data_freshness_seconds" in expr
        for expr in expressions
    )
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
        "Monitor Replay Safety",
        "Monitor Checkpoint Age",
        "Monitor Manifest/Ledger",
        "Monitor Telemetry",
    }
    next_step_title = "Review Recovery Action"
    first_screen_titles = {
        panel_display_title(panel)
        for panel in panels
        if panel.get("type") != "row"
        and int((panel.get("gridPos") or {}).get("y", 999)) < 18
    }

    assert kpi_titles.issubset(first_screen_titles)
    assert next_step_title in first_screen_titles
    assert len(first_screen_titles & kpi_titles) == 4


def test_control_plane_l1_has_single_next_step_panel_with_expected_target() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel_display_title(panel) == "Review Recovery Action"
    ]
    assert len(panels) == 1

    links = panels[0].get("options", {}).get("dataLinks", [])
    urls = [str(link.get("url", "")) for link in links]
    assert urls
    assert any("viewPanel=130" in url for url in urls)
    assert any("viewPanel=9418" in url for url in urls)
    assert any("viewPanel=9415" in url for url in urls)
    assert any("viewPanel=9416" in url for url in urls)
    assert all(
        "/d/bioetl-control-plane-v1/bioetl-control-plane-v1" in url for url in urls
    )


def test_control_plane_has_replay_resume_blockers_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Track Replay Blockers")

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
    expectations = CONTROL_PLANE_GLOBAL_SCOPE_EXPECTATIONS

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
    forbidden_metrics = (
        "bioetl_control_plane_reads_total",
        "bioetl_control_plane_read_duration_seconds",
    )
    for dashboard_name, panel_titles in CONTROL_PLANE_GLOBAL_READ_PANEL_TITLES.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            _assert_control_plane_read_panel_no_pipeline_filter(
                dashboard_name,
                panel_title,
                panels.get(panel_title),
                forbidden_metrics,
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
            assert "GLOBAL" in str(panel.get("title", "")).upper()


def test_control_plane_latency_panels_have_p50_p95_p99() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    latency_panels = (
        "Track Checkpoint Save Latency",
        "Track Global Checkpoint Admin Latency",
        "Track Global Read Latency",
        "Track Global Audit Write Latency",
        "Track Global Audit Query Latency",
    )
    for panel_title in latency_panels:
        _assert_latency_panel_has_quantiles(panel_title, panels.get(panel_title))


def test_control_plane_no_missing_metric_promql() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expressions = "\n".join(get_panel_expressions(dashboard))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    assert "bioetl_replay_duplicate_records_total" not in expressions
    checkpoint_panel = panels["Monitor Checkpoint Age"]
    # Epic #6573/#6574: first-paint Ops HTTP = 0; checkpoint lag uses Prometheus rule.
    assert checkpoint_panel.get("datasource") == {
        "type": "prometheus",
        "uid": "prometheus",
    }
    target = checkpoint_panel.get("targets", [])[0]
    assert "bioetl_checkpoint_age_seconds" in str(target.get("expr", ""))


def test_control_plane_identity_evidence_panels_exist() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for title, view in {
        "Review Identity Anchors": "view=overview",
        "Review Identity Gaps": "view=gaps",
        "Compare Checkpoint Anchors": "view=checkpoint_compare",
        "Inspect Identity Values": "view=copy_values",
        "Review Required Replay Anchors": "view=anchors",
        "Review Additional Forensic Anchors": "view=anchors",
    }.items():
        _assert_identity_evidence_panel(panels, title, view)

    assert "priority=P1" in str(
        panels["Review Required Replay Anchors"]["targets"][0]["url"]
    )
    assert "priority=P2" in str(
        panels["Review Additional Forensic Anchors"]["targets"][0]["url"]
    )


def test_control_plane_remaining_replay_safety_text_is_not_stale() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "Review Uncovered Replay Signals"
        ),
        None,
    )
    assert panel is not None
    content = str(panel.get("options", {}).get("content", ""))
    assert panel.get("options", {}).get("mode") == "html"
    assert "Remaining replay-safety signal:" in content
    assert "occurrence-only vs semantic drift" in content
    assert (
        "Duplicate/overwrite write risk is now bounded Prometheus telemetry" in content
    )
    assert "checkpoint_age <= recovery window / RPO" not in content
    assert "manifest_id/run_id identity table in Grafana" not in content
    assert "duplicate-record evidence" not in content
    description = str(panel.get("description", "")).lower()
    assert "residual semantic-drift evidence" in description
    assert "duplicate/overwrite write risk is now instrumented" in description
    assert "not yet covered" not in description
    assert "manifest/run identity" not in description
    assert "execution/config/contract/input anchors" not in description
    assert "checkpoint freshness lag" not in description


def test_review_and_context_panels_use_no_scroll_layout_contract() -> None:
    """Review/context cards must fit their grids without hidden clipping."""
    panel_specs = {
        "bioetl-control-plane-v1.json": {139: ("html", 4)},
        "bioetl-overview-v2.json": {9021: ("html", 3)},
        "bioetl-runtime.json": {2541: ("html", 3)},
        "bioetl-provider-health-v2.json": {9400: ("html", 4)},
        "bioetl-incident-v1.json": {2007: ("html", 4)},
    }
    for filename, expected in panel_specs.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / filename)
        panels = {
            int(panel["id"]): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("id") in expected
        }
        assert panels.keys() == expected.keys()
        for panel_id, (mode, height) in expected.items():
            panel = panels[panel_id]
            assert panel.get("options", {}).get("mode") == mode
            assert panel.get("gridPos", {}).get("h") == height
            assert "overflow:hidden" not in str(
                panel.get("options", {}).get("content", "")
            )

    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    overview_panels = {
        int(panel["id"]): panel for panel in get_dashboard_panels(overview)
    }
    assert overview_panels[9002]["options"]["cellHeight"] == "sm"
    assert overview_panels[9002]["gridPos"]["h"] >= 5
    assert overview_panels[215]["gridPos"]["h"] >= 5
    assert overview_panels[9603]["gridPos"]["y"] < overview_panels[215]["gridPos"]["y"]

    run_explorer = load_dashboard(
        Path("grafana/dashboards/bioetl-run-explorer-v1.json")
    )
    run_panels = {
        int(panel["id"]): panel for panel in get_dashboard_panels(run_explorer)
    }
    assert run_panels[3016]["type"] == "table"
    assert run_panels[3016]["title"] == "Inspect Layer Accounting"
    assert run_panels[3014]["type"] == "table"
    assert run_panels[3014]["title"] == "Inspect Timings & Failure"

    assert 9403 not in run_panels
    assert 3021 not in run_panels
    assert 3001 not in run_panels
    assert run_panels[3022]["title"] == "Inspect Run Identity"
    assert run_panels[3023]["title"] == "Inspect Processed Records"



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
    assert "0. Trust" not in links  # self-link omitted from machine-readable bus
    for title in ("1. Overview", "2. Pipeline Diagnostics", "4. Data Quality"):
        _assert_scoped_control_plane_nav_link(title, links[title])


def test_silver_validation_panels_use_explicit_pipeline_label() -> None:
    """Silver validation queries should filter on a real pipeline label, not table-name regex."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Silver Validation Failures"
        ),
        None,
    )
    assert panel is not None, (
        "DQ dashboard missing 'Monitor Silver Validation Failures' panel"
    )

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any('{pipeline=~"$pipeline"}' in expr for expr in expressions), (
        "Monitor Silver Validation Failures must filter on the explicit pipeline label"
    )
    assert all('{table=~"$pipeline"}' not in expr for expr in expressions), (
        "Monitor Silver Validation Failures must not rely on the table-to-pipeline naming convention"
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
            if item.get("title") == "Inspect Raw Health Status"
        ),
        None,
    )
    assert panel is not None, (
        "Provider Health dashboard must expose raw provider health enum evidence"
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
    panel = next(
        (item for item in get_dashboard_panels(dashboard) if item.get("id") == 114),
        None,
    )
    assert panel is not None, "provider health raw enum panel id=114 must exist"
    mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    assert isinstance(mappings, list) and mappings, "panel id=114 mappings must exist"
    value_mapping = next(
        (mapping for mapping in mappings if mapping.get("type") == "value"),
        None,
    )
    assert value_mapping is not None, "panel id=114 must define value mappings"
    description = str(panel.get("description", ""))
    _assert_provider_health_value_mappings(
        value_mapping.get("options", {}), description, expected_pairs
    )
    _assert_provider_health_null_mapping(mappings, description, expected_null)


def test_runtime_provider_alert_conditions_do_not_filter_on_missing_pipeline_labels():
    """Provider runtime alert summaries are fleet-wide and must not filter on pipeline."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Global Provider Alert Conditions"
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
        "Inspect Global Provider Alert Conditions must not filter provider-only recording rules by pipeline."
    )


def test_runtime_provider_alert_conditions_local_panel_scopes_all_addends_to_provider_hint():
    """Selected-pipeline provider handoff must not mix in unscoped global provider alert sums."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Provider Alert Conditions"
        ),
        None,
    )
    assert panel is not None
    expr = panel["targets"][0]["expr"]
    assert expr.count('provider=~"$provider_hint"') >= 6
    assert 'provider_adapter_latency_high_30m{provider=~"$provider_hint"}' in expr
    assert 'provider_rate_limiter_wait_high_30m{provider=~"$provider_hint"}' in expr
    assert "unless on()" not in expr


def test_workflow_step_panels_apply_status_variable() -> None:
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))
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
        _assert_workflow_step_panel_selectors(panels, title, required_snippets)


def test_workflow_pipeline_status_fails_closed_without_runtime_fallback() -> None:
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Pipeline Status"
        ),
        None,
    )
    assert panel is not None
    expr = panel["targets"][0]["expr"]
    assert "bioetl_workflow_pipeline_verdict_status" in expr
    assert "bioetl_runtime_current_status" not in expr
    assert 'pipeline=~"$pipeline_context"' in expr
    assert 'run_type=~"$run_type_context"' in expr
    assert " or " not in expr
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "NOT RESOLVED"
    description = str(panel.get("description", ""))
    assert "Runtime fallback is intentionally forbidden" in description
    assert "never green" in description


def test_workflow_dashboard_collapses_step_diagnostics_below_first_screen() -> None:
    dashboard = load_dashboard(_require_dashboard("bioetl-workflow-overview.json"))
    _assert_workflow_step_diagnostics_layout(dashboard)
    _assert_workflow_first_action_panel(dashboard)


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
