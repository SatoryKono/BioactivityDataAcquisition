"""Integration tests for Grafana dashboard links and drilldown handoffs."""

from html import unescape
from pathlib import Path
import re

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    _emit_sample_structured_log,
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
    require_dashboard_navigation_links,
)
from tests.integration._grafana_dashboard_links_support import (
    # Re-export shared helpers for sibling test modules that historically imported
    # private symbols from this file (e.g. test_grafana_dashboard_cta_links).
    _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS,
    _EXPLORE_TIME_HANDOFF_TOKENS,
    _KPI_OWNERSHIP,
    _NAV_LINK_CONTRACT,
    _REQUIRED_PANEL_LINKS_BY_UID,
    _TOP_LEVEL_LINK_TITLE_RE,
    _assert_critical_panel_entry,
    _assert_cross_dashboard_link_policy,
    _assert_cross_scope_matched_links,
    _assert_dashboard_drilldown_routes_and_time,
    _assert_dashboard_exposes_explore_drilldown_links,
    _assert_dashboard_has_required_scope_variable,
    _assert_dashboard_loki_entrypoint,
    _assert_dashboard_loki_safe_baseline,
    _assert_dashboard_top_level_navigation_contract,
    _assert_exact_identifier_variable_isolation,
    _assert_explicit_silver_explorer_policy,
    _assert_first_action_source_contract,
    _assert_inbound_level_payload,
    _assert_kpi_ownership_entry,
    _assert_link_forbids_universal_handoff,
    _assert_named_dashboard_handoff,
    _assert_navigation_panel_visual_bus,
    _assert_no_duplicate_dashboard_targets,
    _assert_pipeline_scoped_tempo_dashboard,
    _assert_primary_identity_handoff_for_dashboard,
    _assert_provider_tempo_drilldown,
    _assert_required_time_tokens,
    _assert_sample_structured_log_fields,
    _assert_silver_explorer_html_bus_forensic_boundary,
    _assert_silver_explorer_presence_for_dashboard,
    _assert_workflow_tempo_drilldown,
    _collect_cross_dashboard_target_locations,
    _cross_scope_marker_specs,
    _extract_dashboard_uid,
    _is_logs_drilldown_url,
    _is_traces_drilldown_url,
    _load_dashboards_by_uid,
    _matching_cross_scope_links,
)

pytestmark = pytest.mark.integration


def test_dashboards_do_not_ship_empty_options_data_links_arrays() -> None:
    """Empty dataLinks arrays are export noise and should not survive in shipped dashboards."""
    offenders: list[str] = []

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            options = panel.get("options")
            if not isinstance(options, dict) or "dataLinks" not in options:
                continue
            links = options.get("dataLinks")
            if isinstance(links, list) and not links:
                offenders.append(
                    f"{dashboard_path.name}:id={panel.get('id')} title={panel.get('title')!r}"
                )

    assert not offenders, (
        "Shipped dashboards must not contain empty options.dataLinks arrays:\n"
        + "\n".join(offenders)
    )


def test_top_level_handoff_fails_closed_when_required_link_is_removed() -> None:
    """The real policy path must reject a removed required dashboard link."""
    link: dict[str, object] = {
        "title": "2. Pipeline Diagnostics",
        "url": (
            "/d/bioetl-runtime?var-workflow=$workflow&var-pipeline=$pipeline"
            "&var-run_type=$run_type&var-run_id=$run_id&from=$__from&to=$__to"
        ),
        "includeVars": False,
    }

    with pytest.raises(AssertionError, match="must be present"):
        _assert_cross_dashboard_link_policy(
            dashboard_name="bioetl-overview-v2.json",
            current_uid="bioetl-overview-v2",
            link=link,
            dashboard_links=[],
        )


def test_empty_navigation_bus_fails_closed_for_required_top_level_contract() -> None:
    """Empty panel id=1000 links must not satisfy required top-level navigation."""
    empty_bus = {
        "uid": "bioetl-overview-v2",
        "panels": [{"id": 1000, "type": "text", "links": []}],
    }
    with pytest.raises(AssertionError, match="non-empty navigation link bus"):
        require_dashboard_navigation_links(
            empty_bus, dashboard_name="bioetl-overview-v2.json"
        )

    partial_bus = {
        "uid": "bioetl-overview-v2",
        "panels": [
            {
                "id": 1000,
                "type": "text",
                "links": [
                    {
                        "title": "Explore Logs",
                        "url": "/a/grafana-lokiexplore-app/",
                    }
                ],
            }
        ],
    }
    with pytest.raises(AssertionError, match="missing required top-level links"):
        _assert_dashboard_top_level_navigation_contract(
            dashboard_name="bioetl-overview-v2.json",
            dashboard=partial_bus,
        )


def test_empty_drilldown_collection_fails_closed() -> None:
    """Drilldown validation must not pass when Logs/Traces links are absent."""
    dashboard = {
        "uid": "bioetl-overview-v2",
        "panels": [
            {
                "id": 1000,
                "type": "text",
                "links": [
                    {
                        "title": "2. Runtime",
                        "url": "/d/bioetl-runtime?var-pipeline=$pipeline",
                    }
                ],
            }
        ],
    }
    with pytest.raises(AssertionError, match="logs drilldown"):
        _assert_dashboard_exposes_explore_drilldown_links(
            dashboard_name="bioetl-overview-v2.json",
            dashboard=dashboard,
        )


def test_missing_critical_panel_data_link_fails_closed() -> None:
    """Critical panel contract must fail when the expected data link is removed."""
    with pytest.raises(AssertionError, match=r"must define dataLinks|must include"):
        _assert_critical_panel_entry(
            dashboard_path=Path("grafana/dashboards/bioetl-overview-v2.json"),
            uid="bioetl-overview-v2",
            panels_by_id={215: {"id": 215, "title": "Status", "options": {}}},
            entry={
                "panel_id": 215,
                "target_uid": "bioetl-runtime",
                "link_titles": ("Open Runtime",),
            },
        )


def test_malformed_navigation_links_collection_fails_closed() -> None:
    """Navigation bus shape errors must raise rather than silently yield zero links."""
    with pytest.raises(AssertionError, match="must be a list"):
        get_dashboard_navigation_links(
            {
                "uid": "bioetl-overview-v2",
                "panels": [{"id": 1000, "type": "text", "links": "not-a-list"}],
            }
        )
    with pytest.raises(AssertionError, match="must be a mapping"):
        get_dashboard_navigation_links(
            {
                "uid": "bioetl-overview-v2",
                "panels": [{"id": 1000, "type": "text", "links": ["bad-entry"]}],
            }
        )
    with pytest.raises(AssertionError, match="navigation panel id=1000"):
        get_dashboard_navigation_links({"uid": "bioetl-overview-v2", "panels": []})


def test_dashboard_to_dashboard_links_are_not_duplicated() -> None:
    """Dashboards should not duplicate target UIDs outside explicit panel CTAs."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"
        target_locations = _collect_cross_dashboard_target_locations(
            dashboard, source_uid=uid
        )
        _assert_no_duplicate_dashboard_targets(
            dashboard_name=dashboard_path.name,
            uid=uid,
            target_locations=target_locations,
        )


def test_kpi_mirror_panels_link_to_canonical_kpi_view() -> None:
    """Mirror KPI panels must include canonical fallback data link."""
    assert isinstance(_KPI_OWNERSHIP, dict), "kpi_ownership must be a mapping"
    dashboards_by_uid = _load_dashboards_by_uid()
    for kpi_name, spec in _KPI_OWNERSHIP.items():
        _assert_kpi_ownership_entry(
            kpi_name=kpi_name,
            spec=spec,
            dashboards_by_uid=dashboards_by_uid,
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

    _assert_dashboard_has_required_scope_variable(dashboard_path, dashboard)


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


@pytest.mark.parametrize(
    "forbidden_label",
    ("manifest_id", "execution_fingerprint", "quarantine_run_id"),
)
@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_queries_do_not_filter_by_high_cardinality_identity_labels(
    dashboard_path: Path, forbidden_label: str
) -> None:
    """Control-plane identity anchors must stay out of Prometheus label filters."""
    dashboard = load_dashboard(dashboard_path)
    expressions = get_panel_expressions(dashboard)

    offenders = [
        expr
        for expr in expressions
        if re.search(rf"\b{re.escape(forbidden_label)}\s*(=|=~|!=|!~)\s*", expr)
        is not None
    ]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} must not filter by {forbidden_label} label.\n"
        + "\n".join(offenders[:10])
    )


def test_exact_identifier_variables_do_not_leak_into_other_dashboards() -> None:
    """Exact-id variables must remain isolated to explicitly contracted dashboards."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        _assert_exact_identifier_variable_isolation(
            dashboard_name=dashboard_path.name,
            dashboard=dashboard,
        )


def test_cross_dashboard_links_pass_only_target_scoped_variables() -> None:
    """Cross-dashboard links must not leak unknown variables into the target."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        current_uid = dashboard.get("uid")
        assert isinstance(current_uid, str), (
            f"Dashboard {dashboard_path.name} must define a uid"
        )
        dashboard_links = require_dashboard_navigation_links(
            dashboard, dashboard_name=dashboard_path.name
        )

        for link in _collect_dashboard_links(dashboard):
            _assert_cross_dashboard_link_policy(
                dashboard_name=dashboard_path.name,
                current_uid=current_uid,
                link=link,
                dashboard_links=dashboard_links,
            )


def test_dashboard_owned_dashboard_links_pin_include_vars_false() -> None:
    """Dashboard-owned /d/ links must disable generic Grafana variable carry-over."""
    offenders: list[str] = []

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            if not isinstance(link, dict):
                continue
            url = str(link.get("url", ""))
            if not url.startswith("/d/"):
                continue
            if link.get("includeVars") is not False:
                offenders.append(
                    f"{dashboard_path.name}:{link.get('title')!r} -> {url}"
                )

    assert not offenders, (
        "Shipped dashboard-owned /d/ links must pin includeVars=false:\n"
        + "\n".join(offenders)
    )


def test_dashboard_top_level_navigation_contract_by_uid() -> None:
    """Each dashboard UID must expose required top-level navigation links."""
    for dashboard_path in get_dashboard_files():
        _assert_dashboard_top_level_navigation_contract(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(dashboard_path),
        )


def test_required_discoverable_inbound_paths_have_panel_level_links_and_policy() -> (
    None
):
    """Contract inbound routes must exist via panel links and obey vars/time policy."""
    inbound = _NAV_LINK_CONTRACT["required_discoverable_inbound_paths"]
    assert isinstance(inbound, dict), (
        "required_discoverable_inbound_paths must be a mapping"
    )

    dashboards = _load_dashboards_by_uid()

    for level_name, level_payload in inbound.items():
        _assert_inbound_level_payload(
            level_name=level_name,
            level_payload=level_payload,
            dashboards=dashboards,
        )


def test_critical_top_level_links_follow_title_allowlist_and_scope_reset_suffix() -> (
    None
):
    """Critical top-level links must follow title style-guide and scope-reset tooltip contract."""
    critical_dashboards = (
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-control-plane-v1.json",
    )
    for dashboard_name in critical_dashboards:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in require_dashboard_navigation_links(
            dashboard, dashboard_name=dashboard_name
        ):
            title = str(link.get("title", ""))
            assert _TOP_LEVEL_LINK_TITLE_RE.match(title), (
                f"{dashboard_name} contains non-conforming top-level link title: {title}"
            )
            tooltip = str(link.get("tooltip", "") or "")
            if "Cross-scope handoff" in tooltip:
                assert "Scope reset:" in tooltip or "Reset scope:" in tooltip, (
                    f"{dashboard_name} link '{title}' must include 'Scope reset:' or 'Reset scope:' suffix"
                )


def test_dashboard_titles_match_home_dashboard_navigation_names() -> None:
    """Grafana Home > Dashboards uses dashboard.title, so titles must match the navigation map."""
    expected_titles_by_uid = {
        "bioetl-control-plane-v1": "0. Trust",
        "bioetl-overview-v2": "1. Overview",
        "bioetl-runtime": "2. Pipeline Diagnostics",
        "bioetl-provider-health-v2": "3. Provider Health",
        "bioetl-dq-v2": "4. Data Quality",
        "bioetl-incident-v1": "Incident Workspace",
        "bioetl-run-explorer-v1": "Run Explorer",
    }

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert uid in expected_titles_by_uid, (
            f"{dashboard_path.name} has unexpected uid={uid!r}"
        )
        assert dashboard.get("title") == expected_titles_by_uid[uid], (
            f"{dashboard_path.name} title must match Grafana Home navigation name"
        )


def test_required_critical_panel_links_by_uid_contract() -> None:
    """Critical KPI panels must provide first-hop action links by contract."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"
        required_entries = _REQUIRED_PANEL_LINKS_BY_UID.get(uid, ())
        if not required_entries:
            continue

        panels_by_id = {
            panel.get("id"): panel
            for panel in get_dashboard_panels(dashboard)
            if isinstance(panel, dict) and isinstance(panel.get("id"), int)
        }
        for entry in required_entries:
            _assert_critical_panel_entry(
                dashboard_path=dashboard_path,
                uid=uid,
                panels_by_id=panels_by_id,
                entry=entry,
            )


def test_cross_scope_links_use_explicit_reset_or_context_markers() -> None:
    """Cross-scope links must expose explicit marker in title/tooltip."""
    dashboards = _load_dashboards_by_uid()
    for transition, marker, _marker_key, tooltip_tokens in _cross_scope_marker_specs():
        base_transition = transition.split("#", 1)[0]
        from_uid, to_uid = base_transition.split("->", 1)
        source_dashboard = dashboards.get(from_uid)
        assert isinstance(source_dashboard, dict), (
            f"source dashboard for transition {transition} must exist: {from_uid}"
        )

        matched_links = _matching_cross_scope_links(
            source_dashboard, to_uid=to_uid, marker=marker
        )
        _assert_cross_scope_matched_links(
            transition=transition,
            marker=marker,
            tooltip_tokens=tooltip_tokens,
            matched_links=matched_links,
        )


def test_first_action_rows_match_navigation_contract() -> None:
    """First Action rows must match contract-defined panel ids and outgoing CTAs."""
    transition_contract = _NAV_LINK_CONTRACT.get("navigation_transition_contract")
    assert isinstance(transition_contract, dict), (
        "navigation_transition_contract must be mapping"
    )
    first_action_contract = transition_contract.get("first_action_contract")
    assert isinstance(first_action_contract, dict), (
        "first_action_contract must be mapping"
    )
    dashboards_by_uid = _load_dashboards_by_uid()
    for source_uid, spec in first_action_contract.items():
        _assert_first_action_source_contract(
            source_uid=source_uid,
            spec=spec,
            dashboards_by_uid=dashboards_by_uid,
        )


def test_dashboard_links_forbid_universal_handoff_patterns() -> None:
    """Dashboard links must avoid generic includeVars and legacy Explore payloads."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        navigation_links = get_dashboard_navigation_links(dashboard)
        for link in _collect_dashboard_links(dashboard):
            _assert_link_forbids_universal_handoff(
                dashboard_name=dashboard_path.name,
                link=link,
                navigation_links=navigation_links,
            )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_navigation_dashboards_expose_explore_drilldown_links() -> None:
    """Every navigation panel should expose Logs and Traces drilldowns."""
    for dashboard_path in get_dashboard_files():
        _assert_dashboard_exposes_explore_drilldown_links(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(dashboard_path),
        )


def test_dashboard_bus_self_links_are_omitted() -> None:
    """Canonical bus and global adjunct links must omit top-level self-links."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"

        for link in get_dashboard_navigation_links(dashboard):
            url = str(link.get("url", ""))
            if _extract_dashboard_uid(url) != uid:
                continue
            raise AssertionError(
                f"{dashboard_path.name} must not expose unexpected top-level self-link: {url}"
            )


def test_navigation_panel_html_links_open_in_same_window() -> None:
    """Navigation panel id=1000 should not force a new browser tab."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        panel = next(
            (item for item in dashboard.get("panels", []) if item.get("id") == 1000),
            None,
        )
        assert panel is not None, (
            f"{dashboard_path.name} must define navigation panel id=1000"
        )
        content = unescape(str((panel.get("options") or {}).get("content", "")))
        assert 'target="_blank"' not in content, (
            f"{dashboard_path.name} navigation panel must open links in the same window"
        )


def test_navigation_panel_html_bus_preserves_primary_identity_handoff() -> None:
    """Visible id=1000 HTML bus must preserve the same primary vars as panel.links."""
    for dashboard_path in get_dashboard_files():
        _assert_primary_identity_handoff_for_dashboard(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(dashboard_path),
        )


def test_navigation_panel_html_bus_keeps_silver_explorer_forensic_boundary() -> None:
    """Visible links into Silver Reject Explorer must not receive shared run scope."""
    for dashboard_path in get_dashboard_files():
        _assert_silver_explorer_html_bus_forensic_boundary(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(dashboard_path),
        )


def test_navigation_panel_renders_full_visual_bus_with_disabled_current_item() -> None:
    """Visual id=1000 bus should show all titles and render current dashboard as disabled."""
    for dashboard_path in get_dashboard_files():
        _assert_navigation_panel_visual_bus(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(dashboard_path),
        )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_explore_links_use_drilldown_routes_and_time_range() -> None:
    """Every dashboard Explore link should target Drilldown apps and preserve time range."""
    dashboard_paths = [
        path
        for path in get_dashboard_files()
        if load_dashboard(path).get("uid") not in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS
    ]
    assert dashboard_paths, "at least one dashboard must own Drilldown navigation"
    for dashboard_path in dashboard_paths:
        _assert_dashboard_drilldown_routes_and_time(
            dashboard_name=dashboard_path.name,
            dashboard=load_dashboard(Path("grafana/dashboards") / dashboard_path.name),
        )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_explore_traces_navigation_is_explicitly_traced_run_only() -> None:
    """Explore Traces must be described as traced-run-only in shipped navigation."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        traces_link = next(
            (
                link
                for link in get_dashboard_navigation_links(dashboard)
                if str(link.get("title", "")) == "Explore Traces"
            ),
            None,
        )
        assert traces_link is not None, (
            f"{dashboard_path.name} must expose Explore Traces in navigation"
        )
        tooltip = str(traces_link.get("tooltip", ""))
        assert "Available only for traced runs" in tooltip, (
            f"{dashboard_path.name} Explore Traces tooltip must say it is traced-run-only"
        )
        assert "--tracing" in tooltip, (
            f"{dashboard_path.name} Explore Traces tooltip must explain how to enable tracing"
        )
        assert "adjunct evidence" in tooltip, (
            f"{dashboard_path.name} Explore Traces tooltip must disclose adjunct-only semantics"
        )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_tempo_drilldown_routes_to_traces_drilldown_app() -> None:
    """Tempo drilldown links should route to Grafana Traces Drilldown app."""
    dashboards = [
        (path.name, load_dashboard(path))
        for path in get_dashboard_files()
        if load_dashboard(path).get("uid") not in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS
    ]
    assert dashboards, "at least one dashboard must own Tempo Drilldown navigation"
    for dashboard_name, dashboard in dashboards:
        tempo_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
            if _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert tempo_links, (
            f"{dashboard_name} must expose at least one Traces Drilldown link"
        )
        for link in tempo_links:
            url = link.get("url", "")
            _assert_required_time_tokens(
                url,
                tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
                context=f"{dashboard_name} traces drilldown link",
            )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_loki_drilldown_links_use_safe_bioetl_baseline_query() -> None:
    """Loki drilldown links should start from a low-cardinality baseline query."""
    dashboards = [
        (path.name, load_dashboard(path))
        for path in get_dashboard_files()
        if load_dashboard(path).get("uid") not in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS
    ]
    assert dashboards, "at least one dashboard must own Loki Drilldown navigation"
    for dashboard_name, dashboard in dashboards:
        _assert_dashboard_loki_safe_baseline(
            dashboard_name=dashboard_name, dashboard=dashboard
        )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_tempo_drilldown_links_are_contextual() -> None:
    """Tempo drilldown links should carry explicit TraceQL context."""
    pipeline_scoped = (
        "bioetl-dq-v2.json",
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
    )
    for dashboard_name in pipeline_scoped:
        _assert_pipeline_scoped_tempo_dashboard(dashboard_name)
    _assert_provider_tempo_drilldown()
    _assert_workflow_tempo_drilldown()


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_explore_drilldown_links_disclose_tracing_profile_dependency() -> None:
    """Loki/Tempo drilldowns should warn that tracing profile is required."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        drilldown_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
            if _is_logs_drilldown_url(link.get("url", ""))
            or _is_traces_drilldown_url(link.get("url", ""))
        ]
        assert drilldown_links, f"{dashboard_name} must expose Drilldown links"
        for link in drilldown_links:
            title = link.get("title", "")
            tooltip = str(link.get("tooltip", ""))
            description = " ".join((title, tooltip)).lower()
            assert "tracing" in description, (
                f"{dashboard_name} Drilldown link must disclose tracing profile dependency"
            )


@pytest.mark.skip(reason="Loki/Tempo Explore drilldowns removed 2026-07-23")
def test_loki_drilldown_uses_grafana_logs_drilldown_entrypoint() -> None:
    """Loki drilldown should route to Grafana Logs Drilldown app entrypoint."""
    sample_line = _emit_sample_structured_log(
        pipeline="chembl_activity",
        provider="chembl",
    )
    _assert_sample_structured_log_fields(sample_line)
    for dashboard_name in (path.name for path in get_dashboard_files()):
        _assert_dashboard_loki_entrypoint(
            dashboard_name=dashboard_name,
            dashboard=load_dashboard(Path("grafana/dashboards") / dashboard_name),
        )


def test_loki_baseline_guidance_matches_shipped_structured_log_fields() -> None:
    """Docs and drilldowns should match the shipped structured-log refinement path."""
    sample_line = _emit_sample_structured_log(
        pipeline="chembl_activity",
        provider="chembl",
    )
    assert re.search(r'"pipeline"\s*:\s*"chembl_activity"', sample_line)
    assert re.search(r'"provider"\s*:\s*"chembl"', sample_line)
    assert re.search(r'"stage"\s*:\s*"extract"', sample_line)

    grafana_readme = Path("grafana/README.md").read_text(encoding="utf-8")
    monitoring_guide = Path("docs/05-operations/01-monitoring-guide.md").read_text(
        encoding="utf-8"
    )

    for content, label in (
        (grafana_readme, "grafana/README.md"),
        (monitoring_guide, "docs/05-operations/01-monitoring-guide.md"),
    ):
        assert '{job="bioetl"}' in content, (
            f"{label} must document the canonical Loki baseline query"
        )
        assert "Zero lines" in content or "Empty Explore results" in content, (
            f"{label} must disclose legitimate empty-result scenarios"
        )

    assert "reports/logs/bioetl.log" in monitoring_guide, (
        "Monitoring guide must explain the local shipped-log fallback for Loki triage"
    )
    assert "pipeline" in monitoring_guide and "provider" in monitoring_guide, (
        "Monitoring guide must direct refinement by structured-log fields after the baseline query"
    )


def test_overview_and_runtime_dashboards_expose_data_quality_handoff() -> None:
    """Overview and Runtime should offer an explicit handoff into DQ triage."""
    for dashboard_name in ("bioetl-overview-v2.json", "bioetl-runtime.json"):
        _assert_named_dashboard_handoff(
            dashboard_name=dashboard_name,
            expected_title="4. Data Quality",
            url_prefix="/d/bioetl-dq-v2",
        )


def test_runtime_and_dq_dashboards_expose_control_plane_handoff() -> None:
    """Runtime and DQ should offer an explicit handoff into control-plane triage."""
    for dashboard_name in ("bioetl-runtime.json", "bioetl-dq-v2.json"):
        _assert_named_dashboard_handoff(
            dashboard_name=dashboard_name,
            expected_title="0. Trust",
            url_prefix="/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
        )


def test_navigation_dashboards_do_not_expose_removed_silver_reject_explorer() -> None:
    """Silver Reject Explorer was removed; no handoff must remain."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        _assert_silver_explorer_presence_for_dashboard(
            dashboard_name=dashboard_name,
            dashboard=load_dashboard(Path("grafana/dashboards") / dashboard_name),
        )
        _assert_explicit_silver_explorer_policy(
            dashboard_name=dashboard_name, expected={}
        )
