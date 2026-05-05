"""Tests for boundary validation assertions in composition factories.

Verifies that composition-layer factory methods include isinstance()
assertions to validate that concrete adapters implement their port protocols.

These assertions act as a safety net at the composition boundary,
catching DI wiring mistakes early at assembly time rather than at runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path("src/bioetl/composition")

# Factory methods that MUST contain isinstance() boundary assertions.
# Format: (module_path_relative_to_src, function_or_method_name)
EXPECTED_ASSERTIONS = [
    ("factories/services/port_factories.py", "create_lock", "LockPort"),
    ("factories/services/port_factories.py", "create_checkpoint", "CheckpointPort"),
    ("factories/services/port_factories.py", "create_quarantine", "QuarantinePort"),
    ("factories/services/port_factories.py", "create_metrics", "MetricsPort"),
    ("factories/datasource/data_source_factory.py", "create", "DataSourcePort"),
    (
        "bootstrap/assembly/checkpoint.py",
        "bootstrap_quarantine_adapter",
        "QuarantinePort",
    ),
    (
        "bootstrap/assembly/checkpoint.py",
        "bootstrap_checkpoint_adapter",
        "CheckpointPort",
    ),
]


class TestBoundaryAssertionsExist:
    """Composition factories MUST have isinstance() boundary assertions."""

    @pytest.mark.parametrize(
        ("module_path", "func_name", "port_name"),
        EXPECTED_ASSERTIONS,
        ids=[f"{m}::{f}" for m, f, _ in EXPECTED_ASSERTIONS],
    )
    def test_factory_contains_isinstance_assertion(
        self,
        module_path: str,
        func_name: str,
        port_name: str,
    ) -> None:
        """Factory method MUST contain an isinstance(..., <Port>) assertion."""
        source_file = SRC_ROOT / module_path
        assert source_file.exists(), f"Source file not found: {source_file}"

        source = source_file.read_text()
        tree = ast.parse(source)
        function_node = _find_named_function(tree, func_name)

        assert function_node is not None, (
            f"Function '{func_name}' not found in {module_path}"
        )
        assert _has_port_isinstance_assert(function_node, source, port_name), (
            f"Function '{func_name}' in {module_path} MUST contain "
            f"`assert isinstance(..., {port_name})` for boundary validation."
        )


class TestBoundaryAssertionsSufficiency:
    """At least 5 factory methods MUST have boundary assertions."""

    def test_minimum_assertion_count(self) -> None:
        """At least 5 factory methods must have boundary assertions."""
        count = 0
        for module_path, _func_name, port_name in EXPECTED_ASSERTIONS:
            source_file = SRC_ROOT / module_path
            if not source_file.exists():
                continue
            source = source_file.read_text()
            if "isinstance(" in source and port_name in source:
                count += 1

        assert count >= 5, (
            f"Expected at least 5 factory methods with boundary assertions, "
            f"found {count}."
        )


def _find_named_function(
    tree: ast.AST,
    func_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == func_name
        ):
            return node
    return None


def _has_port_isinstance_assert(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    port_name: str,
) -> bool:
    return any(
        _is_matching_port_assert(child, source, port_name)
        for child in ast.walk(function_node)
    )


def _is_matching_port_assert(child: ast.AST, source: str, port_name: str) -> bool:
    if not isinstance(child, ast.Assert) or not isinstance(child.test, ast.Call):
        return False
    func = child.test.func
    if not isinstance(func, ast.Name) or func.id != "isinstance":
        return False
    func_source = ast.get_source_segment(source, child)
    return bool(func_source and port_name in func_source)
