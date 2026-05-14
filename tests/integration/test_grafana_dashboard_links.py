"""Integration tests for Grafana dashboard links and drilldown handoffs."""

from pathlib import Path
import re
import yaml

import pytest
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    _emit_sample_structured_log,
    get_dashboard_navigation_links,
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
_CANONICAL_GITHUB_BLOB_PREFIX = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
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
_DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS = frozenset({"bioetl-control-plane-v1"})


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


def _local_repo_path_from_canonical_github_blob_url(url: str) -> Path | None:
    if not url.startswith(_CANONICAL_GITHUB_BLOB_PREFIX):
        return None
    relative_path = url.removeprefix(_CANONICAL_GITHUB_BLOB_PREFIX).split("?", 1)[0]
    relative_path = relative_path.split("#", 1)[0]
    return Path(relative_path)


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
    assert level_name in {"L1", "L2"}, (
        f"Unexpected level in inbound contract: {level_name}"
    )
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
    assert data_links, (
        f"{dashboard_path.name} panel id={panel_id} must define dataLinks"
    )

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
        assert link.get("includeVars") is False, (
            f"{dashboard_path.name} panel id={panel_id} link {link.get('title')!r} "
            "must keep includeVars=false"
        )
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


def _cross_scope_marker_sections() -> tuple[
    dict[object, object], dict[object, object], dict[object, object]
]:
    marker_contract = _CROSS_SCOPE_MARKER_CONTRACT
    assert isinstance(marker_contract, dict), (
        "cross_scope_marker_contract must be mapping"
    )
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


def _cross_scope_marker_spec(
    *,
    transition: object,
    marker_key: object,
    required_markers: dict[object, object],
    required_tooltip_tokens: dict[object, object],
) -> tuple[str, str, str, list[object]]:
    assert isinstance(marker_key, str), f"marker key for {transition} must be a string"
    marker = required_markers.get(marker_key)
    assert isinstance(marker, str) and marker, (
        f"required marker '{marker_key}' must be declared for transition {transition}"
    )
    tooltip_tokens = required_tooltip_tokens.get(marker_key, [])
    assert isinstance(tooltip_tokens, list), (
        f"required_tooltip_tokens.{marker_key} must be list"
    )
    return str(transition), marker, marker_key, tooltip_tokens


def _cross_scope_marker_specs() -> list[tuple[str, str, str, list[object]]]:
    required_markers, required_titles_by_transition, required_tooltip_tokens = (
        _cross_scope_marker_sections()
    )
    return [
        _cross_scope_marker_spec(
            transition=transition,
            marker_key=marker_key,
            required_markers=required_markers,
            required_tooltip_tokens=required_tooltip_tokens,
        )
        for transition, marker_key in required_titles_by_transition.items()
    ]


def _matching_cross_scope_links(
    source_dashboard: dict[str, object], *, to_uid: str, marker: str
) -> list[dict[str, object]]:
    matched_links: list[dict[str, object]] = []
    for link in get_dashboard_navigation_links(source_dashboard):
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


def _required_dashboard_variable_name(dashboard_name: str) -> str:
    if dashboard_name == "bioetl-provider-health-v2.json":
        return "provider"
    if dashboard_name == "bioetl-workflow-overview.json":
        return "workflow"
    return "pipeline"


def _assert_dashboard_has_required_scope_variable(
    dashboard_path: Path, dashboard: dict[str, object]
) -> None:
    variables = [
        var.get("name") for var in dashboard.get("templating", {}).get("list", [])
    ]
    required_variable = _required_dashboard_variable_name(dashboard_path.name)
    assert required_variable in variables, (
        f"Dashboard {dashboard_path.name} must define '{required_variable}' "
        "template variable"
    )


def _assert_dashboard_link_vars_allowed(
    *, dashboard_name: str, target_uid: str, url: str
) -> set[str]:
    allowed_vars = _ALLOWED_DASHBOARD_LINK_VARS.get(target_uid)
    assert allowed_vars is not None, (
        f"Link target {target_uid} must be declared in allowed vars map"
    )
    passed_vars = _extract_link_vars(url)
    assert passed_vars <= allowed_vars, (
        f"{dashboard_name} link to {target_uid} passes unknown vars: "
        f"{sorted(passed_vars - allowed_vars)} via {url}"
    )
    return passed_vars


def _assert_dashboard_link_vars_not_forbidden(
    *, dashboard_name: str, target_uid: str, url: str, passed_vars: set[str]
) -> None:
    forbidden_vars = _FORBIDDEN_DASHBOARD_LINK_VARS_BY_TARGET_UID.get(target_uid)
    assert forbidden_vars is not None, (
        f"Link target {target_uid} must be declared in forbidden vars map"
    )
    assert not (passed_vars & forbidden_vars), (
        f"{dashboard_name} link to {target_uid} leaks forbidden vars: "
        f"{sorted(passed_vars & forbidden_vars)} via {url}"
    )


def _assert_top_level_cross_dashboard_handoff(
    *,
    dashboard_name: str,
    current_uid: str,
    target_uid: str,
    link: dict[str, object],
    url: str,
    dashboard_links: object,
) -> None:
    if target_uid == current_uid or link not in dashboard_links:
        return
    assert link.get("includeVars") is False, (
        f"{dashboard_name} top-level link to {target_uid} must not "
        "use generic includeVars leakage"
    )
    _assert_required_time_tokens(
        url,
        tokens=_DASHBOARD_TIME_HANDOFF_TOKENS,
        context=f"{dashboard_name} top-level link to {target_uid}",
    )


def _assert_cross_dashboard_link_policy(
    *,
    dashboard_name: str,
    current_uid: str,
    link: dict[str, object],
    dashboard_links: object,
) -> None:
    url = link.get("url", "")
    if not isinstance(url, str) or not url.startswith("/d/"):
        return
    target_uid = _extract_dashboard_uid(url)
    assert target_uid is not None, f"Could not parse dashboard UID from {url}"
    passed_vars = _assert_dashboard_link_vars_allowed(
        dashboard_name=dashboard_name,
        target_uid=target_uid,
        url=url,
    )
    _assert_dashboard_link_vars_not_forbidden(
        dashboard_name=dashboard_name,
        target_uid=target_uid,
        url=url,
        passed_vars=passed_vars,
    )
    _assert_top_level_cross_dashboard_handoff(
        dashboard_name=dashboard_name,
        current_uid=current_uid,
        target_uid=target_uid,
        link=link,
        url=url,
        dashboard_links=dashboard_links,
    )


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
    """Dashboards should not duplicate target UIDs outside explicit panel CTAs."""
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

        allowed_duplicate_targets = {
            str(entry["target_uid"])
            for entry in _REQUIRED_PANEL_LINKS_BY_UID.get(uid, ())
        }
        duplicates = {
            target_uid: links
            for target_uid, links in target_locations.items()
            if len(links) > 1 and target_uid not in allowed_duplicate_targets
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


def test_exact_identifier_variables_do_not_leak_into_other_dashboards() -> None:
    """Exact-id variables must remain isolated to explicitly contracted dashboards."""
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
        if dashboard_path.name in {
            "bioetl-overview-v2.json",
            "bioetl-overview-v3.json",
        }:
            assert "run_id" in variables
            assert "payload_hash" not in variables
            continue
        assert "run_id" not in variables, (
            f"{dashboard_path.name} must not define uncontracted variable run_id"
        )
        assert "payload_hash" not in variables, (
            f"{dashboard_path.name} must not define uncontracted variable payload_hash"
        )


def test_cross_dashboard_links_pass_only_target_scoped_variables() -> None:
    """Cross-dashboard links must not leak unknown variables into the target."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        current_uid = dashboard.get("uid")
        assert isinstance(current_uid, str), (
            f"Dashboard {dashboard_path.name} must define a uid"
        )
        dashboard_links = get_dashboard_navigation_links(dashboard)

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
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"

        required_links = _REQUIRED_TOP_LEVEL_LINKS_BY_UID.get(uid)
        assert required_links is not None, f"Unknown dashboard uid in contract: {uid}"

        titles = {
            link.get("title")
            for link in get_dashboard_navigation_links(dashboard)
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
        for link in get_dashboard_navigation_links(dashboard):
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
        "bioetl-overview-v3": "1. Overview v3",
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
        panel_title = spec.get("panel_title", "First Action")
        min_cta = spec.get("min_cta", 0)
        max_cta = spec.get("max_cta", 0)
        ctas = spec.get("ctas", [])
        assert isinstance(panel_id, int), (
            f"first_action_contract.{source_uid}.panel_id must be integer"
        )
        assert isinstance(panel_title, str), (
            f"first_action_contract.{source_uid}.panel_title must be string"
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
        assert panel.get("title") == panel_title, (
            f"{source_uid} first action panel id={panel_id} must be titled {panel_title!r}"
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
        navigation_links = get_dashboard_navigation_links(dashboard)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url", ""))
            assert not any(token in url for token in forbidden_tokens), (
                f"{dashboard_path.name} link uses forbidden universal handoff pattern: {url}"
            )

            if url.startswith("/d/") and link in navigation_links:
                assert link.get("includeVars") is False, (
                    f"{dashboard_path.name} top-level cross-dashboard link must pin includeVars=false: {url}"
                )


def test_navigation_dashboards_expose_explore_drilldown_links() -> None:
    """Non-control-plane navigation panels should expose Logs and Traces drilldowns."""
    for dashboard_path in get_dashboard_files():
        dashboard_name = dashboard_path.name
        dashboard = load_dashboard(dashboard_path)
        links = get_dashboard_navigation_links(dashboard)
        urls = [link.get("url", "") for link in links]
        uid = str(dashboard.get("uid", ""))

        if uid == "bioetl-control-plane-v1":
            assert not any("/a/grafana-lokiexplore-app/" in url for url in urls), (
                f"{dashboard_name} must not expose top-level Logs Drilldown links"
            )
            assert not any("/a/grafana-exploretraces-app/" in url for url in urls), (
                f"{dashboard_name} must not expose top-level Traces Drilldown links"
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
        content = str((panel.get("options") or {}).get("content", ""))
        assert 'target="_blank"' not in content, (
            f"{dashboard_path.name} navigation panel must open links in the same window"
        )


def test_navigation_panel_renders_full_visual_bus_with_disabled_current_item() -> None:
    """Visual id=1000 bus should show all titles and render current dashboard as disabled."""
    expected_current_title = {
        "bioetl-control-plane-v1": "0. Control Plane",
        "bioetl-overview-v2": "1. Overview",
        "bioetl-overview-v3": "1. Overview v3",
        "bioetl-runtime": "2. Runtime",
        "bioetl-provider-health-v2": "3. Provider Health",
        "bioetl-dq-v2": "4. Data Quality",
        "bioetl-workflow-overview": "5. Workflow",
        "bioetl-silver-reject-explorer": "Silver Reject Explorer",
    }
    base_visual_titles = (
        "0. Control Plane",
        "1. Overview",
        "2. Runtime",
        "3. Provider Health",
        "4. Data Quality",
        "5. Workflow",
        "Silver Reject Explorer",
    )
    explore_visual_titles = ("Explore Logs", "Explore Traces")

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"
        panel = next(
            (item for item in dashboard.get("panels", []) if item.get("id") == 1000),
            None,
        )
        assert panel is not None, (
            f"{dashboard_path.name} must define navigation panel id=1000"
        )
        content = str((panel.get("options") or {}).get("content", ""))
        visual_titles = base_visual_titles
        if uid != "bioetl-control-plane-v1":
            visual_titles += explore_visual_titles
        for title in visual_titles:
            assert title in content, (
                f"{dashboard_path.name} visual navigation bus must render '{title}'"
            )
        if uid == "bioetl-control-plane-v1":
            for title in explore_visual_titles:
                assert title not in content, (
                    f"{dashboard_path.name} visual navigation bus must not render '{title}'"
                )

        current_title = expected_current_title[uid]
        disabled_pattern = re.compile(
            rf'<span[^>]*aria-current="page"[^>]*color:#4b5563[^>]*'
            rf"border:1px solid #4b5563[^>]*>{re.escape(current_title)}</span>"
        )
        assert disabled_pattern.search(content), (
            f"{dashboard_path.name} must render current dashboard '{current_title}' as dark-gray disabled item"
        )
        assert re.search(rf"<a[^>]*>{re.escape(current_title)}</a>", content) is None, (
            f"{dashboard_path.name} must not render current dashboard '{current_title}' as active anchor"
        )


def test_explore_links_use_drilldown_routes_and_time_range() -> None:
    """Non-control-plane Explore links should target Drilldown apps and preserve time range."""
    for dashboard_path in get_dashboard_files():
        dashboard_name = dashboard_path.name
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        drilldown_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
            if _is_logs_drilldown_url(link.get("url", ""))
            or _is_traces_drilldown_url(link.get("url", ""))
        ]
        if dashboard.get("uid") == "bioetl-control-plane-v1":
            assert not drilldown_links, (
                f"{dashboard_name} must not expose top-level Drilldown app links"
            )
            continue
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


def test_explore_traces_navigation_is_explicitly_traced_run_only() -> None:
    """Explore Traces must be described as traced-run-only in shipped navigation."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")

        if uid == "bioetl-control-plane-v1":
            links = get_dashboard_navigation_links(dashboard)
            assert not any(
                str(link.get("title", "")) == "Explore Traces" for link in links
            ), f"{dashboard_path.name} must not expose Explore Traces in top navigation"
            continue

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


def test_tempo_drilldown_routes_to_traces_drilldown_app() -> None:
    """Tempo drilldown links should route to Grafana Traces Drilldown app."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        if dashboard.get("uid") in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS:
            continue
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


def test_loki_drilldown_links_use_safe_bioetl_baseline_query() -> None:
    """Loki drilldown links should start from a low-cardinality baseline query."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        if dashboard.get("uid") in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS:
            continue
        loki_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
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
            tooltip = str(link.get("tooltip", ""))
            assert "Zero lines can legitimately mean" in tooltip, (
                f"{dashboard_name} Loki drilldown must disclose that empty results can be legitimate"
            )
            assert (
                "refine in Explore" in tooltip or "refinement inside Explore" in tooltip
            ), (
                f"{dashboard_name} Loki drilldown must disclose baseline-first refinement workflow"
            )


def test_tempo_drilldown_links_are_contextual() -> None:
    """Tempo drilldown links should carry explicit TraceQL context."""
    pipeline_scoped = (
        "bioetl-dq-v2.json",
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-silver-reject-explorer.json",
    )

    for dashboard_name in pipeline_scoped:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        tempo_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
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

    provider_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    provider_links = [
        link
        for link in get_dashboard_navigation_links(provider_dashboard)
        if _is_traces_drilldown_url(link.get("url", ""))
    ]
    assert provider_links, (
        "bioetl-provider-health-v2.json must expose Tempo drilldown links"
    )
    for link in provider_links:
        url = str(link.get("url", ""))
        assert "queryType=traceqlSearch" in url
        assert "bioetl.provider" in url, (
            "bioetl-provider-health-v2.json Tempo drilldown must scope by provider"
        )
        assert "bioetl.pipeline" not in url and "bioetl.run_type" not in url, (
            "bioetl-provider-health-v2.json Tempo drilldown must not use pipeline/run_type scope"
        )

    workflow_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-workflow-overview.json")
    )
    workflow_links = [
        link
        for link in get_dashboard_navigation_links(workflow_dashboard)
        if _is_traces_drilldown_url(link.get("url", ""))
    ]
    assert workflow_links, (
        "bioetl-workflow-overview.json must expose Tempo drilldown links"
    )
    for link in workflow_links:
        url = str(link.get("url", ""))
        assert "queryType=traceqlSearch" in url
        assert "query=%7B%7D" not in url and "query={}" not in url, (
            "bioetl-workflow-overview.json Tempo drilldown must not use empty trace query payload"
        )
        assert "bioetl.pipeline" in url and "bioetl.run_type" in url, (
            "bioetl-workflow-overview.json Tempo drilldown should use workflow handoff pipeline/run_type scope"
        )


def test_explore_drilldown_links_disclose_tracing_profile_dependency() -> None:
    """Loki/Tempo drilldowns should warn that tracing profile is required."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        for link in get_dashboard_navigation_links(dashboard):
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

    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        if dashboard.get("uid") in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS:
            continue
        loki_links = [
            link
            for link in get_dashboard_navigation_links(dashboard)
            if _is_logs_drilldown_url(link.get("url", ""))
        ]
        assert loki_links, (
            f"{dashboard_name} must expose at least one Logs Drilldown link"
        )
        assert all(
            "/explore?left=" not in link.get("url", "") for link in loki_links
        ), f"{dashboard_name} must not keep legacy Loki Explore payload links"


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
    expectations = (
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
    )

    for dashboard_name in expectations:
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        navigation_links = get_dashboard_navigation_links(dashboard)
        titles = {link.get("title") for link in navigation_links if link.get("title")}
        urls = [link.get("url", "") for link in navigation_links]

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
        navigation_links = get_dashboard_navigation_links(dashboard)
        titles = {link.get("title") for link in navigation_links if link.get("title")}
        urls = [link.get("url", "") for link in navigation_links]

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


def test_navigation_dashboards_expose_silver_reject_explorer_handoff() -> None:
    """Every navigation panel should expose a Silver Reject Explorer handoff."""
    for dashboard_name in (path.name for path in get_dashboard_files()):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_name} must declare string uid"
        links = get_dashboard_navigation_links(dashboard)
        titles = {link.get("title") for link in links if link.get("title")}
        urls = [link.get("url", "") for link in links]

        if uid == "bioetl-silver-reject-explorer":
            assert "Silver Reject Explorer" not in titles, (
                "bioetl-silver-reject-explorer.json must omit top-level self-link"
            )
            continue

        assert "Silver Reject Explorer" in titles, (
            f"{dashboard_name} must expose a Silver Reject Explorer handoff"
        )
        assert any(
            url.startswith("/d/bioetl-silver-reject-explorer") for url in urls
        ), f"{dashboard_name} handoff must target /d/bioetl-silver-reject-explorer"

    explicit_expectations = {
        "bioetl-dq-v2.json": {
            "url_tokens": ("var-pipeline=$pipeline", "var-run_type=$run_type"),
            "tooltip_token": "bounded pipeline/run_type",
        },
        "bioetl-provider-health-v2.json": {
            "url_tokens": ("var-pipeline=$pipeline_context", "var-run_type=All"),
            "tooltip_token": "Context mapping",
        },
        "bioetl-workflow-overview.json": {
            "url_tokens": (
                "var-pipeline=$pipeline_context",
                "var-run_type=$run_type_context",
            ),
            "tooltip_token": "Context mapping",
        },
    }
    for dashboard_name, expected in explicit_expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        links = get_dashboard_navigation_links(dashboard)
        silver_link = next(
            (
                link
                for link in links
                if str(link.get("url", "")).startswith(
                    "/d/bioetl-silver-reject-explorer"
                )
            ),
            None,
        )
        assert silver_link is not None, (
            f"Silver Reject Explorer link must exist on {dashboard_name}"
        )
        assert silver_link.get("includeVars") is False, (
            f"{dashboard_name} handoff must not pass generic Grafana includeVars into Silver Reject Explorer"
        )
        url = str(silver_link.get("url", ""))
        for token in expected["url_tokens"]:
            assert token in url, (
                f"{dashboard_name} handoff must preserve expected bounded Silver explorer vars via token {token!r}"
            )
        assert expected["tooltip_token"] in str(silver_link.get("tooltip", "")), (
            f"{dashboard_name} handoff tooltip should document {expected['tooltip_token']!r} policy"
        )
