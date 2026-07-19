"""Integration tests for Grafana selector taxonomy and shipped selector registry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

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


def _variable_query_text(dashboard_file: str, variable_name: str) -> str:
    variable = _dashboard_variables(dashboard_file)[variable_name]
    query = variable.get("query", {})
    return str(query.get("query", "") if isinstance(query, dict) else query)


def _record_expression(rules_file: str, record_name: str) -> str:
    payload = yaml.safe_load(Path(rules_file).read_text(encoding="utf-8"))
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("record") == record_name:
                return str(rule.get("expr", "")).strip()
    raise AssertionError(f"missing recording rule: {record_name}")


def _panel_by_id(dashboard_file: str, panel_id: int) -> dict:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    matches = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") == panel_id
    ]
    assert len(matches) == 1, f"{dashboard_file} must contain panel id={panel_id}"
    return matches[0]


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


def test_pipeline_universe_contract_matches_shipped_query_sources() -> None:
    contract = _SELECTOR_CONTRACT.get("pipeline_universe_contract")
    registry = _SELECTOR_CONTRACT.get("shipped_selector_registry")
    assert isinstance(contract, dict)
    assert isinstance(registry, dict)
    assert contract.get("status") == "shipped"
    assert (
        contract.get("canonical_user_facing_metric")
        == "bioetl_overview_pipeline_run_type_universe"
    )

    shared = contract.get("shared_query_metrics")
    exceptions = contract.get("role_local_exceptions")
    assert isinstance(shared, dict)
    assert isinstance(exceptions, dict)
    assert set(shared) | set(exceptions) == set(registry)
    assert set(shared) & set(exceptions) == set()

    file_by_uid = {
        "bioetl-control-plane-v1": "bioetl-control-plane-v1.json",
        "bioetl-overview-v2": "bioetl-overview-v2.json",
        "bioetl-runtime": "bioetl-runtime.json",
        "bioetl-provider-health-v2": "bioetl-provider-health-v2.json",
        "bioetl-dq-v2": "bioetl-dq-v2.json",
        "bioetl-workflow-overview": "bioetl-workflow-overview.json",
        "bioetl-silver-reject-explorer": "bioetl-silver-reject-explorer.json",
        "bioetl-alerts-slo": "bioetl-alerts-slo.json",
    }
    for uid, metric in shared.items():
        query = _variable_query_text(file_by_uid[uid], "pipeline")
        assert metric in query
        source_family = registry[uid]["query_source_families"]["pipeline"]
        assert source_family == f"prometheus_{metric.removeprefix('bioetl_')}"
    for uid, payload in exceptions.items():
        assert isinstance(payload, dict)
        query = _variable_query_text(file_by_uid[uid], "pipeline")
        metric = payload.get("query_metric")
        assert metric in query
        source_family = registry[uid]["query_source_families"]["pipeline"]
        assert source_family == f"prometheus_{metric.removeprefix('bioetl_')}"

    control_plane = exceptions["bioetl-control-plane-v1"]
    assert control_plane.get("required_relation") == "provenance_gated_overlap"
    assert control_plane.get("allowed_role_local_only_sources") == [
        "bioetl_control_plane_manifest_writes_total"
    ]
    assert control_plane.get("allowed_canonical_only_sources") == [
        "bioetl_pipeline_runs_total",
        "bioetl_records_processed_total",
    ]
    assert (
        control_plane.get("shared_planned_source")
        == "bioetl_workflow_pipeline_expected"
    )
    assert control_plane.get("unexplained_difference_count_required") == 0

    explorer = exceptions["bioetl-silver-reject-explorer"]
    assert explorer.get("required_relation") == (
        "subset_of_canonical_user_facing_metric"
    )


def test_pipeline_universe_relations_follow_recording_rule_sources() -> None:
    canonical_expr = _record_expression(
        "grafana/prometheus-rules/bioetl_observability.yml",
        "bioetl_runtime_pipeline_run_type_universe",
    )
    control_plane_expr = _record_expression(
        "grafana/prometheus-rules/bioetl_control_plane_current_status.yml",
        "bioetl_control_plane_run_type_universe",
    )

    for source in (
        "bioetl_pipeline_runs_total",
        "bioetl_records_processed_total",
        "bioetl_workflow_pipeline_expected",
    ):
        assert source in canonical_expr
    assert "bioetl_control_plane_manifest_writes_total" not in canonical_expr

    for source in (
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_workflow_pipeline_expected",
    ):
        assert source in control_plane_expr
    assert "bioetl_pipeline_runs_total" not in control_plane_expr
    assert "bioetl_records_processed_total" not in control_plane_expr


def test_role_local_pipeline_handoffs_have_visible_recovery_paths() -> None:
    navigation = _panel_by_id("bioetl-control-plane-v1.json", 1000)
    assert "/d/bioetl-overview-v2/" in str(
        navigation.get("options", {}).get("content", "")
    )

    for panel_id in (9410, 9411):
        panel = _panel_by_id("bioetl-control-plane-v1.json", panel_id)
        guidance = " ".join(
            (
                str(panel.get("description", "")),
                str(panel.get("options", {}).get("content", "")),
            )
        ).lower()
        assert "scope" in guidance
        assert "health" in guidance

    explorer_scope = _panel_by_id("bioetl-silver-reject-explorer.json", 1)
    recovery = " ".join(
        (
            str(explorer_scope.get("description", "")),
            str(explorer_scope.get("options", {}).get("content", "")),
        )
    ).lower()
    for token in ("reset", "concrete pipeline", "backend health"):
        assert token in recovery


def test_overview_universe_is_an_exact_runtime_alias() -> None:
    rules_path = Path("grafana/prometheus-rules/bioetl_observability.yml")
    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    rules = [
        rule
        for group in payload.get("groups", [])
        for rule in group.get("rules", [])
        if isinstance(rule, dict)
    ]
    record_map = {
        rule.get("record"): str(rule.get("expr", "")).strip() for rule in rules
    }

    assert record_map["bioetl_overview_pipeline_run_type_universe"] == (
        "bioetl_runtime_pipeline_run_type_universe"
    )


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
