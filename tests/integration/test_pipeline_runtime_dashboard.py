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
    "bioetl-overview-v2": frozenset({"workflow", "pipeline", "run_type", "run_id"}),
    "bioetl-dq-v2": frozenset({"workflow", "pipeline", "run_type", "run_id", "stage"}),
    "bioetl-runtime": frozenset(
        {"workflow", "pipeline", "run_type", "run_id", "stage"}
    ),
    "bioetl-provider-health-v2": frozenset(
        {
            "workflow",
            "pipeline",
            "run_type",
            "run_id",
            "provider",
            "pipeline_context",
            "adapter",
        }
    ),
    "bioetl-control-plane-v1": frozenset(
        {"workflow", "pipeline", "run_type", "run_id"}
    ),
    "bioetl-workflow-overview": frozenset(
        {"workflow", "pipeline", "run_type", "run_id"}
    ),
    "bioetl-alerts-slo": frozenset({"workflow", "pipeline", "run_type"}),
    "bioetl-incident-v1": frozenset({"workflow", "pipeline", "run_type", "run_id"}),
    "bioetl-run-explorer-v1": frozenset({"workflow", "pipeline", "run_type", "run_id"}),
}


def _dashboard() -> dict:
    return load_dashboard(_DASHBOARD_PATH)


def _extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    return match.group(1) if match is not None else None


def _extract_link_vars(url: str) -> set[str]:
    vars = set(_LINK_VAR_RE.findall(url))
    if "bioetl-provider-health-v2" in url:
        vars.discard("stage")
    return vars


def _runtime_data_panels() -> list[dict]:
    return [
        panel
        for panel in get_dashboard_panels(_dashboard())
        if panel.get("type") not in {"row", "text"}
    ]


def test_pipeline_runtime_dashboard_json_is_valid() -> None:
    dashboard = _dashboard()
    assert isinstance(dashboard, dict)
    assert dashboard.get("title") == "2. Pipeline Diagnostics"


def test_pipeline_runtime_dashboard_uid_is_bioetl_runtime() -> None:
    assert _dashboard().get("uid") == "bioetl-runtime"


def test_pipeline_runtime_has_required_variables() -> None:
    variables = {
        variable.get("name")
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }
    assert variables == {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "stage",
        "provider_hint",
    }


def test_pipeline_runtime_variables_use_runtime_universe() -> None:
    variables = {
        variable.get("name"): variable
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }

    pipeline_query = variables["pipeline"].get("query", {}).get("query", "")
    run_type_query = variables["run_type"].get("query", {}).get("query", "")
    stage_query = variables["stage"].get("query", {}).get("query", "")

    assert "bioetl_runtime_pipeline_run_type_universe" in pipeline_query
    assert "bioetl_runtime_pipeline_run_type_universe" in run_type_query
    assert "bioetl_records_processed_total" not in pipeline_query
    assert "bioetl_records_processed_total" not in run_type_query
    assert "bioetl_pipeline_stage_expected" in stage_query
    assert variables["provider_hint"].get("current", {}).get("value") == "chembl"


def test_pipeline_runtime_keeps_record_level_forensic_variables_out() -> None:
    variables = {
        variable.get("name")
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }
    assert "run_id" in variables
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


def test_pipeline_runtime_localization_empty_states_are_explicit() -> None:
    panels = {panel.get("title"): panel for panel in _runtime_data_panels()}

    errors_panel = panels["Review Errors by Stage & Code"]
    errors_description = errors_panel.get("description", "")
    assert "empty table means no matching samples" in errors_description.lower()

    records_panel = panels["Compare Records by Stage & Run Type"]
    records_description = records_panel.get("description", "")
    records_defaults = records_panel.get("fieldConfig", {}).get("defaults", {})
    assert records_defaults.get("noValue") == "No processed-record samples"
    assert (
        "phase duration"
        not in f"{records_description} {records_defaults.get('noValue', '')}"
    )


def test_pipeline_runtime_data_panel_titles_are_action_first() -> None:
    allowed_prefixes = (
        "Monitor ",
        "Inspect ",
        "Track ",
        "Review ",
        "Compare ",
        "Start ",
        "First Action",
    )
    shared_panel_titles = {
        "Understand Pipeline Scope",
        "Monitor Pipeline Status",
        "Inspect Pipeline Identity",
        "Inspect Processed Records",
        "Review Runtime Blockers",
        "Monitor Metrics Coverage",
        "Monitor Monitor Runtime Error Rate",
        "Monitor Monitor Failed Runs",
        "Monitor Monitor Worst Stage Lag",
        "Track Failed Workflow Runs",
        "Track Failed Workflow Steps",
    }
    offenders = [
        panel.get("title", "<untitled>")
        for panel in get_dashboard_panels(_dashboard())
        if panel.get("type") not in {"row", "text"}
        and isinstance(panel.get("title"), str)
        and not panel["title"].startswith(allowed_prefixes)
        and panel["title"] not in shared_panel_titles
        and not str(panel["title"]).startswith("Failed ")
        and not str(panel["title"]).startswith("Workflow ")
    ]
    assert not offenders, (
        "Runtime dashboard data panels must use action-first titles:\n"
        + "\n".join(offenders)
    )


def test_pipeline_runtime_count_panels_have_window_in_title_or_description() -> None:
    titles = {
        "Monitor Runtime Blockers",
        "Monitor Monitor Failed Runs",
        "Monitor No-Records Runs",
        "Monitor Monitor Runtime Error Rate",
        "Monitor Monitor Worst Stage Lag",
        "Monitor Memory Pressure Active",
        "Inspect Entities Stale Over 24h",
        "Inspect Warning Logs (1h)",
        "Inspect GLOBAL Unstructured Logs (1h)",
        "Inspect Top Warning Events by Event / Logger / Range",
        "Review Errors by Stage & Code",
        "Compare Records by Stage & Run Type",
        "Track Global Shutdown Starts",
        "Track Global Shutdown Completions",
    }
    offenders = []
    for panel in _runtime_data_panels():
        title = panel.get("title", "")
        if title not in titles:
            continue
        description = panel.get("description", "")
        windowed = any(
            token in f"{title} {description}"
            for token in (
                "15m",
                "30m",
                "1h",
                "24h",
                "Range",
                "Interval",
                "range",
                "current",
                "fixed",
                "minutes",
            )
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
        "Track Phase Duration",
        "Track Pipeline Duration",
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
    blockers_panel = panels.get("Monitor Runtime Blockers")
    assert blockers_panel is not None, "Monitor Runtime Blockers panel is missing"
    expr = blockers_panel["targets"][0]["expr"]
    assert "bioetl_runtime_current_blocker_reason" in expr
    assert 'stage=~"$stage"' not in expr, (
        "Runtime Blockers must aggregate canonical blocker reasons without "
        "stage-variable filtering"
    )


def test_runtime_blockers_includes_gold_write_missing() -> None:
    """Runtime Blockers must consume canonical runtime blocker reasons."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    blockers_panel = panels.get("Monitor Runtime Blockers")
    assert blockers_panel is not None
    expr = blockers_panel["targets"][0]["expr"]
    assert "bioetl_runtime_current_blocker_reason" in expr, (
        "Runtime Blockers query must reference canonical blocker reason rule"
    )


def test_runtime_blockers_preserves_unknown_without_inline_conditions() -> None:
    """Runtime Blockers must not turn missing current telemetry into false OK."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    blockers_panel = panels.get("Monitor Runtime Blockers")
    assert blockers_panel is not None
    expr = blockers_panel["targets"][0]["expr"]
    assert "or vector(0)" not in expr
    assert "bioetl_runtime_current_status_trusted" in expr
    assert "== 0" in expr
    assert "bioetl_runtime_alert_condition_" not in expr
    defaults = blockers_panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN"


def test_runtime_current_panels_use_scoped_recording_rules_for_workflow_aliases() -> (
    None
):
    """Runtime current-triage panels must delegate workflow_<pipeline> selectors to rules."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    expected_rules = {
        "Monitor Pipeline Status": ("bioetl_runtime_current_status_trusted",),
        "Review Runtime Blockers": ("bioetl_runtime_current_blocker_reason_scoped",),
        "Monitor Runtime Blockers": (
            "bioetl_runtime_current_blocker_reason_scoped",
            "bioetl_runtime_current_status_trusted",
        ),
    }

    for title, required_tokens in expected_rules.items():
        panel = panels.get(title)
        assert panel is not None, f"Runtime dashboard missing {title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        for token in required_tokens:
            assert token in expr
        assert 'label_replace(vector(1), "pipeline_raw", "$pipeline"' not in expr


def test_top_runtime_blockers_hides_prometheus_metric_name_column() -> None:
    """Top blocker table must not expose the Prometheus __name__ service column."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    panel = panels.get("Review Runtime Blockers")
    assert panel is not None

    organize = next(
        (
            transformation
            for transformation in panel.get("transformations", [])
            if transformation.get("id") == "organize"
        ),
        None,
    )
    assert organize is not None
    assert organize.get("options", {}).get("excludeByName", {}).get("__name__") is True


def test_active_runtime_blocker_detail_panel_exists() -> None:
    """Inspect Active Runtime Blocker Detail table panel must be present."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    detail_panel = panels.get("Inspect Active Runtime Blocker Detail")
    assert detail_panel is not None, (
        "Inspect Active Runtime Blocker Detail panel is missing"
    )
    assert detail_panel["type"] == "table"
    targets = detail_panel.get("targets", [])
    canonical_targets = [
        target
        for target in targets
        if "bioetl_runtime_current_blocker_reason" in target.get("expr", "")
    ]
    assert canonical_targets, (
        "Inspect Active Runtime Blocker Detail must include canonical "
        "runtime blocker reason rows, not only derived alert-condition rows"
    )
    blocker_names = set()
    for t in targets:
        expr = t.get("expr", "")
        if "label_replace" in expr:
            for match in re.findall(r'"blocker",\s*"([^"]+)"', expr):
                blocker_names.add(match)
    expected = {
        "preflight_failed",
        "infrastructure_failed",
        "runs_failed",
        "stage_backlog_active",
        "stage_lag_high",
        "gold_write_missing",
        "no_terminal_run",
        "ingestion_throughput_degraded",
        "flow_invariant_violated",
    }
    assert expected <= blocker_names, (
        "Inspect Active Runtime Blocker Detail missing blockers: "
        f"{expected - blocker_names}"
    )


def test_stage_expectedness_panel_exists() -> None:
    """Inspect Stage Expectedness panel must be present on Runtime dashboard."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    panel = panels.get("Inspect Stage Expectedness")
    assert panel is not None, "Inspect Stage Expectedness panel is missing"
    assert panel["type"] == "table"
    expr_texts = [t.get("expr", "") for t in panel.get("targets", [])]
    assert any("bioetl_pipeline_stage_expected" in e for e in expr_texts), (
        "Inspect Stage Expectedness panel must query bioetl_pipeline_stage_expected"
    )


def test_pipeline_duration_has_explicit_no_value_message() -> None:
    """Pipeline Duration panel must show explicit message instead of bare No data."""
    panels = {p.get("title"): p for p in _runtime_data_panels()}
    panel = panels.get("Track Pipeline Duration")
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
        (252, "Inspect Detection Signals"),
        (253, "Localize Runtime Cause"),
        (254, "Review Escalation Paths"),
    ], f"Runtime row order/title drifted: {row_pairs}"


def test_runtime_first_action_cta_contract() -> None:
    """Panel 9991 (First Action) must have exactly 4 CTAs with specific titles."""
    panels = {p.get("id"): p for p in get_dashboard_panels(_dashboard())}
    first_action_panel = panels.get(9991)
    assert first_action_panel is not None, (
        "Runtime dashboard missing First Action panel (id=9991)"
    )
    assert first_action_panel.get("title") == "Start Pipeline Triage", (
        "Panel 9991 must have title 'Start Pipeline Triage', "
        f"got {first_action_panel.get('title')!r}"
    )
    content = str(first_action_panel.get("options", {}).get("content", ""))
    description = str(first_action_panel.get("description", ""))
    assert "continue monitoring" in content
    assert "highest-severity blocker" in content
    assert "SCRAPING" not in content
    assert "verify coverage" in description.lower()
    assert "scraping is telemetry confidence" in description.lower()
    # First Action panel uses panel-level links, not options.dataLinks
    links = first_action_panel.get("links", [])
    assert isinstance(links, list), "First Action panel must have links list"
    assert len(links) == 4, (
        f"First Action panel must have exactly 4 CTAs, got {len(links)}"
    )
    link_titles = {link.get("title") for link in links if isinstance(link, dict)}
    expected_ctas = {
        "Review current status",
        "Review range evidence",
        "Inspect top blockers",
        "Inspect active blocker",
    }
    assert link_titles == expected_ctas, (
        f"First Action CTAs must be {expected_ctas}, got {link_titles}"
    )
