"""Tests for quarantine payload immutability.

This test verifies that quarantine-related data structures are immutable
according to the architectural requirement that quarantine payload must be
immutable to guarantee data integrity and reproducibility.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def _iter_python_files_under(root_path: Path) -> list[Path]:
    """Return all Python files under root_path."""
    return sorted(root_path.rglob("*.py"))


def _find_dataclass_definitions(file_path: Path) -> list[dict[str, object]]:
    """Find all dataclass definitions in a Python file."""
    content = file_path.read_text(encoding="utf-8")
    tree = ast.parse(content)

    dataclasses = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if this class has @dataclass decorator
            is_dataclass = False
            is_frozen = False
            has_quarantine_payload = False

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id == "dataclass":
                        is_dataclass = True
                elif isinstance(decorator, ast.Call):
                    if (
                        isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "dataclass"
                    ):
                        is_dataclass = True
                        # Check for frozen=True argument
                        for keyword in decorator.keywords:
                            if keyword.arg == "frozen" and isinstance(
                                keyword.value, ast.Constant
                            ):
                                is_frozen = keyword.value.value is True

            # Check if class name contains both "quarantine" and "payload" (case-insensitive)
            class_name_lower = node.name.lower()
            has_quarantine_payload = (
                "quarantine" in class_name_lower and "payload" in class_name_lower
            )

            if is_dataclass and has_quarantine_payload:
                dataclasses.append(
                    {
                        "name": node.name,
                        "file": file_path,
                        "is_frozen": is_frozen,
                    }
                )

    return dataclasses


def _find_class_method(
    tree: ast.AST, class_name: str, method_name: str
) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return child
    raise AssertionError(f"Could not find {class_name}.{method_name}")


def _attribute_path(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return None


def _calls_deepcopy_with_arg(node: ast.AST, expected_arg: tuple[str, ...]) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Name) or child.func.id != "deepcopy":
            continue
        if not child.args:
            continue
        if _attribute_path(child.args[0]) == expected_arg:
            return True
    return False


def test_quarantine_payload_dataclasses_are_frozen() -> None:
    """Test that all quarantine payload dataclasses are frozen (immutable)."""
    src_path = Path("src/bioetl")

    non_frozen_quarantine_payloads = []
    for py_file in _iter_python_files_under(src_path):
        dataclasses = _find_dataclass_definitions(py_file)
        for dc in dataclasses:
            if not dc["is_frozen"]:
                non_frozen_quarantine_payloads.append(f"{dc['file']}:{dc['name']}")

    if non_frozen_quarantine_payloads:
        pytest.fail(
            f"Found quarantine payload dataclasses that are not frozen (immutable):\n"
            f"{chr(10).join(non_frozen_quarantine_payloads)}\n\n"
            f"All quarantine payload dataclasses must be frozen=True to ensure "
            f"immutability as per architectural requirements."
        )


def test_quarantine_entry_defensively_copies_constructor_and_accessor_payloads() -> (
    None
):
    """Constructor and accessors must preserve payload immutability via defensive copies."""
    aggregate_path = Path("src/bioetl/domain/aggregates/_quarantine_aggregate.py")
    aggregate_tree = ast.parse(aggregate_path.read_text(encoding="utf-8"))
    init_method = _find_class_method(aggregate_tree, "QuarantineEntry", "__init__")

    assert _calls_deepcopy_with_arg(init_method, ("payload",))
    assert _calls_deepcopy_with_arg(init_method, ("metadata",))

    properties_path = Path(
        "src/bioetl/domain/aggregates/_quarantine_entry_properties_mixin.py"
    )
    properties_tree = ast.parse(properties_path.read_text(encoding="utf-8"))
    payload_property = _find_class_method(
        properties_tree, "QuarantineEntryPropertiesMixin", "payload"
    )
    metadata_property = _find_class_method(
        properties_tree, "QuarantineEntryPropertiesMixin", "metadata"
    )

    assert _calls_deepcopy_with_arg(payload_property, ("self", "_payload"))
    assert _calls_deepcopy_with_arg(metadata_property, ("self", "_metadata"))
