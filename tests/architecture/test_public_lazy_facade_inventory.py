"""Governance checks for public lazy facade classification."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs/quality/public_lazy_facade_inventory.yaml"
PUBLIC_MARKERS = frozenset({"__getattr__", "_PUBLIC_EXPORTS", "_PUBLIC_SYMBOL_TARGETS"})


def _load_inventory() -> dict[str, Any]:
    payload = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _target_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    if isinstance(target, ast.Tuple | ast.List):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_names(element))
        return names
    return set()


def _assignment_names(node: ast.stmt) -> set[str]:
    if isinstance(node, ast.Assign):
        names: set[str] = set()
        for target in node.targets:
            names.update(_target_names(target))
        return names
    if isinstance(node, ast.AnnAssign):
        return _target_names(node.target)
    return set()


def _public_lazy_markers(tree: ast.Module) -> frozenset[str]:
    markers: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__getattr__":
            markers.add("__getattr__")
            continue
        markers.update(_assignment_names(node).intersection(PUBLIC_MARKERS))
    return frozenset(markers)


def _discover_public_lazy_markers(
    source_ast_cache: dict[Path, ast.Module],
) -> dict[str, frozenset[str]]:
    discovered: dict[str, frozenset[str]] = {}
    for path, tree in source_ast_cache.items():
        try:
            relative_path = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if not relative_path.startswith("src/bioetl/"):
            continue
        markers = _public_lazy_markers(tree)
        if markers:
            discovered[relative_path] = markers
    return discovered


def _inventory_by_path() -> dict[str, dict[str, Any]]:
    payload = _load_inventory()
    return {str(row["path"]): row for row in payload["facades"]}


def test_public_lazy_facade_inventory_has_policy_shape() -> None:
    payload = _load_inventory()
    facades = payload["facades"]

    assert payload["schema_version"] == 1
    assert payload["policy_scope"] == "public_lazy_facades"
    assert payload["linked_issue"] == "#6624"
    assert payload["new_surface_policy"] == (
        "fail_fast_unclassified_lazy_public_facade"
    )
    assert payload["row_count"] == len(facades) == 52
    assert set(payload["allowed_classifications"]) == {
        "external_public_api",
        "owner_package_root",
        "compatibility_debt",
        "internal_lazy_import_optimization",
    }
    assert len({row["path"] for row in facades}) == len(facades)


def test_public_lazy_facade_inventory_matches_source_ast(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    inventory_markers = {
        path: frozenset(str(marker) for marker in row["markers"])
        for path, row in _inventory_by_path().items()
    }

    assert _discover_public_lazy_markers(source_ast_cache) == inventory_markers


def test_public_lazy_facade_rows_have_owner_importer_and_exit_metadata() -> None:
    payload = _load_inventory()
    allowed = set(payload["allowed_classifications"])

    violations: list[str] = []
    for row in payload["facades"]:
        path = str(row["path"])
        if row["classification"] not in allowed:
            violations.append(f"{path}: unknown classification {row['classification']}")
        if not str(row["owner"]).startswith("@"):
            violations.append(f"{path}: owner must be a team handle")
        if not row["allowed_importers"]:
            violations.append(f"{path}: allowed_importers must be populated")
        if not str(row["exit_criteria"]).strip():
            violations.append(f"{path}: exit_criteria must be populated")
        if not (ROOT / path).is_file():
            violations.append(f"{path}: missing source file")

    assert violations == []


def test_infrastructure_config_root_facade_remains_bounded_compatibility_debt() -> None:
    row = _inventory_by_path()["src/bioetl/infrastructure/config/__init__.py"]

    assert row["classification"] == "compatibility_debt"
    assert row["owner"] == "@bioetl-config"
    assert row["allowed_importers"] == [
        "external_compatibility_consumers",
        "tests",
    ]
    assert "Collapse after first-party callers remain at zero" in row["exit_criteria"]
