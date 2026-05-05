"""Integration tests for Grafana dashboard links and drilldown handoffs."""

from pathlib import Path
import re
import yaml

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

_DASHBOARD_UID_RE = re.compile(r"^/d/([^\\/?]+)")
_LINK_VAR_RE = re.compile(r"[?&]var-(\w+)=")
_NAV_LINK_CONTRACT_PATH = Path(
    "docs/03-guides/dashboards/contracts/navigation-links.yaml"
)


def _load_navigation_links_contract() -> dict[str, object]:
    with _NAV_LINK_CONTRACT_PATH.open("r", encoding="utf-8") as stream:
        raw_contract = yaml.safe_load(stream)

    def _as_frozenset_map(section_name: str) -> dict[str, frozenset[str]]:
        raw_map = raw_contract.get(section_name, {})
        assert isinstance(raw_map, dict), f"{section_name} must be a mapping"
        result: dict[str, frozenset[str]] = {}
        for uid, values in raw_map.items():
            assert isinstance(uid, str), f"{section_name} keys must be strings"
            assert isinstance(values, list), f"{section_name}.{uid} must be a list"
            result[uid] = frozenset(str(v) for v in values)
        return result

    raw_required_panel_links = raw_contract.get("required_panel_links_by_uid", {})
    assert isinstance(raw_required_panel_links, dict), (
        "required_panel_links_by_uid must be a mapping"
    )
    required_panel_links_by_uid: dict[str, tuple[dict[str, object], ...]] = {}
    for uid, entries in raw_required_panel_links.items():
        assert isinstance(uid, str), "required_panel_links_by_uid keys must be strings"
        assert isinstance(entries, list), (
            f"required_panel_links_by_uid.{uid} must be a list"
        )
        normalized_entries: list[dict[str, object]] = []
        for entry in entries:
            assert isinstance(entry, dict), (
                f"required_panel_links_by_uid.{uid} entries must be mappings"
            )
            panel_id = entry.get("panel_id")
            target_uid = entry.get("target_uid")
            link_titles = entry.get("link_titles", [])
            assert isinstance(panel_id, int), (
                f"required_panel_links_by_uid.{uid}.panel_id must be integer"
            )
            assert isinstance(target_uid, str), (
                f"required_panel_links_by_uid.{uid}.target_uid must be string"
            )
            assert isinstance(link_titles, list), (
                f"required_panel_links_by_uid.{uid}.link_titles must be a list"
            )
            normalized_entries.append(
                {
                    "panel_id": panel_id,
                    "target_uid": target_uid,
                    "link_titles": tuple(str(title) for title in link_titles),
                }
            )
        required_panel_links_by_uid[uid] = tuple(normalized_entries)

    return {
        "allowed_dashboard_link_vars": _as_frozenset_map("allowed_dashboard_link_vars"),
        "forbidden_dashboard_link_vars_by_target_uid": _as_frozenset_map(
            "forbidden_dashboard_link_vars_by_target_uid"
        ),
        "required_link_vars_by_target_uid": _as_frozenset_map(
            "required_link_vars_by_target_uid"
        ),
        "required_top_level_links_by_uid": _as_frozenset_map(
            "required_top_level_links_by_uid"
        ),
        "required_discoverable_inbound_paths": raw_contract.get(
            "required_discoverable_inbound_paths", {}
        ),
        "required_panel_links_by_uid": required_panel_links_by_uid,
        "cross_scope_marker_contract": raw_contract.get(
            "cross_scope_marker_contract", {}
        ),
        "navigation_transition_contract": raw_contract.get(
            "navigation_transition_contract", {}
        ),
        "kpi_ownership": raw_contract.get("kpi_ownership", {}),
    }


_NAV_LINK_CONTRACT = _load_navigation_links_contract()
_ALLOWED_DASHBOARD_LINK_VARS = _NAV_LINK_CONTRACT["allowed_dashboard_link_vars"]
_FORBIDDEN_DASHBOARD_LINK_VARS_BY_TARGET_UID = _NAV_LINK_CONTRACT[
    "forbidden_dashboard_link_vars_by_target_uid"
]
_REQUIRED_LINK_VARS_BY_TARGET_UID = _NAV_LINK_CONTRACT[
    "required_link_vars_by_target_uid"
]
_REQUIRED_TOP_LEVEL_LINKS_BY_UID = _NAV_LINK_CONTRACT["required_top_level_links_by_uid"]
_TOP_LEVEL_LINK_TITLE_RE = re.compile(
    r"^([0-5]\. .+|Silver Reject Explorer|Explore (Logs|Traces)|Observability Checklist \(runbook\))$"
)
_REQUIRED_PANEL_LINKS_BY_UID = _NAV_LINK_CONTRACT["required_panel_links_by_uid"]
_CROSS_SCOPE_MARKER_CONTRACT = _NAV_LINK_CONTRACT["cross_scope_marker_contract"]
_KPI_OWNERSHIP = _NAV_LINK_CONTRACT["kpi_ownership"]


def _extract_required_time_tokens(section: str) -> tuple[str, ...]:
    requirements = _NAV_LINK_CONTRACT.get("time_handoff_requirements", {})
    assert isinstance(requirements, dict), "time_handoff_requirements must be a mapping"
    section_payload = requirements.get(section, {})
    assert isinstance(section_payload, dict), (
        f"time_handoff_requirements.{section} must be a mapping"
    )
    tokens = section_payload.get("required_tokens", [])
    assert isinstance(tokens, list), (
        f"time_handoff_requirements.{section}.required_tokens must be a list"
    )
    return tuple(str(token) for token in tokens)


def _assert_required_time_tokens(
    url: str, *, tokens: tuple[str, ...], context: str
) -> None:
    for token in tokens:
        assert token in url, f"{context} must include time token '{token}': {url}"


_DASHBOARD_TIME_HANDOFF_TOKENS = _extract_required_time_tokens("dashboard_links")
_EXPLORE_TIME_HANDOFF_TOKENS = _extract_required_time_tokens("explore_links")
_CANONICAL_PAGE_UIDS = frozenset(
    {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-workflow-overview",
    }
)
_EXPLORE_ALLOWED_UIDS = frozenset({"bioetl-runtime", "bioetl-dq-v2"})


def _extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    return match.group(1) if match is not None else None


def _extract_link_vars(url: str) -> set[str]:
    return set(_LINK_VAR_RE.findall(url))


def _is_logs_drilldown_url(url: str) -> bool:
    return "/a/grafana-lokiexplore-app/" in url


def _is_traces_drilldown_url(url: str) -> bool:
    return "/a/grafana-exploretraces-app/" in url


_OVERVIEW_STATUS_PANEL_IDS_BY_TARGET_UID: tuple[tuple[int, str], ...] = (
    (215, "bioetl-runtime"),
    (215, "bioetl-dq-v2"),
    (215, "bioetl-control-plane-v1"),
    (215, "bioetl-provider-health-v2"),
    (215, "bioetl-workflow-overview"),
)


def _iter_panel_data_links(panel: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    options = panel.get("options")
    if isinstance(options, dict):
        links = options.get("dataLinks", [])
        if isinstance(links, list):
            result.extend(link for link in links if isinstance(link, dict))

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    if isinstance(defaults, dict):
        field_links = defaults.get("links", [])
        if isinstance(field_links, list):
            result.extend(link for link in field_links if isinstance(link, dict))
    return result


def _find_panel_by_id(
    dashboard: dict[str, object], panel_id: int
) -> dict[str, object] | None:
    return next(
        (
            candidate
            for candidate in get_dashboard_panels(dashboard)
            if candidate.get("id") == panel_id
        ),
        None,
    )


def _find_status_header_panel(
    dashboard: dict[str, object], title_matcher: str
) -> dict[str, object] | None:
    row_re = re.compile(title_matcher)
    return next(
        (
            candidate
            for candidate in get_dashboard_panels(dashboard)
            if isinstance(candidate.get("title"), str)
            and row_re.search(candidate["title"]) is not None
        ),
        None,
    )


def _assert_l1_inbound_status_policy(
    *,
    source_dashboard: dict[str, object],
    panel: dict[str, object],
    source_uid: str,
    panel_id: int,
    target_uid: str,
    title_matcher: str,
) -> None:
    status_header_panel = _find_status_header_panel(source_dashboard, title_matcher)
    assert isinstance(status_header_panel, dict), (
        f"{source_uid}:{panel_id}->{target_uid} must resolve status-row matcher {title_matcher!r}"
    )
    row_y = status_header_panel.get("gridPos", {}).get("y")
    panel_y = panel.get("gridPos", {}).get("y")
    assert isinstance(row_y, int) and isinstance(panel_y, int), (
        f"{source_uid}:{panel_id}->{target_uid} row/panel y gridPos must be integers"
    )
    assert panel_y > row_y, (
        f"{source_uid}:{panel_id}->{target_uid} panel must be on first-screen status row "
        f"below matched header panel {status_header_panel.get('title')!r}"
    )


def _target_panel_links(panel: dict[str, object], target_uid: str) -> list[str]:
    return [
        link["url"]
        for link in _iter_panel_data_links(panel)
        if isinstance(link.get("url"), str)
        and _extract_dashboard_uid(link["url"]) == target_uid
    ]


def _assert_inbound_target_link_policy(
    *, url: str, source_uid: str, panel_id: int, target_uid: str
) -> None:
    passed_vars = _extract_link_vars(url)
    required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID[target_uid]
    forbidden_vars = _FORBIDDEN_DASHBOARD_LINK_VARS_BY_TARGET_UID[target_uid]
    assert required_vars <= passed_vars, (
        f"Inbound path {source_uid}:{panel_id}->{target_uid} missing vars "
        f"{sorted(required_vars - passed_vars)} via {url}"
    )
    assert not (passed_vars & forbidden_vars), (
        f"Inbound path {source_uid}:{panel_id}->{target_uid} leaks forbidden vars "
        f"{sorted(passed_vars & forbidden_vars)} via {url}"
    )
    _assert_required_time_tokens(
        url,
        tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
        context=f"Inbound path {source_uid}:{panel_id}->{target_uid}",
    )


def _assert_inbound_route_policy(
    *,
    level_name: str,
    target_uid: str,
    route: object,
    dashboards: dict[str, dict[str, object]],
) -> None:
    assert isinstance(route, dict), f"{level_name}.{target_uid} route must be mapping"
    source_uid = route.get("source_uid")
    panel_id = route.get("source_panel_id")
    panel_title = route.get("source_panel_title")
    status_row_title_matcher = route.get("source_status_row_panel_title_matcher")
    assert isinstance(source_uid, str)
    assert isinstance(panel_id, int)
    assert isinstance(panel_title, str) and panel_title
    if level_name == "L1":
        assert isinstance(status_row_title_matcher, str) and status_row_title_matcher

    source_dashboard = dashboards.get(source_uid)
    assert isinstance(source_dashboard, dict), (
        f"Source dashboard uid={source_uid} from inbound contract not found"
    )
    panel = _find_panel_by_id(source_dashboard, panel_id)
    assert isinstance(panel, dict), (
        f"Source panel id={panel_id} for {source_uid}->{target_uid} not found"
    )
    assert panel.get("title") == panel_title, (
        f"Source panel id={panel_id} title mismatch: expected {panel_title!r}, got {panel.get('title')!r}"
    )
    if level_name == "L1":
        _assert_l1_inbound_status_policy(
            source_dashboard=source_dashboard,
            panel=panel,
            source_uid=source_uid,
            panel_id=panel_id,
            target_uid=target_uid,
            title_matcher=str(status_row_title_matcher),
        )

    target_links = _target_panel_links(panel, target_uid)
    assert target_links, (
        f"Panel id={panel_id} ({panel_title}) must contain data link to {target_uid}"
    )
    for url in target_links:
        _assert_inbound_target_link_policy(
            url=url, source_uid=source_uid, panel_id=panel_id, target_uid=target_uid
        )


def _assert_inbound_level_payload(
    *,
    level_name: str,
    level_payload: object,
    dashboards: dict[str, dict[str, object]],
) -> None:
    assert level_name in {"L1", "L2"}, f"Unexpected level in inbound contract: {level_name}"
    assert isinstance(level_payload, dict), f"{level_name} payload must be mapping"
    for target_uid, routes in level_payload.items():
        assert isinstance(target_uid, str)
        assert isinstance(routes, list) and routes, (
            f"{level_name}.{target_uid} must declare at least one source panel route"
        )
        for route in routes:
            _assert_inbound_route_policy(
                level_name=level_name,
                target_uid=target_uid,
                route=route,
                dashboards=dashboards,
            )


def _matching_panel_links(
    *,
    data_links: list[dict[str, object]],
    expected_titles: set[object],
    target_uid: object,
) -> list[dict[str, object]]:
    return [
        link
        for link in data_links
        if (not expected_titles or str(link.get("title", "")) in expected_titles)
        and str(link.get("url", "")).startswith(f"/d/{target_uid}/")
    ]


def _assert_critical_panel_entry(
    *,
    dashboard_path: Path,
    uid: str,
    panels_by_id: dict[object, dict[str, object]],
    entry: dict[str, object],
) -> None:
    panel_id = entry["panel_id"]
    target_uid = entry["target_uid"]
    expected_titles = set(entry["link_titles"])
    panel = panels_by_id.get(panel_id)
    assert isinstance(panel, dict), (
        f"{dashboard_path.name} ({uid}) missing critical panel id={panel_id}"
    )

    data_links = _iter_panel_data_links(panel)
    assert data_links, f"{dashboard_path.name} panel id={panel_id} must define dataLinks"

    matching_links = _matching_panel_links(
        data_links=data_links,
        expected_titles=expected_titles,
        target_uid=target_uid,
    )
    assert matching_links, (
        f"{dashboard_path.name} panel id={panel_id} must include at least one "
        f"critical link to target_uid={target_uid} with title in {sorted(expected_titles)}"
    )

    allowed_vars = _ALLOWED_DASHBOARD_LINK_VARS[target_uid]
    for link in matching_links:
        url = str(link.get("url", ""))
        _assert_required_time_tokens(
            url,
            tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
            context=f"{dashboard_path.name} panel id={panel_id}",
        )
        passed_vars = _extract_link_vars(url)
        assert passed_vars <= allowed_vars, (
            f"{dashboard_path.name} panel id={panel_id} link to {target_uid} "
            f"passes non-allowlisted vars: {sorted(passed_vars - allowed_vars)}"
        )


def _cross_scope_marker_sections() -> tuple[dict[object, object], dict[object, object], dict[object, object]]:
    marker_contract = _CROSS_SCOPE_MARKER_CONTRACT
    assert isinstance(marker_contract, dict), "cross_scope_marker_contract must be mapping"
    required_markers = marker_contract.get("required_markers", {})
    assert isinstance(required_markers, dict), "required_markers must be mapping"
    required_titles_by_transition = marker_contract.get(
        "required_titles_by_transition", {}
    )
    assert isinstance(required_titles_by_transition, dict), (
        "required_titles_by_transition must be mapping"
    )
    required_tooltip_tokens = marker_contract.get("required_tooltip_tokens", {})
    assert isinstance(required_tooltip_tokens, dict), (
        "required_tooltip_tokens must be mapping"
    )
    return required_markers, required_titles_by_transition, required_tooltip_tokens


def _cross_scope_marker_specs() -> list[tuple[str, str, str, list[object]]]:
    required_markers, required_titles_by_transition, required_tooltip_tokens = (
        _cross_scope_marker_sections()
    )
    specs: list[tuple[str, str, str, list[object]]] = []
    for transition, marker_key in required_titles_by_transition.items():
        assert isinstance(marker_key, str), (
            f"marker key for {transition} must be a string"
        )
        marker = required_markers.get(marker_key)
        assert isinstance(marker, str) and marker, (
            f"required marker '{marker_key}' must be declared for transition {transition}"
        )
        tooltip_tokens = required_tooltip_tokens.get(marker_key, [])
        assert isinstance(tooltip_tokens, list), (
            f"required_tooltip_tokens.{marker_key} must be list"
        )
        specs.append((str(transition), marker, marker_key, tooltip_tokens))
    return specs


def _matching_cross_scope_links(
    source_dashboard: dict[str, object], *, to_uid: str, marker: str
) -> list[dict[str, object]]:
    matched_links: list[dict[str, object]] = []
    for link in source_dashboard.get("links", []):
        if not isinstance(link, dict):
            continue
        url = link.get("url", "")
        if not isinstance(url, str) or _extract_dashboard_uid(url) != to_uid:
            continue
        title = str(link.get("title", ""))
        tooltip = str(link.get("tooltip", ""))
        if marker in title or marker in tooltip:
            matched_links.append(link)
    return matched_links


def _assert_cross_scope_matched_links(
    *,
    transition: str,
    marker: str,
    tooltip_tokens: list[object],
    matched_links: list[dict[str, object]],
) -> None:
    assert matched_links, (
        f"Missing cross-scope link for {transition} with marker '{marker}'"
    )
    for link in matched_links:
        title = str(link.get("title", ""))
        tooltip = str(link.get("tooltip", ""))
        assert marker in title or marker in tooltip, (
            f"Link title/tooltip must include '{marker}' for transition {transition}: "
            f"{title} {tooltip}"
        )
        for token in tooltip_tokens:
            assert str(token) in tooltip, (
                f"Link tooltip for transition {transition} must include '{token}': {tooltip}"
            )


def test_dashboard_to_dashboard_links_are_not_duplicated() -> None:
    """A dashboard may expose at most one link to any other dashboard UID."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"

        target_locations: dict[str, list[str]] = {}
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            target_uid = _extract_dashboard_uid(url)
            if target_uid is None or target_uid == uid:
                continue
            title = str(link.get("title", ""))
            target_locations.setdefault(target_uid, []).append(f"{title} -> {url}")

        duplicates = {
            target_uid: links
            for target_uid, links in target_locations.items()
            if len(links) > 1
        }
        assert not duplicates, (
            f"{dashboard_path.name} duplicates dashboard links by target UID: {duplicates}"
        )


def test_kpi_mirror_panels_link_to_canonical_kpi_view() -> None:
    """Mirror KPI panels must include canonical fallback data link."""
    assert isinstance(_KPI_OWNERSHIP, dict), "kpi_ownership must be a mapping"

    dashboards_by_uid: dict[str, dict[str, object]] = {}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must define string uid"
        dashboards_by_uid[uid] = dashboard

    for kpi_name, spec in _KPI_OWNERSHIP.items():
        assert isinstance(spec, dict), f"kpi_ownership.{kpi_name} must be a mapping"
        canonical_uid = spec.get("canonical_uid")
        assert isinstance(canonical_uid, str), (
            f"kpi_ownership.{kpi_name}.canonical_uid must be string"
        )

        mirror_panels = spec.get("mirror_panels", [])
        assert isinstance(mirror_panels, list), (
            f"kpi_ownership.{kpi_name}.mirror_panels must be a list"
        )
        for mirror in mirror_panels:
            assert isinstance(mirror, dict), (
                f"kpi_ownership.{kpi_name}.mirror_panels entries must be mappings"
            )
            dashboard_uid = mirror.get("dashboard_uid")
            panel_id = mirror.get("panel_id")
            assert isinstance(dashboard_uid, str), "mirror dashboard_uid must be string"
            assert isinstance(panel_id, int), "mirror panel_id must be integer"

            dashboard = dashboards_by_uid.get(dashboard_uid)
            assert dashboard is not None, (
                f"kpi_ownership.{kpi_name} references unknown dashboard {dashboard_uid}"
            )
            panel = next(
                (
                    panel
                    for panel in get_dashboard_panels(dashboard)
                    if panel.get("id") == panel_id
                ),
                None,
            )
            assert isinstance(panel, dict), (
                f"kpi_ownership.{kpi_name} panel id={panel_id} not found in {dashboard_uid}"
            )
            links = _iter_panel_data_links(panel)
            canonical_link = next(
                (
                    link
                    for link in links
                    if link.get("title") == "Open canonical KPI view"
                ),
                None,
            )
            assert isinstance(canonical_link, dict), (
                f"{dashboard_uid} panel id={panel_id} must define data link "
                "'Open canonical KPI view'"
            )
            url = canonical_link.get("url", "")
            assert isinstance(url, str) and url.startswith(f"/d/{canonical_uid}/"), (
                f"{dashboard_uid} panel id={panel_id} canonical link must target "
                f"/d/{canonical_uid}/, got {url!r}"
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
            forbidden_vars = _FORBIDDEN_DASHBOARD_LINK_VARS_BY_TARGET_UID.get(
                target_uid
            )
            assert forbidden_vars is not None, (
                f"Link target {target_uid} must be declared in forbidden vars map"
            )
            assert not (passed_vars & forbidden_vars), (
                f"{dashboard_path.name} link to {target_uid} leaks forbidden vars: "
                f"{sorted(passed_vars & forbidden_vars)} via {url}"
            )

            if target_uid != current_uid and link in dashboard.get("links", []):
                assert link.get("includeVars") is False, (
                    f"{dashboard_path.name} top-level link to {target_uid} must not "
                    "use generic includeVars leakage"
                )
                _assert_required_time_tokens(
                    url,
                    tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
                    context=f"{dashboard_path.name} top-level link to {target_uid}",
                )


def test_dashboard_top_level_navigation_contract_by_uid() -> None:
    """Each dashboard UID must expose required top-level navigation links."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"

        required_links = _REQUIRED_TOP_LEVEL_LINKS_BY_UID.get(uid)
        assert required_links is not None, f"Unknown dashboard uid in contract: {uid}"

        titles = {
            link.get("title")
            for link in dashboard.get("links", [])
            if isinstance(link.get("title"), str)
        }
        missing = required_links - titles
        assert not missing, (
            f"{dashboard_path.name} ({uid}) is missing required top-level links: "
            f"{sorted(missing)}"
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
        "bioetl-workflow-overview.json",
    )
    for dashboard_name in critical_dashboards:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in dashboard.get("links", []):
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
        "bioetl-control-plane-v1": "0. Control Plane",
        "bioetl-overview-v2": "1. Overview",
        "bioetl-runtime": "2. Runtime",
        "bioetl-provider-health-v2": "3. Provider Health",
        "bioetl-dq-v2": "4. Data Quality",
        "bioetl-workflow-overview": "5. Workflow",
        "bioetl-silver-reject-explorer": "Silver Reject Explorer",
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


def _load_dashboards_by_uid() -> dict[str, dict[str, object]]:
    dashboards: dict[str, dict[str, object]] = {}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"
        dashboards[uid] = dashboard
    return dashboards


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
        assert isinstance(spec, dict), (
            f"first_action_contract.{source_uid} must be mapping"
        )
        panel_id = spec.get("panel_id")
        min_cta = spec.get("min_cta", 0)
        max_cta = spec.get("max_cta", 0)
        ctas = spec.get("ctas", [])
        assert isinstance(panel_id, int), (
            f"first_action_contract.{source_uid}.panel_id must be integer"
        )
        assert isinstance(min_cta, int), (
            f"first_action_contract.{source_uid}.min_cta must be integer"
        )
        assert isinstance(max_cta, int), (
            f"first_action_contract.{source_uid}.max_cta must be integer"
        )
        assert isinstance(ctas, list) and ctas, (
            f"first_action_contract.{source_uid}.ctas must be a non-empty list"
        )
        assert min_cta <= max_cta, (
            f"first_action_contract.{source_uid} has invalid CTA bounds: {min_cta}>{max_cta}"
        )

        dashboard = dashboards_by_uid.get(source_uid)
        assert isinstance(dashboard, dict), (
            f"first_action_contract references unknown uid {source_uid}"
        )

        panels_by_id = {
            panel.get("id"): panel
            for panel in get_dashboard_panels(dashboard)
            if isinstance(panel.get("id"), int)
        }
        panel = panels_by_id.get(panel_id)
        assert panel is not None, (
            f"{source_uid} missing First Action panel with id={panel_id}"
        )
        assert panel.get("title") == "First Action", (
            f"{source_uid} first action panel id={panel_id} must be titled 'First Action'"
        )

        links = panel.get("links")
        assert isinstance(links, list) and links, (
            f"{source_uid} first action panel id={panel_id} must define row links"
        )
        assert min_cta <= len(links) <= max_cta, (
            f"{source_uid} first action panel id={panel_id} must include "
            f"{min_cta}-{max_cta} links, got {len(links)}"
        )

        required_titles = {str(arrow.get("title")) for arrow in ctas}
        actual_titles = {str(link.get("title", "")) for link in links}
        assert required_titles.issubset(actual_titles), (
            f"{source_uid} first action panel id={panel_id} missing CTAs: "
            f"{sorted(required_titles - actual_titles)}"
        )

        for entry in ctas:
            title = entry.get("title")
            expected_target_uid = entry.get("expected_target_uid")
            assert isinstance(title, str), (
                f"first_action_contract.{source_uid}.ctas entry missing title"
            )
            assert isinstance(expected_target_uid, str), (
                f"first_action_contract.{source_uid}.{title} missing expected_target_uid"
            )
            link = next(
                (item for item in links if item.get("title") == title),
                None,
            )
            assert link is not None, (
                f"{source_uid} first action must define CTA link '{title}'"
            )
            assert link.get("includeVars") is False, (
                f"{source_uid} First Action CTA '{title}' must keep includeVars=false"
            )

            url = str(link.get("url", ""))
            assert url, f"{source_uid} First Action CTA '{title}' must define URL"

            if expected_target_uid.startswith("grafana-"):
                assert url.startswith(f"/a/{expected_target_uid}/"), (
                    f"{source_uid} First Action CTA '{title}' must target app {expected_target_uid}"
                )
                _assert_required_time_tokens(
                    url,
                    tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
                    context=f"{source_uid} first action CTA '{title}'",
                )
                continue

            assert url.startswith(f"/d/{expected_target_uid}/"), (
                f"{source_uid} First Action CTA '{title}' must target /d/{expected_target_uid}/"
            )
            required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID.get(expected_target_uid)
            assert required_vars is not None, (
                f"Unknown target UID {expected_target_uid} in first_action_contract"
            )
            allowed_vars = _ALLOWED_DASHBOARD_LINK_VARS[expected_target_uid]
            passed_vars = _extract_link_vars(url)
            assert required_vars <= passed_vars, (
                f"{source_uid} first action CTA '{title}' missing required vars "
                f"{sorted(required_vars - passed_vars)}"
            )
            assert passed_vars <= allowed_vars, (
                f"{source_uid} first action CTA '{title}' passes non-allowlisted vars "
                f"{sorted(passed_vars - allowed_vars)}"
            )
            _assert_required_time_tokens(
                url,
                tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
                context=f"{source_uid} first action CTA '{title}'",
            )


def test_dashboard_links_forbid_universal_handoff_patterns() -> None:
    """Dashboard links must avoid generic includeVars and legacy Explore payloads."""
    forbidden_tokens = ("includeVars=true", "/explore?left=")

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            assert not any(token in url for token in forbidden_tokens), (
                f"{dashboard_path.name} link uses forbidden universal handoff pattern: {url}"
            )

            if url.startswith("/d/") and link in dashboard.get("links", []):
                assert link.get("includeVars") is False, (
                    f"{dashboard_path.name} top-level cross-dashboard link must pin includeVars=false: {url}"
                )


def test_only_runtime_and_dq_dashboards_expose_explore_drilldown_links() -> None:
    """Explore handoffs are intentionally limited to Runtime and Data Quality."""
    expectations = {
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
    }

    for dashboard_path in get_dashboard_files():
        dashboard_name = dashboard_path.name
        dashboard = load_dashboard(dashboard_path)
        links = _collect_dashboard_links(dashboard)
        urls = [link.get("url", "") for link in links]

        if dashboard_name not in expectations:
            assert not any("/a/grafana-lokiexplore-app/" in url for url in urls), (
                f"{dashboard_name} must not expose Logs drilldown"
            )
            assert not any("/a/grafana-exploretraces-app/" in url for url in urls), (
                f"{dashboard_name} must not expose Traces drilldown"
            )
            continue

        titles = {link.get("title") for link in links if link.get("title")}
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
            _assert_required_time_tokens(
                url,
                tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
                context=f"{dashboard_name} drilldown URL",
            )
            assert "/explore?left=" not in url, (
                f"{dashboard_name} drilldown URL must not use legacy /explore payload links"
            )


def test_dashboard_bus_self_links_are_omitted() -> None:
    """Canonical page dashboards must not link to themselves in top navigation."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"

        for link in dashboard.get("links", []):
            url = str(link.get("url", ""))
            assert _extract_dashboard_uid(url) != uid, (
                f"{dashboard_path.name} must not expose top-level self-link: {url}"
            )


def test_explore_links_use_drilldown_routes_and_time_range() -> None:
    """Explore links should target Drilldown apps and preserve current time range."""
    expectations = (
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
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
            _assert_required_time_tokens(
                url,
                tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
                context=f"{dashboard_name} drilldown link",
            )
            assert "/explore?left=" not in url, (
                f"{dashboard_name} drilldown link must not use legacy Explore payload URL"
            )


def test_tempo_drilldown_routes_to_traces_drilldown_app() -> None:
    """Tempo drilldown links should route to Grafana Traces Drilldown app."""
    expectations = (
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
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
            _assert_required_time_tokens(
                url,
                tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
                context=f"{dashboard_name} traces drilldown link",
            )


def test_loki_drilldown_links_use_safe_bioetl_baseline_query() -> None:
    """Loki drilldown links should start from a low-cardinality baseline query."""
    expectations = (
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
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
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
    )

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
            assert "query=%7B%7D" not in url and "query={}" not in url, (
                f"{dashboard_name} Tempo drilldown must not use empty trace query payload"
            )
            assert "bioetl.pipeline" in url and "bioetl.run_type" in url, (
                f"{dashboard_name} Tempo drilldown must scope by pipeline/run_type"
            )
            assert "bioetl.provider" not in url, (
                f"{dashboard_name} pipeline drilldown must not switch to provider-only scope"
            )


def test_explore_drilldown_links_disclose_tracing_profile_dependency() -> None:
    """Loki/Tempo drilldowns should warn that tracing profile is required."""
    expectations = (
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in _collect_dashboard_links(dashboard):
            url = link.get("url", "")
            title = link.get("title", "")
            if not (_is_logs_drilldown_url(url) or _is_traces_drilldown_url(url)):
                continue
            tooltip = str(link.get("tooltip", ""))
            description = " ".join((title, tooltip)).lower()
            assert "tracing" in description, (
                f"{dashboard_name} Drilldown link must disclose tracing profile dependency"
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
        "bioetl-dq-v2.json",
        "bioetl-runtime.json",
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

        assert "0. Control Plane" in titles, (
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

    assert "Silver Reject Explorer" in titles, (
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
    assert "bounded pipeline/run_type" in str(silver_link.get("tooltip", "")), (
        "Data Quality handoff tooltip should document bounded explorer handoff policy"
    )


def test_runtime_incident_panels_do_not_duplicate_control_plane_dashboard_link() -> (
    None
):
    """Runtime incident panels must not duplicate the top-level Control Plane link."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel_titles = {"Control-plane Alert Conditions", "No-Records Runs"}

    for panel_title in panel_titles:
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
        dashboard_links = [
            link
            for link in data_links
            if _extract_dashboard_uid(str(link.get("url", ""))) is not None
        ]
        assert not dashboard_links, (
            f"Panel '{panel_title}' must not duplicate dashboard handoff links"
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
        "GLOBAL Provider Alert Conditions": (
            "Open Provider Incident Runbook",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "Freshness Alert Conditions": (
            "Open DQ Freshness Runbook",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "No-Records Runs": (
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


def test_provider_health_critical_panels_expose_incident_runbook_links() -> None:
    """Provider Health condition panels should point directly to incident-response runbook."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    targets = {
        104: "Open Provider Incident Runbook",
        106: "Open Provider Incident Runbook",
        114: "Open Provider Incident Runbook",
    }

    panels_by_id = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    for panel_id, expected_title in targets.items():
        panel = panels_by_id.get(panel_id)
        assert isinstance(panel, dict), f"Provider Health missing panel id={panel_id}"
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert isinstance(data_links, list) and data_links, (
            f"Provider Health panel id={panel_id} must define dataLinks"
        )
        link = next(
            (item for item in data_links if item.get("title") == expected_title),
            None,
        )
        assert link is not None, (
            f"Provider Health panel id={panel_id} must expose '{expected_title}'"
        )
        url = str(link.get("url", ""))
        assert url == (
            "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
            "docs/05-operations/runbooks/incident-response.md"
        ), f"Provider Health panel id={panel_id} runbook URL must be canonical"


@pytest.mark.skip("Expected panels do not exist in bioetl-runtime.json")
def test_runtime_first_action_cta_links_preserve_scoped_vars_and_time() -> None:
    """Runtime First Action row must use explicit allowlisted vars and preserve time."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected = {
        "Pipeline conditions": ("var-pipeline=$pipeline", "var-run_type=$run_type"),
        "DQ conditions": (
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
            "var-stage=$stage",
        ),
        "Control Plane conditions": (
            "var-pipeline=$pipeline",
            "var-run_type=$run_type",
        ),
        "Provider health checks": ("var-provider=$pipeline", "var-adapter=unknown"),
    }
    forbidden = ("var-workflow=", "var-status=", "var-run_id=", "var-payload_hash=")

    for panel_title, required_tokens in expected.items():
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
        links = panel.get("links", [])
        assert links, f"Panel '{panel_title}' must expose a CTA link"
        link = links[0]
        assert link.get("includeVars") is False, (
            f"Panel '{panel_title}' must keep includeVars=false"
        )
        url = str(link.get("url", ""))
        _assert_required_time_tokens(
            url,
            tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
            context=f"{panel_title} CTA link",
        )
        for token in required_tokens:
            assert token in url, f"Panel '{panel_title}' must include token {token}"
        for token in forbidden:
            assert token not in url, f"Panel '{panel_title}' must not leak {token}"


def test_data_quality_incident_panels_do_not_duplicate_control_plane_dashboard_link() -> (
    None
):
    """DQ panels must not duplicate the top-level Control Plane link."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel_titles = {
        "Data Flow in Range: Bronze -> Silver -> Gold",
        "Lineage Refs Missing",
        "Gold Strict Validation Failures",
    }

    for panel_title in panel_titles:
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
        dashboard_links = [
            link
            for link in data_links
            if _extract_dashboard_uid(str(link.get("url", ""))) is not None
        ]
        assert not dashboard_links, (
            f"Panel '{panel_title}' must not duplicate dashboard handoff links"
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


def test_control_plane_dashboard_does_not_expose_top_level_runbook_link() -> None:
    """Top navigation should contain only dashboard-bus links for Control Plane."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    assert all(
        str(link.get("url", "")).startswith("/d/")
        for link in dashboard.get("links", [])
    ), "Control-plane top navigation must not mix dashboard bus links with runbooks"


def test_cross_dashboard_links_enforce_required_handoff_or_explicit_fallback() -> None:
    """Top-level links must pass required target vars or rely on explicit fallback."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)

        for link in dashboard.get("links", []):
            url = link.get("url", "")
            if not isinstance(url, str) or not url.startswith("/d/"):
                continue

            target_uid = _extract_dashboard_uid(url)
            assert target_uid is not None, f"Could not parse dashboard UID from {url}"

            required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID.get(target_uid)
            assert required_vars is not None, (
                f"Link target {target_uid} must be declared in required vars map"
            )
            passed_vars = _extract_link_vars(url)

            source_vars = {
                var.get("name")
                for var in dashboard.get("templating", {}).get("list", [])
                if var.get("name")
            }
            required_from_source = {var for var in required_vars if var in source_vars}
            missing = required_from_source - passed_vars
            assert not missing, (
                f"{dashboard_path.name} top-level link to {target_uid} must pass available "
                f"required vars {sorted(missing)}. URL: {url}"
            )


def test_provider_dashboard_exposes_single_runtime_link() -> None:
    """Provider Health must not duplicate Runtime handoffs."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    links = dashboard.get("links", [])

    runtime_links = [
        link
        for link in links
        if _extract_dashboard_uid(str(link.get("url", ""))) == "bioetl-runtime"
    ]
    assert len(runtime_links) == 1, (
        "Provider Health must expose exactly one Runtime link"
    )
    runtime_link = runtime_links[0]
    assert runtime_link.get("title") == "2. Runtime"
    runtime_url = str(runtime_link.get("url", ""))
    assert "var-pipeline=$pipeline_context" in runtime_url
    assert "var-run_type=unknown" in runtime_url
    assert "var-stage=unknown" in runtime_url


def test_pipeline_and_provider_variables_are_single_select_unknown_default() -> None:
    """Pipeline and Provider selectors must be single-value fail-closed scopes."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        variables = {
            var.get("name"): var
            for var in dashboard.get("templating", {}).get("list", [])
            if isinstance(var, dict) and var.get("name")
        }
        for variable_name in ("pipeline", "provider"):
            variable = variables.get(variable_name)
            if variable is None:
                continue
            assert variable.get("multi") is False, (
                f"{dashboard_path.name} '{variable_name}' must be single-select"
            )
            current = variable.get("current", {})
            assert isinstance(current, dict)
            if (
                dashboard_path.name == "bioetl-overview-v2.json"
                and variable_name == "pipeline"
            ):
                assert variable.get("includeAll") is True, (
                    "bioetl-overview-v2.json 'pipeline' must default to All so "
                    "the overview landing page renders a meaningful scope"
                )
                assert current.get("value") == "$__all", (
                    "bioetl-overview-v2.json 'pipeline' must default to All"
                )
                continue
            assert variable.get("includeAll") is False, (
                f"{dashboard_path.name} '{variable_name}' must disable All"
            )
            assert current.get("value") == "unknown", (
                f"{dashboard_path.name} '{variable_name}' must default to unknown"
            )


def test_provider_health_handoff_maps_pipeline_and_remembers_return_context() -> None:
    """Pipeline-scoped dashboards map pipeline -> provider and preserve pipeline_context."""
    pipeline_sources = {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-silver-reject-explorer",
    }
    dashboards = _load_dashboards_by_uid()

    for source_uid in pipeline_sources:
        dashboard = dashboards[source_uid]
        link = next(
            item
            for item in dashboard.get("links", [])
            if _extract_dashboard_uid(str(item.get("url", "")))
            == "bioetl-provider-health-v2"
        )
        url = str(link.get("url", ""))
        tooltip = str(link.get("tooltip", ""))
        assert "var-provider=$pipeline" in url
        assert "var-pipeline_context=$pipeline" in url
        assert "var-provider=All" not in url
        assert "Context mapping" in tooltip

    provider_dashboard = dashboards["bioetl-provider-health-v2"]
    provider_vars = {
        var.get("name"): var
        for var in provider_dashboard.get("templating", {}).get("list", [])
        if isinstance(var, dict)
    }
    pipeline_context = provider_vars.get("pipeline_context")
    assert pipeline_context is not None
    assert pipeline_context.get("hide") == 2
    assert pipeline_context.get("current", {}).get("value") == "unknown"

    for target_uid in {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-dq-v2",
    }:
        link = next(
            item
            for item in provider_dashboard.get("links", [])
            if _extract_dashboard_uid(str(item.get("url", ""))) == target_uid
        )
        url = str(link.get("url", ""))
        assert "var-pipeline=$pipeline_context" in url
        assert "var-pipeline=All" not in url


def test_dashboard_links_do_not_use_all_for_pipeline_or_provider() -> None:
    """Unknown is the only explicit fallback for Pipeline/Provider handoff values."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            assert "var-pipeline=All" not in url
            assert "var-provider=All" not in url
