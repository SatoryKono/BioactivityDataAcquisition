"""Integration tests for Grafana selector taxonomy and shipped selector registry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration

_SELECTOR_CONTRACT_PATH = Path(
    "docs/03-guides/dashboards/contracts/selector-contracts.yaml"
)


def _load_selector_contract() -> dict[str, object]:
    payload = yaml.safe_load(_SELECTOR_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), (
        "selector-contracts.yaml must deserialize into a mapping"
    )
    return payload


_SELECTOR_CONTRACT = _load_selector_contract()


def _dashboard_variables(dashboard_file: str) -> dict[str, dict]:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    return {
        variable.get("name"): variable
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }


def test_selector_contract_declares_single_normative_source() -> None:
    marker = _SELECTOR_CONTRACT.get("normative_source")
    assert isinstance(marker, dict)
    assert marker.get("scope") == "selector_taxonomy_registry_semantics"
    assert marker.get("authority") == "single_source_of_truth"
    assert isinstance(marker.get("narrative_minimal"), str)


def test_selector_taxonomy_contains_required_classes() -> None:
    taxonomy = _SELECTOR_CONTRACT.get("selector_taxonomy")
    assert isinstance(taxonomy, dict)
    for key in (
        "scope",
        "state",
        "execution_future",
        "context_hidden",
        "forensic_only",
    ):
        assert key in taxonomy


def test_dashboard_families_cover_all_shipped_dashboards() -> None:
    families = _SELECTOR_CONTRACT.get("dashboard_families")
    registry = _SELECTOR_CONTRACT.get("shipped_selector_registry")
    assert isinstance(families, dict)
    assert isinstance(registry, dict)

    covered_uids: set[str] = set()
    for payload in families.values():
        assert isinstance(payload, dict)
        uids = payload.get("uids", [])
        assert isinstance(uids, list)
        covered_uids.update(str(uid) for uid in uids)

    assert covered_uids == set(registry), (
        "dashboard_families.uids must cover exactly the dashboards present in "
        "shipped_selector_registry"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "dashboard_uid"),
    [
        ("bioetl-control-plane-v1.json", "bioetl-control-plane-v1"),
        ("bioetl-overview-v2.json", "bioetl-overview-v2"),
        ("bioetl-runtime.json", "bioetl-runtime"),
        ("bioetl-provider-health-v2.json", "bioetl-provider-health-v2"),
        ("bioetl-dq-v2.json", "bioetl-dq-v2"),
        ("bioetl-workflow-overview.json", "bioetl-workflow-overview"),
        ("bioetl-silver-reject-explorer.json", "bioetl-silver-reject-explorer"),
    ],
)
def test_shipped_selector_registry_matches_dashboard_variables(
    dashboard_file: str, dashboard_uid: str
) -> None:
    registry = _SELECTOR_CONTRACT["shipped_selector_registry"][dashboard_uid]
    assert isinstance(registry, dict)

    expected_variables = (
        set(registry.get("visible_selectors", []))
        | set(registry.get("hidden_context_selectors", []))
        | set(registry.get("hidden_detail_selectors", []))
    )
    variable_map = _dashboard_variables(dashboard_file)

    assert set(variable_map) == expected_variables, (
        f"{dashboard_file} variables must match shipped selector registry"
    )

    visible = set(registry.get("visible_selectors", []))
    hidden_context = set(registry.get("hidden_context_selectors", []))
    hidden_detail = set(registry.get("hidden_detail_selectors", []))

    for name in visible:
        assert variable_map[name].get("hide", 0) != 2, (
            f"{dashboard_file}:{name} must remain visible per selector registry"
        )
    for name in hidden_context | hidden_detail:
        assert variable_map[name].get("hide", 0) == 2, (
            f"{dashboard_file}:{name} must remain hidden per selector registry"
        )


def test_ship_now_selector_contract_matches_registry_visible_selectors() -> None:
    registry = _SELECTOR_CONTRACT.get("shipped_selector_registry")
    ship_now = _SELECTOR_CONTRACT.get("ship_now_selector_contract_by_uid")
    assert isinstance(registry, dict)
    assert isinstance(ship_now, dict)

    for uid, payload in ship_now.items():
        assert uid in registry
        assert payload.get("visible_selectors") == registry[uid].get(
            "visible_selectors"
        )


def test_hidden_handoff_contract_matches_shipped_hidden_vars() -> None:
    hidden_contract = _SELECTOR_CONTRACT.get("hidden_handoff_contract")
    registry = _SELECTOR_CONTRACT.get("shipped_selector_registry")
    assert isinstance(hidden_contract, dict)
    assert isinstance(registry, dict)

    shipped_hidden = set(hidden_contract.get("allowed_shipped_vars", []))
    shipped_detail = set(hidden_contract.get("detail_only_shipped_vars", []))
    registry_hidden = set()
    registry_detail = set()
    for payload in registry.values():
        assert isinstance(payload, dict)
        registry_hidden.update(payload.get("hidden_context_selectors", []))
        registry_detail.update(payload.get("hidden_detail_selectors", []))

    assert shipped_hidden == registry_hidden
    assert shipped_detail == registry_detail


def test_control_plane_selector_context_contract_is_local_only() -> None:
    resolver = _SELECTOR_CONTRACT.get("control_plane_selector_context_contract")
    assert isinstance(resolver, dict)
    assert resolver.get("status") == "shipped"
    assert resolver.get("endpoint") == "/ops/control-plane/selector-context"
    assert (
        resolver.get("filter_options_endpoint") == "/ops/control-plane/filter-options"
    )
    assert resolver.get("local_only") is True

    forbidden = set(resolver.get("forbidden", []))
    assert "prometheus_run_id_labels" in forbidden
    assert "blanket_includevars_run_id_handoff" in forbidden
    assert "run_id_handoff_to_forensic_explorer" in forbidden
    assert "cyclic_grafana_variable_dependencies" in forbidden


def test_current_dashboards_do_not_ship_future_execution_selectors() -> None:
    future = _SELECTOR_CONTRACT.get("execution_selector_future_contract")
    hidden_contract = _SELECTOR_CONTRACT.get("hidden_handoff_contract")
    assert isinstance(future, dict)
    assert isinstance(hidden_contract, dict)

    forbidden_now = {str(future.get("selector_name"))} | set(
        hidden_contract.get("reserved_future_vars", [])
    )

    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        variable_names = set(_dashboard_variables(dashboard_path.name))
        assert not (variable_names & forbidden_now), (
            f"{dashboard_path.name} must not ship future execution selectors yet: "
            f"{sorted(variable_names & forbidden_now)}"
        )
