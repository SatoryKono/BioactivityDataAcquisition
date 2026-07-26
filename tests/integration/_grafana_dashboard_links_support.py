"""Private helpers for Grafana dashboard links integration tests."""

from html import unescape
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit
import yaml

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_navigation_links,
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
    require_dashboard_navigation_links,
)


_DASHBOARD_UID_RE = re.compile(r"^/d/([^\\/?]+)")

_LINK_VAR_RE = re.compile(r"[?&]var-(\w+)=")

_LINK_VAR_VALUE_RE = re.compile(r"[?&]var-(\w+)=([^&#]+)")

_NAV_LINK_CONTRACT_PATH = Path(
    "docs/03-guides/dashboards/contracts/navigation-links.yaml"
)


def _as_frozenset_map(raw_map: object, section_name: str) -> dict[str, frozenset[str]]:
    assert isinstance(raw_map, dict), f"{section_name} must be a mapping"
    result: dict[str, frozenset[str]] = {}
    for uid, values in raw_map.items():
        assert isinstance(uid, str), f"{section_name} keys must be strings"
        assert isinstance(values, list), f"{section_name}.{uid} must be a list"
        result[uid] = frozenset(str(v) for v in values)
    return result


def _normalize_required_panel_entry(uid: str, entry: object) -> dict[str, object]:
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
    return {
        "panel_id": panel_id,
        "target_uid": target_uid,
        "link_titles": tuple(str(title) for title in link_titles),
    }


def _normalize_required_panel_links(
    raw_required_panel_links: object,
) -> dict[str, tuple[dict[str, object], ...]]:
    assert isinstance(raw_required_panel_links, dict), (
        "required_panel_links_by_uid must be a mapping"
    )
    required_panel_links_by_uid: dict[str, tuple[dict[str, object], ...]] = {}
    for uid, entries in raw_required_panel_links.items():
        assert isinstance(uid, str), "required_panel_links_by_uid keys must be strings"
        assert isinstance(entries, list), (
            f"required_panel_links_by_uid.{uid} must be a list"
        )
        required_panel_links_by_uid[uid] = tuple(
            _normalize_required_panel_entry(uid, entry) for entry in entries
        )
    return required_panel_links_by_uid


def _load_navigation_links_contract() -> dict[str, object]:
    with _NAV_LINK_CONTRACT_PATH.open("r", encoding="utf-8") as stream:
        raw_contract = yaml.safe_load(stream)

    return {
        "allowed_dashboard_link_vars": _as_frozenset_map(
            raw_contract.get("allowed_dashboard_link_vars", {}),
            "allowed_dashboard_link_vars",
        ),
        "forbidden_dashboard_link_vars_by_target_uid": _as_frozenset_map(
            raw_contract.get("forbidden_dashboard_link_vars_by_target_uid", {}),
            "forbidden_dashboard_link_vars_by_target_uid",
        ),
        "required_link_vars_by_target_uid": _as_frozenset_map(
            raw_contract.get("required_link_vars_by_target_uid", {}),
            "required_link_vars_by_target_uid",
        ),
        "required_top_level_links_by_uid": _as_frozenset_map(
            raw_contract.get("required_top_level_links_by_uid", {}),
            "required_top_level_links_by_uid",
        ),
        "required_discoverable_inbound_paths": raw_contract.get(
            "required_discoverable_inbound_paths", {}
        ),
        "required_panel_links_by_uid": _normalize_required_panel_links(
            raw_contract.get("required_panel_links_by_uid", {})
        ),
        "cross_scope_marker_contract": raw_contract.get(
            "cross_scope_marker_contract", {}
        ),
        "preserved_identity_handoff": raw_contract.get(
            "preserved_identity_handoff", {}
        ),
        "navigation_transition_contract": raw_contract.get(
            "navigation_transition_contract", {}
        ),
        "time_handoff_requirements": raw_contract.get("time_handoff_requirements", {}),
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
    r"^([0-6]\. .+|Silver Reject Explorer|Explore (Logs|Traces)|Observability Checklist \(runbook\))$"
)

_CANONICAL_GITHUB_BLOB_PREFIX = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
)

_REQUIRED_PANEL_LINKS_BY_UID = _NAV_LINK_CONTRACT["required_panel_links_by_uid"]

_CROSS_SCOPE_MARKER_CONTRACT = _NAV_LINK_CONTRACT["cross_scope_marker_contract"]

_PRESERVED_IDENTITY_HANDOFF = _NAV_LINK_CONTRACT["preserved_identity_handoff"]

_KPI_OWNERSHIP = _NAV_LINK_CONTRACT["kpi_ownership"]

_PRIMARY_DASHBOARD_UIDS = frozenset(
    {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-workflow-overview",
    }
)


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

_DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS: frozenset[str] = frozenset()


def _extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    return match.group(1) if match is not None else None


def _extract_link_vars(url: str) -> set[str]:
    vars = set(_LINK_VAR_RE.findall(url))
    if "bioetl-provider-health-v2" in url:
        vars.discard("stage")
    return vars


def _extract_link_var_values(url: str) -> dict[str, str]:
    return dict(_LINK_VAR_VALUE_RE.findall(url))


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


def _extend_link_dicts(
    result: list[dict[str, object]], container: object, key: str
) -> None:
    if not isinstance(container, dict):
        return
    links = container.get(key, [])
    if not isinstance(links, list):
        return
    result.extend(link for link in links if isinstance(link, dict))


def _iter_panel_data_links(panel: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    _extend_link_dicts(result, panel.get("options"), "dataLinks")
    field_config = panel.get("fieldConfig")
    defaults = field_config.get("defaults") if isinstance(field_config, dict) else None
    _extend_link_dicts(result, defaults, "links")
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


def _assert_dashboard_link_vars_required(
    *,
    dashboard_name: str,
    target_uid: str,
    url: str,
    passed_vars: set[str],
) -> None:
    required_vars = _REQUIRED_LINK_VARS_BY_TARGET_UID.get(target_uid)
    assert required_vars is not None, (
        f"Link target {target_uid} must be declared in required vars map"
    )
    missing_vars = required_vars - passed_vars
    assert not missing_vars, (
        f"{dashboard_name} link to {target_uid} missing required handoff vars: "
        f"{sorted(missing_vars)} via {url}"
    )


def _assert_preserved_identity_handoff(
    *,
    dashboard_name: str,
    current_uid: str,
    target_uid: str,
    url: str,
    passed_vars: set[str],
) -> None:
    spec = _PRESERVED_IDENTITY_HANDOFF
    assert isinstance(spec, dict), "preserved_identity_handoff must be a mapping"
    selector = spec.get("selector")
    required_value = spec.get("required_value")
    source_uids = set(spec.get("source_uids", []))
    target_uids = set(spec.get("target_uids", []))
    excluded_source_uids = set(spec.get("excluded_source_uids", []))
    excluded_target_uids = set(spec.get("excluded_target_uids", []))
    assert selector == "run_id", "preserved identity selector must be run_id"
    assert required_value == "$run_id", "preserved run_id handoff value must be $run_id"

    if current_uid in source_uids and target_uid in target_uids:
        values = _extract_link_var_values(url)
        assert selector in passed_vars, (
            f"{dashboard_name} link to {target_uid} must preserve exact Run ID "
            f"with var-{selector}={required_value}: {url}"
        )
        assert values.get(selector) == required_value, (
            f"{dashboard_name} link to {target_uid} must use "
            f"var-{selector}={required_value}, got {values.get(selector)!r}: {url}"
        )
        return

    if current_uid in excluded_source_uids or target_uid in excluded_target_uids:
        assert selector not in passed_vars, (
            f"{dashboard_name} link to {target_uid} must not pass primary "
            f"var-{selector} across excluded identity boundary: {url}"
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
    if target_uid == current_uid:
        return
    assert isinstance(dashboard_links, list), (
        f"{dashboard_name} top-level links must be a list"
    )
    assert link in dashboard_links, (
        f"{dashboard_name} cross-dashboard link to {target_uid} must be "
        "present in the dashboard-level link collection"
    )
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
    if target_uid != current_uid:
        _assert_dashboard_link_vars_required(
            dashboard_name=dashboard_name,
            target_uid=target_uid,
            url=url,
            passed_vars=passed_vars,
        )
        _assert_preserved_identity_handoff(
            dashboard_name=dashboard_name,
            current_uid=current_uid,
            target_uid=target_uid,
            url=url,
            passed_vars=passed_vars,
        )
    required_top_level_titles = _REQUIRED_TOP_LEVEL_LINKS_BY_UID.get(
        current_uid, frozenset()
    )
    is_required_top_level_link = link.get("title") in required_top_level_titles
    if is_required_top_level_link or (
        isinstance(dashboard_links, list) and link in dashboard_links
    ):
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


def _collect_cross_dashboard_target_locations(
    dashboard: dict[str, object], *, source_uid: str
) -> dict[str, list[str]]:
    target_locations: dict[str, list[str]] = {}
    for link in _collect_dashboard_links(dashboard):
        url = str(link.get("url", ""))
        target_uid = _extract_dashboard_uid(url)
        if target_uid is None or target_uid == source_uid:
            continue
        title = str(link.get("title", ""))
        target_locations.setdefault(target_uid, []).append(f"{title} -> {url}")
    return target_locations


def _assert_no_duplicate_dashboard_targets(
    *, dashboard_name: str, uid: str, target_locations: dict[str, list[str]]
) -> None:
    allowed_duplicate_targets = {
        str(entry["target_uid"]) for entry in _REQUIRED_PANEL_LINKS_BY_UID.get(uid, ())
    }
    duplicates = {
        target_uid: links
        for target_uid, links in target_locations.items()
        if len(links) > 1 and target_uid not in allowed_duplicate_targets
    }
    assert not duplicates, (
        f"{dashboard_name} duplicates dashboard links by target UID: {duplicates}"
    )


def _assert_kpi_mirror_panel_canonical_link(
    *,
    kpi_name: str,
    mirror: object,
    canonical_uid: str,
    dashboards_by_uid: dict[str, dict[str, object]],
) -> None:
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
    panel = _find_panel_by_id(dashboard, panel_id)
    assert isinstance(panel, dict), (
        f"kpi_ownership.{kpi_name} panel id={panel_id} not found in {dashboard_uid}"
    )
    links = _iter_panel_data_links(panel)
    canonical_link = next(
        (link for link in links if link.get("title") == "Open canonical KPI view"),
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


def _assert_kpi_ownership_entry(
    *,
    kpi_name: object,
    spec: object,
    dashboards_by_uid: dict[str, dict[str, object]],
) -> None:
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
        _assert_kpi_mirror_panel_canonical_link(
            kpi_name=str(kpi_name),
            mirror=mirror,
            canonical_uid=canonical_uid,
            dashboards_by_uid=dashboards_by_uid,
        )


_LOCAL_IDENTITY_DASHBOARDS = frozenset(
    {
        "bioetl-control-plane-v1.json",
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-workflow-overview.json",
    }
)


def _dashboard_template_variable_names(dashboard: dict[str, object]) -> set[object]:
    return {
        variable.get("name")
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }


def _assert_silver_explorer_identity_variables(variables: set[object]) -> None:
    assert {"quarantine_run_id", "payload_hash"} <= variables
    assert "run_id" not in variables


def _assert_local_identity_variables(variables: set[object]) -> None:
    assert "run_id" in variables
    assert "quarantine_run_id" not in variables
    assert "payload_hash" not in variables


def _assert_no_uncontracted_identity_variables(
    *, dashboard_name: str, variables: set[object]
) -> None:
    assert "run_id" not in variables, (
        f"{dashboard_name} must not define uncontracted variable run_id"
    )
    assert "quarantine_run_id" not in variables, (
        f"{dashboard_name} must not define uncontracted variable quarantine_run_id"
    )
    assert "payload_hash" not in variables, (
        f"{dashboard_name} must not define uncontracted variable payload_hash"
    )


def _assert_exact_identifier_variable_isolation(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    variables = _dashboard_template_variable_names(dashboard)
    if dashboard_name in _LOCAL_IDENTITY_DASHBOARDS:
        _assert_local_identity_variables(variables)
        return
    _assert_no_uncontracted_identity_variables(
        dashboard_name=dashboard_name, variables=variables
    )


def _assert_dashboard_top_level_navigation_contract(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    uid = dashboard.get("uid")
    assert isinstance(uid, str), f"{dashboard_name} must declare string uid"

    required_links = _REQUIRED_TOP_LEVEL_LINKS_BY_UID.get(uid)
    assert required_links is not None, f"Unknown dashboard uid in contract: {uid}"

    navigation_links = require_dashboard_navigation_links(
        dashboard, dashboard_name=dashboard_name
    )
    titles = {
        link.get("title")
        for link in navigation_links
        if isinstance(link.get("title"), str)
    }
    missing = required_links - titles
    assert not missing, (
        f"{dashboard_name} ({uid}) is missing required top-level links: "
        f"{sorted(missing)}"
    )


def _load_dashboards_by_uid() -> dict[str, dict[str, object]]:
    dashboards: dict[str, dict[str, object]] = {}
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str), f"{dashboard_path.name} must declare string uid"
        dashboards[uid] = dashboard
    return dashboards


def _parse_first_action_spec(
    source_uid: object, spec: object
) -> tuple[int, str, int, int, list[object]]:
    assert isinstance(spec, dict), f"first_action_contract.{source_uid} must be mapping"
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
    return panel_id, panel_title, min_cta, max_cta, ctas


def _assert_first_action_panel_shape(
    *,
    source_uid: str,
    dashboard: dict[str, object],
    panel_id: int,
    panel_title: str,
    min_cta: int,
    max_cta: int,
    ctas: list[object],
) -> list[object]:
    panel = _find_panel_by_id(dashboard, panel_id)
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
    return links


def _assert_first_action_app_cta(
    *, source_uid: str, title: str, expected_target_uid: str, url: str
) -> None:
    assert url.startswith(f"/a/{expected_target_uid}/"), (
        f"{source_uid} First Action CTA '{title}' must target app {expected_target_uid}"
    )
    _assert_required_time_tokens(
        url,
        tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
        context=f"{source_uid} first action CTA '{title}'",
    )


def _assert_first_action_dashboard_cta(
    *, source_uid: str, title: str, expected_target_uid: str, url: str
) -> None:
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


def _assert_first_action_cta_entry(
    *, source_uid: str, entry: object, links: list[object]
) -> None:
    title = entry.get("title") if isinstance(entry, dict) else None
    expected_target_uid = (
        entry.get("expected_target_uid") if isinstance(entry, dict) else None
    )
    assert isinstance(title, str), (
        f"first_action_contract.{source_uid}.ctas entry missing title"
    )
    assert isinstance(expected_target_uid, str), (
        f"first_action_contract.{source_uid}.{title} missing expected_target_uid"
    )
    link = next((item for item in links if item.get("title") == title), None)
    assert link is not None, f"{source_uid} first action must define CTA link '{title}'"
    assert link.get("includeVars") is False, (
        f"{source_uid} First Action CTA '{title}' must keep includeVars=false"
    )
    url = str(link.get("url", ""))
    assert url, f"{source_uid} First Action CTA '{title}' must define URL"
    if expected_target_uid.startswith("grafana-"):
        _assert_first_action_app_cta(
            source_uid=source_uid,
            title=title,
            expected_target_uid=expected_target_uid,
            url=url,
        )
        return
    _assert_first_action_dashboard_cta(
        source_uid=source_uid,
        title=title,
        expected_target_uid=expected_target_uid,
        url=url,
    )


def _assert_first_action_source_contract(
    *,
    source_uid: object,
    spec: object,
    dashboards_by_uid: dict[str, dict[str, object]],
) -> None:
    panel_id, panel_title, min_cta, max_cta, ctas = _parse_first_action_spec(
        source_uid, spec
    )
    source_uid_str = str(source_uid)
    dashboard = dashboards_by_uid.get(source_uid_str)
    assert isinstance(dashboard, dict), (
        f"first_action_contract references unknown uid {source_uid_str}"
    )
    links = _assert_first_action_panel_shape(
        source_uid=source_uid_str,
        dashboard=dashboard,
        panel_id=panel_id,
        panel_title=panel_title,
        min_cta=min_cta,
        max_cta=max_cta,
        ctas=ctas,
    )
    for entry in ctas:
        _assert_first_action_cta_entry(
            source_uid=source_uid_str, entry=entry, links=links
        )


_FORBIDDEN_UNIVERSAL_HANDOFF_TOKENS = ("includeVars=true", "/explore?left=")


def _assert_link_forbids_universal_handoff(
    *,
    dashboard_name: str,
    link: dict[str, object],
    navigation_links: list[dict[str, object]],
) -> None:
    url = str(link.get("url", ""))
    assert not any(token in url for token in _FORBIDDEN_UNIVERSAL_HANDOFF_TOKENS), (
        f"{dashboard_name} link uses forbidden universal handoff pattern: {url}"
    )
    if url.startswith("/d/") and link in navigation_links:
        assert link.get("includeVars") is False, (
            f"{dashboard_name} top-level cross-dashboard link must pin includeVars=false: {url}"
        )


def _assert_navigation_has_logs_and_traces_titles(
    *, dashboard_name: str, titles: set[object]
) -> None:
    assert any("Logs" in str(title) for title in titles), (
        f"{dashboard_name} must expose a logs drilldown link"
    )
    assert any("Traces" in str(title) for title in titles), (
        f"{dashboard_name} must expose a traces drilldown link"
    )


def _assert_navigation_has_drilldown_app_urls(
    *, dashboard_name: str, urls: list[object]
) -> list[object]:
    assert any("/a/grafana-lokiexplore-app/" in str(url) for url in urls), (
        f"{dashboard_name} must point logs drilldown to Logs Drilldown app"
    )
    assert any("/a/grafana-exploretraces-app/" in str(url) for url in urls), (
        f"{dashboard_name} must point traces drilldown to Traces Drilldown app"
    )
    drilldown_urls = [
        url
        for url in urls
        if "/a/grafana-lokiexplore-app/" in str(url)
        or "/a/grafana-exploretraces-app/" in str(url)
    ]
    assert drilldown_urls, f"{dashboard_name} must expose Grafana Drilldown app URLs"
    return drilldown_urls


def _assert_drilldown_urls_time_and_no_legacy(
    *, dashboard_name: str, drilldown_urls: list[object]
) -> None:
    for url in drilldown_urls:
        _assert_required_time_tokens(
            str(url),
            tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
            context=f"{dashboard_name} drilldown URL",
        )
        assert "/explore?left=" not in str(url), (
            f"{dashboard_name} drilldown URL must not use legacy /explore payload links"
        )


def _assert_dashboard_exposes_explore_drilldown_links(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    links = require_dashboard_navigation_links(dashboard, dashboard_name=dashboard_name)
    urls = [link.get("url", "") for link in links]
    titles = {link.get("title") for link in links if link.get("title")}
    _assert_navigation_has_logs_and_traces_titles(
        dashboard_name=dashboard_name, titles=titles
    )
    drilldown_urls = _assert_navigation_has_drilldown_app_urls(
        dashboard_name=dashboard_name, urls=urls
    )
    _assert_drilldown_urls_time_and_no_legacy(
        dashboard_name=dashboard_name, drilldown_urls=drilldown_urls
    )


_PRIMARY_IDENTITY_HANDOFF_VARS = frozenset(
    {"workflow", "pipeline", "run_type", "run_id"}
)


def _navigation_panel_by_id_1000(
    dashboard: dict[str, object], *, dashboard_name: str
) -> dict[str, object]:
    panel = next(
        (item for item in dashboard.get("panels", []) if item.get("id") == 1000),
        None,
    )
    assert panel is not None, f"{dashboard_name} must define navigation panel id=1000"
    assert isinstance(panel, dict), (
        f"{dashboard_name} navigation panel id=1000 must be a mapping"
    )
    return panel


def _html_hrefs_from_panel_content(
    panel: dict[str, object], *, prefix: str | None = None
) -> list[str]:
    content = str((panel.get("options") or {}).get("content", ""))
    hrefs = [unescape(match) for match in re.findall(r'href="([^"]+)"', content)]
    if prefix is None:
        return hrefs
    return [href for href in hrefs if href.startswith(prefix)]


def _query_var_values(url: str) -> dict[str, str]:
    return {
        key[4:]: value
        for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True)
        if key.startswith("var-")
    }


def _assert_primary_identity_href(
    *, dashboard_name: str, source_uid: str, href: str
) -> None:
    target_uid = _extract_dashboard_uid(href)
    if target_uid not in _PRIMARY_DASHBOARD_UIDS or target_uid == source_uid:
        return
    query_vars = _query_var_values(href)
    missing = _PRIMARY_IDENTITY_HANDOFF_VARS - set(query_vars)
    assert not missing, (
        f"{dashboard_name} visible navigation link to {target_uid} "
        f"must preserve {sorted(_PRIMARY_IDENTITY_HANDOFF_VARS)}; "
        f"missing {sorted(missing)}: {href}"
    )


def _assert_primary_identity_handoff_for_dashboard(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    source_uid = dashboard.get("uid")
    assert isinstance(source_uid, str), f"{dashboard_name} must declare string uid"
    if source_uid not in _PRIMARY_DASHBOARD_UIDS:
        return
    panel = _navigation_panel_by_id_1000(dashboard, dashboard_name=dashboard_name)
    hrefs = _html_hrefs_from_panel_content(panel, prefix="/d/")
    assert hrefs, f"{dashboard_name} navigation HTML bus must expose links"
    for href in hrefs:
        _assert_primary_identity_href(
            dashboard_name=dashboard_name, source_uid=source_uid, href=href
        )


_SILVER_EXPLORER_ALLOWED_HTML_VARS = frozenset(
    {
        "pipeline",
        "run_type",
        "reason_code",
        "field",
        "quarantine_run_id",
        "payload_hash",
    }
)


def _assert_silver_explorer_href_forensic_boundary(
    *, dashboard_name: str, href: str
) -> None:
    unexpected = set(_query_var_values(href)) - _SILVER_EXPLORER_ALLOWED_HTML_VARS
    assert not unexpected, (
        f"{dashboard_name} visible navigation link to Silver Reject "
        f"Explorer leaks unsupported vars {sorted(unexpected)}: {href}"
    )


def _assert_silver_explorer_html_bus_forensic_boundary(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    """Silver Reject Explorer was removed; assert no residual handoff hrefs."""
    panel = _navigation_panel_by_id_1000(dashboard, dashboard_name=dashboard_name)
    hrefs = _html_hrefs_from_panel_content(panel)
    residual = [href for href in hrefs if "silver-reject" in href]
    assert not residual, (
        f"{dashboard_name} still links to removed Silver Reject Explorer: {residual}"
    )


_EXPECTED_CURRENT_NAV_TITLE = {
    "bioetl-control-plane-v1": "0. Control Plane",
    "bioetl-overview-v2": "1. Overview",
    "bioetl-runtime": "2. Runtime",
    "bioetl-provider-health-v2": "3. Provider Health",
    "bioetl-dq-v2": "4. Data Quality",
    "bioetl-workflow-overview": "5. Workflow",
    "bioetl-alerts-slo": "6. Alerts & SLO",
}

_BASE_VISUAL_NAV_TITLES = (
    "0. Control Plane",
    "1. Overview",
    "2. Runtime",
    "3. Provider Health",
    "4. Data Quality",
    "5. Workflow",
    "6. Alerts & SLO",
)

_OPTIONAL_VISUAL_NAV_TITLES = (
    "Silver Reject Explorer",
    "Explore Logs",
    "Explore Traces",
)

_SANITIZER_SAFE_NAV_TOKENS = (
    "display:flex",
    "flex-wrap:wrap",
    "overflow:visible",
    "flex:1 1 145px",
    "text-align:center",
    "color:#f8fafc",
    "background:#334155",
    "border:1px solid #94a3b8",
    "background:#1d4ed8",
    "border:2px solid #7dd3fc",
)


def _assert_titles_in_order(
    content: str, titles: tuple[str, ...], *, dashboard_name: str
) -> None:
    positions = [content.index(title) for title in titles]
    assert positions == sorted(positions), (
        f"{dashboard_name} must preserve canonical navigation order"
    )


def _assert_visual_bus_base_content(
    *, dashboard_name: str, content: str, panel: dict[str, object]
) -> None:
    for title in _BASE_VISUAL_NAV_TITLES:
        assert title in content, (
            f"{dashboard_name} visual navigation bus must render '{title}'"
        )
    _assert_titles_in_order(
        content, _BASE_VISUAL_NAV_TITLES, dashboard_name=dashboard_name
    )
    assert "<style" not in content.lower(), (
        f"{dashboard_name} navigation must survive Grafana Text-panel "
        "sanitization without a style block"
    )
    for token in _SANITIZER_SAFE_NAV_TOKENS:
        assert token in content, (
            f"{dashboard_name} navigation must define sanitizer-safe {token}"
        )
    description = str(panel.get("description", ""))
    assert "Sanitizer-compatible" in description
    assert "native keyboard focus" in description


def _assert_current_dashboard_disabled_in_visual_bus(
    *, dashboard_name: str, uid: str, content: str
) -> None:
    current_title = _EXPECTED_CURRENT_NAV_TITLE[uid]
    disabled_pattern = re.compile(
        rf'<span[^>]*aria-current="page"[^>]*>{re.escape(current_title)}</span>'
    )
    assert disabled_pattern.search(content), (
        f"{dashboard_name} must render current dashboard '{current_title}' as disabled item"
    )
    assert re.search(rf"<a[^>]*>{re.escape(current_title)}</a>", content) is None, (
        f"{dashboard_name} must not render current dashboard '{current_title}' as active anchor"
    )


def _assert_optional_visual_title_order(visible_optional_titles: list[str]) -> None:
    if (
        "Silver Reject Explorer" in visible_optional_titles
        and "Explore Logs" in visible_optional_titles
    ):
        assert visible_optional_titles.index(
            "Silver Reject Explorer"
        ) < visible_optional_titles.index("Explore Logs")
    if (
        "Explore Logs" in visible_optional_titles
        and "Explore Traces" in visible_optional_titles
    ):
        assert visible_optional_titles.index(
            "Explore Logs"
        ) < visible_optional_titles.index("Explore Traces")


def _assert_visual_bus_optional_order(*, dashboard_name: str, content: str) -> None:
    visible_optional_titles = [
        title for title in _OPTIONAL_VISUAL_NAV_TITLES if title in content
    ]
    all_expected_titles = _BASE_VISUAL_NAV_TITLES + tuple(visible_optional_titles)
    _assert_titles_in_order(content, all_expected_titles, dashboard_name=dashboard_name)
    # Optional adjunct links may be excluded by deployment profile; when present,
    # they should stay in the canonical relative order.
    if visible_optional_titles:
        _assert_optional_visual_title_order(visible_optional_titles)


def _assert_navigation_panel_visual_bus(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    uid = dashboard.get("uid")
    assert isinstance(uid, str), f"{dashboard_name} must declare string uid"
    panel = _navigation_panel_by_id_1000(dashboard, dashboard_name=dashboard_name)
    content = unescape(str((panel.get("options") or {}).get("content", "")))
    _assert_visual_bus_base_content(
        dashboard_name=dashboard_name, content=content, panel=panel
    )
    _assert_current_dashboard_disabled_in_visual_bus(
        dashboard_name=dashboard_name, uid=uid, content=content
    )
    _assert_visual_bus_optional_order(dashboard_name=dashboard_name, content=content)


def _navigation_drilldown_links(
    dashboard: dict[str, object],
) -> list[dict[str, object]]:
    return [
        link
        for link in get_dashboard_navigation_links(dashboard)
        if _is_logs_drilldown_url(link.get("url", ""))
        or _is_traces_drilldown_url(link.get("url", ""))
    ]


def _assert_drilldown_link_time_and_route(
    *, dashboard_name: str, link: dict[str, object]
) -> None:
    url = str(link.get("url", ""))
    _assert_required_time_tokens(
        url,
        tokens=_EXPLORE_TIME_HANDOFF_TOKENS,
        context=f"{dashboard_name} drilldown link",
    )
    assert "/explore?left=" not in url, (
        f"{dashboard_name} drilldown link must not use legacy Explore payload URL"
    )


def _assert_dashboard_drilldown_routes_and_time(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    drilldown_links = _navigation_drilldown_links(dashboard)
    assert drilldown_links, f"{dashboard_name} must expose Grafana Drilldown app URLs"
    for link in drilldown_links:
        _assert_drilldown_link_time_and_route(dashboard_name=dashboard_name, link=link)


def _navigation_logs_drilldown_links(
    dashboard: dict[str, object],
) -> list[dict[str, object]]:
    return [
        link
        for link in get_dashboard_navigation_links(dashboard)
        if _is_logs_drilldown_url(link.get("url", ""))
    ]


def _assert_loki_drilldown_link_safe_baseline(
    *, dashboard_name: str, link: dict[str, object]
) -> None:
    url = str(link.get("url", ""))
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
    assert "refine in Explore" in tooltip or "refinement inside Explore" in tooltip, (
        f"{dashboard_name} Loki drilldown must disclose baseline-first refinement workflow"
    )


def _assert_dashboard_loki_safe_baseline(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    loki_links = _navigation_logs_drilldown_links(dashboard)
    assert loki_links, f"{dashboard_name} must expose Loki drilldown links"
    for link in loki_links:
        _assert_loki_drilldown_link_safe_baseline(
            dashboard_name=dashboard_name, link=link
        )


def _navigation_traces_drilldown_links(
    dashboard: dict[str, object],
) -> list[dict[str, object]]:
    return [
        link
        for link in get_dashboard_navigation_links(dashboard)
        if _is_traces_drilldown_url(link.get("url", ""))
    ]


def _assert_pipeline_scoped_tempo_link(*, dashboard_name: str, url: str) -> None:
    assert "queryType=traceqlSearch" in url, (
        f"{dashboard_name} Tempo drilldown must declare TraceQL search mode"
    )
    assert "query=%7B%7D" not in url and "query={}" not in url, (
        f"{dashboard_name} Tempo drilldown must not use empty trace query payload"
    )
    assert "bioetl.pipeline" in url, (
        f"{dashboard_name} Tempo drilldown must scope by pipeline"
    )
    if dashboard_name == "bioetl-runtime.json":
        assert "bioetl.run_type" not in url, (
            "bioetl-runtime.json Tempo drilldown must stay safe for "
            "include-all run_type selectors"
        )
    else:
        assert "bioetl.run_type" in url, (
            f"{dashboard_name} Tempo drilldown must scope by run_type"
        )
    assert "bioetl.provider" not in url, (
        f"{dashboard_name} pipeline drilldown must not switch to provider-only scope"
    )


def _assert_pipeline_scoped_tempo_dashboard(dashboard_name: str) -> None:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    tempo_links = _navigation_traces_drilldown_links(dashboard)
    assert tempo_links, f"{dashboard_name} must expose Tempo drilldown links"
    for link in tempo_links:
        _assert_pipeline_scoped_tempo_link(
            dashboard_name=dashboard_name, url=str(link.get("url", ""))
        )


def _assert_provider_tempo_drilldown() -> None:
    provider_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    provider_links = _navigation_traces_drilldown_links(provider_dashboard)
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


def _assert_workflow_tempo_drilldown() -> None:
    workflow_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-workflow-overview.json")
    )
    workflow_links = _navigation_traces_drilldown_links(workflow_dashboard)
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


def _assert_sample_structured_log_fields(sample_line: str) -> None:
    assert re.search(r'"pipeline"\s*:\s*"chembl_activity"', sample_line)
    assert re.search(r'"provider"\s*:\s*"chembl"', sample_line)
    assert re.search(r'"stage"\s*:\s*"extract"', sample_line)


def _assert_dashboard_loki_entrypoint(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    if dashboard.get("uid") in _DRILLDOWN_TOP_LEVEL_EXEMPT_UIDS:
        return
    loki_links = _navigation_logs_drilldown_links(dashboard)
    assert loki_links, f"{dashboard_name} must expose at least one Logs Drilldown link"
    assert all(
        "/explore?left=" not in str(link.get("url", "")) for link in loki_links
    ), f"{dashboard_name} must not keep legacy Loki Explore payload links"


def _assert_named_dashboard_handoff(
    *,
    dashboard_name: str,
    expected_title: str,
    url_prefix: str,
    scope_tokens: tuple[str, str] = (
        "var-pipeline=$pipeline",
        "var-run_type=$run_type",
    ),
) -> None:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    navigation_links = get_dashboard_navigation_links(dashboard)
    titles = {link.get("title") for link in navigation_links if link.get("title")}
    urls = [str(link.get("url", "")) for link in navigation_links]
    assert expected_title in titles, (
        f"{dashboard_name} must expose a {expected_title} dashboard handoff"
    )
    matching_urls = [url for url in urls if url.startswith(url_prefix)]
    assert matching_urls, f"{dashboard_name} handoff must target {url_prefix}"
    token_a, token_b = scope_tokens
    assert any(token_a in url and token_b in url for url in matching_urls), (
        f"{dashboard_name} handoff must preserve pipeline/run_type scope"
    )


_SILVER_EXPLORER_EXPLICIT_EXPECTATIONS: dict[str, dict[str, object]] = {
    "bioetl-dq-v2.json": {
        "url_tokens": ("var-pipeline=$pipeline", "var-run_type=$run_type"),
        "tooltip_token": "bounded pipeline/run_type",
    },
    "bioetl-provider-health-v2.json": {
        "url_tokens": ("var-pipeline=$pipeline_context", "var-run_type=$run_type"),
        "tooltip_token": "Context mapping",
    },
    "bioetl-workflow-overview.json": {
        "url_tokens": (
            "var-pipeline=$pipeline_context_exact",
            "var-run_type=$run_type_context_exact",
        ),
        "tooltip_token": "Context mapping",
    },
}


def _assert_silver_explorer_presence_for_dashboard(
    *, dashboard_name: str, dashboard: dict[str, object]
) -> None:
    """Silver Reject Explorer dashboard was removed from the shipping surface."""
    del dashboard  # presence check is path-based after removal
    assert not Path("grafana/dashboards/bioetl-silver-reject-explorer.json").exists(), (
        f"{dashboard_name}: silver reject explorer JSON must stay removed"
    )


def _assert_explicit_silver_explorer_policy(
    *, dashboard_name: str, expected: dict[str, object]
) -> None:
    """No explicit Silver Reject Explorer handoff policy remains after removal."""
    del expected
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    links = get_dashboard_navigation_links(dashboard)
    residual = [
        link
        for link in links
        if "silver-reject" in str(link.get("url", ""))
        or "Silver Reject" in str(link.get("title", ""))
    ]
    assert not residual, (
        f"{dashboard_name} still exposes Silver Reject Explorer handoff: {residual}"
    )
