"""Integration tests for dashboard level navigation transition matrix."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration

_DASHBOARDS_DIR = Path("grafana/dashboards")
_CONTRACT_PATH = Path("docs/03-guides/dashboards/contracts/navigation-links.yaml")
_DASHBOARD_UID_RE = re.compile(r"^/d/([^/?]+)")
_LINK_VAR_VALUE_RE = re.compile(r"(?:\?|&)var-([A-Za-z_]+)=([^&#]+)")


def _load_contract() -> dict[str, object]:
    return yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))


def _build_top_level_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for path in _DASHBOARDS_DIR.glob("*.json"):
        payload = load_dashboard(path)
        source_uid = payload.get("uid")
        assert isinstance(source_uid, str), f"{path.name} must define string uid"
        edges.setdefault(source_uid, set())

        for link in payload.get("links", []):
            url = link.get("url")
            if not isinstance(url, str):
                continue
            match = _DASHBOARD_UID_RE.match(url)
            if match is None:
                continue
            edges[source_uid].add(match.group(1))
    return edges


def _iter_top_level_uid_links() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for path in _DASHBOARDS_DIR.glob("*.json"):
        payload = load_dashboard(path)
        source_uid = payload.get("uid")
        assert isinstance(source_uid, str), f"{path.name} must define string uid"
        for link in payload.get("links", []):
            url = link.get("url")
            if not isinstance(url, str):
                continue
            match = _DASHBOARD_UID_RE.match(url)
            if match is None:
                continue
            rows.append((source_uid, match.group(1), url))
    return rows


def _iter_top_level_uid_links_with_title() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for path in _DASHBOARDS_DIR.glob("*.json"):
        payload = load_dashboard(path)
        source_uid = payload.get("uid")
        assert isinstance(source_uid, str), f"{path.name} must define string uid"
        for link in payload.get("links", []):
            title = link.get("title")
            url = link.get("url")
            if not isinstance(title, str) or not isinstance(url, str):
                continue
            match = _DASHBOARD_UID_RE.match(url)
            if match is None:
                continue
            rows.append((source_uid, title, match.group(1), url))
    return rows


def test_level_matrix_required_inbound_outbound_transitions_present() -> None:
    contract = _load_contract()["navigation_transition_contract"]
    assert isinstance(contract, dict)

    matrix = contract["dashboard_levels"]
    assert isinstance(matrix, dict)
    edges = _build_top_level_edges()

    for level_name, level_payload in matrix.items():
        assert isinstance(level_payload, dict), f"{level_name} payload must be mapping"
        dashboards = set(level_payload["dashboards"])
        required_outbound = set(level_payload["required_outbound"])
        required_inbound = set(level_payload["required_inbound"])

        for uid in dashboards:
            outbound = edges.get(uid, set())
            missing_outbound = required_outbound - outbound
            assert not missing_outbound, (
                f"{level_name}:{uid} missing required outbound transitions: {sorted(missing_outbound)}"
            )

            inbound = {src for src, targets in edges.items() if uid in targets}
            missing_inbound = required_inbound - inbound
            assert not missing_inbound, (
                f"{level_name}:{uid} missing required inbound transitions: {sorted(missing_inbound)}"
            )


def test_scoped_route_class_forbids_default_all_values() -> None:
    contract = _load_contract()["navigation_transition_contract"]
    assert isinstance(contract, dict)

    route_class_by_transition = contract["route_class_by_transition"]
    default_semantics = contract["default_semantics_by_route_class"]
    assert isinstance(route_class_by_transition, dict)
    assert isinstance(default_semantics, dict)

    for source_uid, target_uid, url in _iter_top_level_uid_links():
        transition_key = f"{source_uid}->{target_uid}"
        route_class = route_class_by_transition.get(transition_key)
        if route_class != "scoped_handoff":
            continue

        for variable_name, variable_value in _LINK_VAR_VALUE_RE.findall(url):
            decoded_value = variable_value.replace("%20", " ")
            assert decoded_value != "All", (
                f"Scoped transition {transition_key} must not pass var-{variable_name}=All: {url}"
            )

        class_defaults = default_semantics["scoped_handoff"]["allowed_default_values"]
        assert "All" not in class_defaults, (
            "scoped_handoff route class must not allow default 'All' semantics"
        )


def test_incident_critical_paths_are_reciprocal_and_non_terminal() -> None:
    contract = _load_contract()["navigation_transition_contract"]
    assert isinstance(contract, dict)

    critical_pairs = contract["incident_critical_reciprocal_paths"]
    assert isinstance(critical_pairs, list)

    edges = _build_top_level_edges()

    critical_nodes: set[str] = set()
    for pair in critical_pairs:
        assert isinstance(pair, list) and len(pair) == 2
        left, right = pair
        assert isinstance(left, str) and isinstance(right, str)
        critical_nodes.update({left, right})

        assert right in edges.get(left, set()), (
            f"Incident-critical forward path missing: {left} -> {right}"
        )
        assert left in edges.get(right, set()), (
            f"Incident-critical reciprocal return path missing: {right} -> {left}"
        )

    terminal_nodes = [uid for uid in critical_nodes if not edges.get(uid)]
    assert not terminal_nodes, (
        f"Incident-critical dashboards must not be terminal nodes: {sorted(terminal_nodes)}"
    )


def test_primary_priority_links_are_unique_per_target_uid_and_semantics() -> None:
    contract = _load_contract()
    priority_map = contract["top_level_link_priority_by_uid"]
    assert isinstance(priority_map, dict)

    links_by_source_and_title: dict[tuple[str, str], tuple[str, str]] = {}
    for source_uid, title, target_uid, _url in _iter_top_level_uid_links_with_title():
        links_by_source_and_title[(source_uid, title)] = (target_uid, title)

    for source_uid, entries in priority_map.items():
        assert isinstance(entries, list), f"{source_uid} priority entries must be list"
        primary_by_target: dict[str, list[str]] = {}

        for entry in entries:
            assert isinstance(entry, dict), (
                f"{source_uid} priority entry must be mapping"
            )
            title = entry["title"]
            target_uid = entry["target_uid"]
            priority = entry["priority"]
            semantics = entry["semantics"]
            assert isinstance(title, str)
            assert isinstance(target_uid, str)
            assert isinstance(priority, str)
            assert isinstance(semantics, str) and semantics.strip(), (
                f"{source_uid}:{title} must declare non-empty semantics"
            )

            assert (source_uid, title) in links_by_source_and_title, (
                f"Missing top-level link in dashboard JSON for {source_uid}:{title}"
            )
            actual_target_uid, _ = links_by_source_and_title[(source_uid, title)]
            assert actual_target_uid == target_uid, (
                f"{source_uid}:{title} target mismatch: contract={target_uid}, dashboard={actual_target_uid}"
            )

            if priority == "primary":
                primary_by_target.setdefault(target_uid, []).append(semantics)

        for target_uid, semantics_list in primary_by_target.items():
            assert len(semantics_list) <= 1, (
                f"{source_uid}->{target_uid} has more than one primary link semantics: {semantics_list}"
            )
