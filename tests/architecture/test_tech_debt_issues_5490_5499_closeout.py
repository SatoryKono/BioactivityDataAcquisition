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
"""Closeout guardrails for technical-debt issues #5490-#5499."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.git_index_scan import git_grep_fixed


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5490-5499-closeout.json"
COMPAT_INVENTORY = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
CONFIG_ROOT_INVENTORY = (
    ROOT / "configs" / "quality" / "infrastructure_config_root_facade_inventory.yaml"
)
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _collect_exact_importers(target_module: str) -> set[str]:
    importers: set[str] = set()
    candidate_paths = {
        match.path
        for match in git_grep_fixed(
            root=ROOT,
            patterns=(target_module,),
            paths=("src/bioetl",),
            suffixes=(".py",),
        )
    }
    for relative_path in sorted(candidate_paths):
        path = ROOT / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module or "")
            if any(module_name == target_module for module_name in modules):
                importers.add(path.relative_to(ROOT).as_posix())
                break
    return importers


def test_issue_5490_infrastructure_config_root_facade_stays_zero_growth() -> None:
    inventory = _load_yaml(CONFIG_ROOT_INVENTORY)
    assert inventory["linked_issue"] == "#5490"
    assert _collect_exact_importers("bioetl.infrastructure.config") == set()


def test_issue_5492_public_export_budgets_stay_reduced() -> None:
    inventory = _load_yaml(COMPAT_INVENTORY)
    budgets = {
        row["path"]: row["public_export_contract"]["max_public_exports"]
        for row in inventory["retained_entrypoints"]
        if isinstance(row, dict) and "public_export_contract" in row
    }
    ceilings = {
        "src/bioetl/composition/entrypoints.py": 13,
        "src/bioetl/composition/health_api.py": 7,
        "src/bioetl/composition/maintenance_api.py": 4,
    }

    for path, max_public_exports in ceilings.items():
        assert budgets[path] <= max_public_exports


def test_issue_5494_ranked_tail_tier_violations_block() -> None:
    gates = _load_yaml(MODULE_COVERAGE_GATES)
    enforcement = gates["enforcement"]

    assert enforcement["default_mode"] == "block-regression"
    assert enforcement["ranked_target_tier_violation_mode"] == "block"


def test_issue_5496_control_plane_root_routes_through_explicit_seams() -> None:
    import bioetl.application.services.control_plane as control_plane_root

    assert set(control_plane_root.RESPONSIBILITY_SEAMS) == {
        "effective_config",
        "forensic",
        "ledger",
        "manifest",
        "replay",
        "workflow",
    }
    assert (
        control_plane_root._LAZY_ATTR_EXPORTS["ForensicRunDiffService"][0]
        == "bioetl.application.services.control_plane.forensic"
    )


def test_issue_5497_pandera_runtime_monkeypatching_stays_retired() -> None:
    import bioetl.infrastructure.compat as compat_package

    assert compat_package.__all__ == []
    assert not (
        ROOT / "src" / "bioetl" / "infrastructure" / "compat" / "pandera_compat.py"
    ).exists()


def test_issue_5499_first_party_config_facade_imports_stay_collapsed() -> None:
    importers = _collect_exact_importers("bioetl.domain.composite.config")

    assert importers == set()
