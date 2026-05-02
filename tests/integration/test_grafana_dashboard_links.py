"""Integration tests for Grafana dashboard links and drilldown handoffs."""

from pathlib import Path
import re

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    _emit_sample_structured_log,
    get_dashboard_files,
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_DASHBOARD_UID_RE = re.compile(r"^/d/([^/?]+)")
_LINK_VAR_RE = re.compile(r"(?:\?|&)var-([A-Za-z_]+)=")
_ALLOWED_DASHBOARD_LINK_VARS = {
    "bioetl-overview-v2": frozenset({"pipeline", "run_type"}),
    "bioetl-dq-v2": frozenset({"pipeline", "run_type", "stage"}),
    "bioetl-runtime": frozenset({"pipeline", "run_type", "stage"}),
    "bioetl-provider-health-v2": frozenset({"provider", "adapter"}),
    "bioetl-control-plane-v1": frozenset({"pipeline", "run_type"}),
    "bioetl-workflow-overview": frozenset({"workflow", "status"}),
    "bioetl-silver-reject-explorer": frozenset(
        {"pipeline", "run_type", "reason_code", "field", "run_id", "payload_hash"}
    ),
}


def _extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    return match.group(1) if match is not None else None


def _extract_link_vars(url: str) -> set[str]:
    return set(_LINK_VAR_RE.findall(url))


def _is_logs_drilldown_url(url: str) -> bool:
    return "/a/grafana-lokiexplore-app/" in url


def _is_traces_drilldown_url(url: str) -> bool:
    return "/a/grafana-exploretraces-app/" in url


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


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_queries_do_not_filter_by_payload_hash_label(
    dashboard_path: Path,
) -> None:
    """Dashboards must not use payload_hash as a Prometheus label selector."""
    dashboard = load_dashboard(dashboard_path)
    expressions = get_panel_expressions(dashboard)

    offenders = [
        expr
        for expr in expressions
        if re.search(r"\bpayload_hash\s*(=|=~|!=|!~)\s*", expr) is not None
    ]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} must not filter by payload_hash label.\n"
        + "\n".join(offenders[:10])
    )


def test_explorer_only_forensic_variables_do_not_leak_into_other_dashboards() -> None:
    """run_id/payload_hash variables must remain isolated to the reject explorer."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        variables = {
            variable.get("name")
            for variable in dashboard.get("templating", {}).get("list", [])
            if variable.get("name")
        }
        if dashboard_path.name == "bioetl-silver-reject-explorer.json":
            assert {"run_id", "payload_hash"} <= variables
            continue
        assert "run_id" not in variables, (
            f"{dashboard_path.name} must not define explorer-only variable run_id"
        )
        assert "payload_hash" not in variables, (
            f"{dashboard_path.name} must not define explorer-only variable payload_hash"
        )


def test_cross_dashboard_links_pass_only_target_scoped_variables() -> None:
    """Cross-dashboard links must not leak unknown variables into the target."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        current_uid = dashboard.get("uid")
        assert isinstance(current_uid, str), (
            f"Dashboard {dashboard_path.name} must define a uid"
        )

        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            if not isinstance(url, str) or not url.startswith("/d/"):
                continue

            target_uid = _extract_dashboard_uid(url)
            assert target_uid is not None, f"Could not parse dashboard UID from {url}"
            allowed_vars = _ALLOWED_DASHBOARD_LINK_VARS.get(target_uid)
            assert allowed_vars is not None, (
                f"Link target {target_uid} must be declared in allowed vars map"
            )

            passed_vars = _extract_link_vars(url)
            assert passed_vars <= allowed_vars, (
                f"{dashboard_path.name} link to {target_uid} passes unknown vars: "
                f"{sorted(passed_vars - allowed_vars)} via {url}"
            )

            if target_uid != current_uid and link in dashboard.get("links", []):
                assert link.get("includeVars") is False, (
                    f"{dashboard_path.name} top-level link to {target_uid} must not "
                    "use generic includeVars leakage"
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


def test_loki_drilldown_links_use_safe_bioetl_baseline_query() -> None:
    """Loki drilldown links should start from a low-cardinality baseline query."""
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
        assert loki_links, f"{dashboard_name} must expose Loki drilldown links"
        for link in loki_links:
            url = link.get("url", "")
            assert "%7Bjob%3D%22bioetl%22%7D" in url or '{job="bioetl"}' in url, (
                f"{dashboard_name} Loki drilldown must prepopulate safe bioetl baseline"
            )
            assert "${pipeline" not in url and "${provider" not in url, (
                f"{dashboard_name} Loki drilldown must not bake dashboard variables "
                "into encoded query payload"
            )


def test_tempo_drilldown_links_are_contextual() -> None:
    """Tempo drilldown links should carry explicit TraceQL context."""
    pipeline_scoped = (
        "bioetl-overview-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
        "bioetl-control-plane-v1.json",
        "bioetl-silver-reject-explorer.json",
    )
    provider_scoped = ("bioetl-provider-health-v2.json",)

    for dashboard_name in pipeline_scoped:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        tempo_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert tempo_links, f"{dashboard_name} must expose Tempo drilldown links"
        for link in tempo_links:
            url = link.get("url", "")
            assert "queryType=traceqlSearch" in url, (
                f"{dashboard_name} Tempo drilldown must declare TraceQL search mode"
            )
            assert "bioetl.pipeline" in url and "bioetl.run_type" in url, (
                f"{dashboard_name} Tempo drilldown must scope by pipeline/run_type"
            )
            assert "bioetl.provider" not in url, (
                f"{dashboard_name} pipeline drilldown must not switch to provider-only scope"
            )

    for dashboard_name in provider_scoped:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        tempo_links = [
            link
            for link in _collect_dashboard_links(dashboard)
            if _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert tempo_links, f"{dashboard_name} must expose Tempo drilldown links"
        for link in tempo_links:
            url = link.get("url", "")
            assert "queryType=traceqlSearch" in url
            assert "bioetl.provider" in url, (
                f"{dashboard_name} provider drilldown must scope by provider"
            )
            assert "bioetl.pipeline" not in url and "bioetl.run_type" not in url, (
                f"{dashboard_name} provider drilldown must not fake pipeline scope"
            )


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
        matching_urls = [url for url in urls if url.startswith("/d/bioetl-dq-v2")]
        assert matching_urls, (
            f"{dashboard_name} Data Quality handoff must target /d/bioetl-dq-v2"
        )
        assert any(
            "var-pipeline=$pipeline" in url and "var-run_type=$run_type" in url
            for url in matching_urls
        ), (
            f"{dashboard_name} Data Quality handoff must preserve pipeline/run_type scope"
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
        matching_urls = [
            url
            for url in urls
            if url.startswith("/d/bioetl-control-plane-v1/bioetl-control-plane-v1")
        ]
        assert matching_urls, (
            f"{dashboard_name} Control Plane handoff must target /d/bioetl-control-plane-v1/bioetl-control-plane-v1"
        )
        assert any(
            "var-pipeline=$pipeline" in url and "var-run_type=$run_type" in url
            for url in matching_urls
        ), (
            f"{dashboard_name} Control Plane handoff must preserve pipeline/run_type scope"
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
    assert any(url.startswith("/d/bioetl-silver-reject-explorer") for url in urls), (
        "Data Quality handoff must target /d/bioetl-silver-reject-explorer"
    )
    silver_link = next(
        (
            link
            for link in links
            if str(link.get("url", "")).startswith("/d/bioetl-silver-reject-explorer")
        ),
        None,
    )
    assert silver_link is not None, "Silver Reject Explorer link must exist"
    assert silver_link.get("includeVars") is False, (
        "Data Quality handoff must not pass Prometheus variables into "
        "Silver Reject Explorer"
    )
    url = silver_link.get("url", "")
    assert "var-pipeline=$pipeline" in url and "var-run_type=$run_type" in url, (
        "Data Quality handoff must pass only bounded explorer pipeline/run_type scope"
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


def test_runtime_alert_condition_panels_expose_direct_runbook_links() -> None:
    """Runtime condition-summary panels should route operators directly to runbooks."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expectations = {
        "Pipeline Alert Conditions": (
            "Open Pipeline Failure Runbook",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "DQ Alert Conditions": (
            "Open DQ Failure Runbook",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "Control-plane Alert Conditions": (
            "Open Run Manifest Runbook",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "Provider Alert Conditions": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Freshness Alert Conditions": (
            "Open DQ Freshness Runbook",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "Replay Not Reconstructable": (
            "Open Checkpoint Debugging Runbook",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
    }

    for panel_title, (link_title, expected_suffix) in expectations.items():
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
            (item for item in data_links if item.get("title") == link_title), None
        )
        assert link is not None, (
            f"Panel '{panel_title}' must expose direct runbook handoff"
        )
        url = link.get("url", "")
        assert url.startswith(
            "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
        ), f"Panel '{panel_title}' runbook link must target canonical GitHub docs"
        assert url.endswith(expected_suffix), (
            f"Panel '{panel_title}' runbook link must target {expected_suffix}"
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
