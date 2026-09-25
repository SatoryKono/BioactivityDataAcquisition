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
"""Architecture guardrails for active hotspot-family internal fan-in budgets."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    _is_type_checking_guard,
    collect_internal_fan_in_census,
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)
from tests.architecture.quality_artifacts import load_quality_json

pytestmark = pytest.mark.architecture

_ENFORCED_RATCHET_STAGES = {"active", "reviewed-baseline"}


def test_active_hotspot_family_internal_fan_in_budgets_hold_reviewed_baseline() -> None:
    """Selected active hotspot families must not exceed their internal fan-in cap."""
    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families

    budgeted_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") in _ENFORCED_RATCHET_STAGES
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "max_internal_fan_in" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, (
        "Expected at least one enforced hotspot family with a fan-in budget"
    )

    for family in budgeted_families:
        family_name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_fan_in, actual_module = count_internal_fan_in(files=files)
        budget = family["bounded_growth_budgets"].get("max_internal_fan_in")
        assert isinstance(budget, int) and budget >= 0
        assert actual_fan_in <= budget, (
            f"Hotspot family {family_name} has max_internal_fan_in={actual_fan_in} "
            f"at module {actual_module}, exceeding bounded budget {budget}. "
            "Keep the family dependency ratchet stable or intentionally refresh "
            "the reviewed hotspot-family baseline under RF-06."
        )


def test_issue_10304_control_plane_replay_fan_in_has_headroom() -> None:
    """#10304: replay types/extended fold must not remain the family fan-in hub."""
    replay_root = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "control_plane"
        / "replay"
    )
    removed = (
        replay_root / "reproducibility_score_cards_types.py",
        replay_root / "reproducibility_score_cards_category_scores_extended.py",
    )
    for path in removed:
        assert not path.exists(), f"expected removed replay leaf: {path.name}"

    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)
    family = next(
        row
        for row in families
        if isinstance(row, dict)
        and row.get("name") == "application_services_control_plane"
    )
    budgets = family.get("bounded_growth_budgets", {})
    assert isinstance(budgets, dict)
    assert budgets.get("max_internal_fan_in") == 2

    files = iter_family_python_files(
        path_prefixes=["src/bioetl/application/services/control_plane/"]
    )
    actual_fan_in, actual_module = count_internal_fan_in(files=files)
    family_budget = budgets.get("max_internal_fan_in")
    assert family_budget == 2
    assert actual_fan_in <= family_budget
    assert actual_module != (
        "bioetl.application.services.control_plane.replay."
        "reproducibility_score_cards_types"
    )

    score_card_files = [
        path
        for path in files
        if path.parent == replay_root
        and path.name.startswith("reproducibility_score_cards_")
    ]
    cluster_fan_in, cluster_module = count_internal_fan_in(files=score_card_files)
    assert cluster_fan_in < 2, (
        "replay score-card cluster max_internal_fan_in="
        f"{cluster_fan_in} at {cluster_module}; expected a line graph after #10304"
    )


_PIPELINE_SPAN_LIFECYCLE = "bioetl.application.core.pipeline_span_lifecycle"
_PIPELINE_SPAN_LIFECYCLE_RUNTIME_IMPORTERS = (
    "src/bioetl/application/core/_base_transformer_execution_support.py",
    "src/bioetl/application/core/_record_processor_span_support.py",
    "src/bioetl/application/core/batch_tracing.py",
    "src/bioetl/application/core/postrun/service.py",
    "src/bioetl/application/core/runner.py",
)


def _runtime_imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()

    def walk(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
            for child in node.orelse:
                walk(child)
            return
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(tree)
    return found


def test_issue_10306_pipeline_span_lifecycle_fan_in_at_most_five() -> None:
    """#10306: application/core live fan-in must stay ≤5 without new lifecycle importers."""
    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)
    family = next(
        row
        for row in families
        if isinstance(row, dict) and row.get("name") == "application_core"
    )
    budgets = family.get("bounded_growth_budgets", {})
    assert isinstance(budgets, dict)
    assert budgets.get("max_internal_fan_in") == 7

    files = iter_family_python_files(path_prefixes=["src/bioetl/application/core/"])
    actual_fan_in, actual_module = count_internal_fan_in(files=files)
    assert actual_fan_in <= 5, (
        "application_core max_internal_fan_in="
        f"{actual_fan_in} at {actual_module}; #10306 requires ≤5"
    )

    repo_root = Path(__file__).resolve().parents[2]
    importers = sorted(
        path.relative_to(repo_root).as_posix()
        for path in files
        if _PIPELINE_SPAN_LIFECYCLE in _runtime_imported_modules(path)
    )
    assert importers == list(_PIPELINE_SPAN_LIFECYCLE_RUNTIME_IMPORTERS)
    assert len(importers) <= 5


_C0_FAMILY_CAPS = {
    "application_services_control_plane": 2,
    "composition_runtime_builders": 3,
}


def test_hotspot_family_fan_in_census_matches_live_ast_graph() -> None:
    """#10470: committed reverse-import census must equal the live AST graph."""
    committed = load_quality_json("hotspot-family-baseline.json")
    families = committed.get("families")
    assert isinstance(families, list) and families

    for family in families:
        assert isinstance(family, dict)
        name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(name, str)
        assert isinstance(path_prefixes, list) and path_prefixes
        files = iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        live = collect_internal_fan_in_census(files=files)
        wrapper_max, wrapper_module = count_internal_fan_in(files=files)
        census = family.get("internal_fan_in_census")
        assert isinstance(census, dict)
        live_modules = [
            {
                "module": row.module,
                "fan_in": row.fan_in,
                "runtime_importers": list(row.runtime_importers),
            }
            for row in live.modules
        ]
        assert census["distribution"] == live.distribution
        assert census["modules"] == live_modules
        assert census["max_fan_in"] == live.max_fan_in
        assert census["max_modules"] == list(live.max_modules)
        assert family["max_internal_fan_in"] == live.max_fan_in
        assert family["files"] == len(live.modules)
        assert sum(live.distribution.values()) == family["files"]
        assert wrapper_max == live.max_fan_in
        if live.max_fan_in == 0:
            assert wrapper_module is None
        else:
            assert wrapper_module == live.max_modules[-1]
        for row in live.modules:
            assert row.runtime_importers == tuple(sorted(set(row.runtime_importers)))

        cap = family.get("bounded_growth_budgets", {})
        assert isinstance(cap, dict)
        fan_in_cap = cap.get("max_internal_fan_in")
        if isinstance(fan_in_cap, int):
            at_budget = [
                module for module in live.modules if module.fan_in == fan_in_cap
            ]
            assert family.get("at_budget_module_count") == len(at_budget)
            assert family.get("at_budget_modules") == [
                {
                    "module": row.module,
                    "fan_in": row.fan_in,
                    "runtime_importers": list(row.runtime_importers),
                }
                for row in at_budget
            ]

    by_name = {
        str(row["name"]): row
        for row in families
        if isinstance(row, dict) and "name" in row
    }
    for family_name, expected_cap in _C0_FAMILY_CAPS.items():
        family = by_name[family_name]
        budgets = family.get("bounded_growth_budgets", {})
        assert isinstance(budgets, dict)
        assert budgets.get("max_internal_fan_in") == expected_cap
        census = family["internal_fan_in_census"]
        assert isinstance(census, dict)
        assert census["max_fan_in"] <= expected_cap
        assert family["at_budget_module_count"] == 0
        if family_name == "composition_runtime_builders":
            assert census["max_fan_in"] == 2
        else:
            assert census["max_fan_in"] <= 1

    control_plane = by_name["application_services_control_plane"]
    runtime_builders = by_name["composition_runtime_builders"]
    assert control_plane["files"] == 124
    assert control_plane["internal_fan_in_census"]["distribution"] == {
        "0": 20,
        "1": 104,
    }
    assert control_plane["at_budget_module_count"] == 0
    assert runtime_builders["files"] == 56
    assert runtime_builders["internal_fan_in_census"]["distribution"] == {
        "0": 3,
        "1": 27,
        "2": 26,
    }
    assert runtime_builders["internal_fan_in_census"]["max_fan_in"] == 2
    assert runtime_builders["at_budget_module_count"] == 0
