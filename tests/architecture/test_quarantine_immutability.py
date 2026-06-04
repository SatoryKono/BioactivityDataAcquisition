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
