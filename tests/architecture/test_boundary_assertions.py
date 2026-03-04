"""Tests for boundary validation assertions in composition factories.

Verifies that composition-layer factory methods include isinstance()
assertions to validate that concrete adapters implement their port protocols.

These assertions act as a safety net at the composition boundary,
catching DI wiring mistakes early at assembly time rather than at runtime.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

SRC_ROOT = Path("src/bioetl/composition")

# Factory methods that MUST contain isinstance() boundary assertions.
# Format: (module_path_relative_to_src, function_or_method_name)
EXPECTED_ASSERTIONS = [
    ("factories/services_factory.py", "_create_lock", "LockPort"),
    ("factories/services_factory.py", "_create_checkpoint", "CheckpointPort"),
    ("factories/services_factory.py", "_create_quarantine", "QuarantinePort"),
    ("factories/services_factory.py", "_create_metrics", "MetricsPort"),
    ("factories/data_source_factory.py", "create", "DataSourcePort"),
    (
        "bootstrap/assembly/checkpoint.py",
        "bootstrap_quarantine_port",
        "QuarantinePort",
    ),
    (
        "bootstrap/assembly/checkpoint.py",
        "bootstrap_checkpoint_port",
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

        # Find the function/method body
        func_body_found = False
        has_isinstance_assert = False

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    func_body_found = True
                    # Check for assert isinstance(...) in function body
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assert) and isinstance(
                            child.test, ast.Call
                        ):
                            func = child.test.func
                            if isinstance(func, ast.Name) and func.id == "isinstance":
                                # Verify the port name appears in the assertion
                                func_source = ast.get_source_segment(source, child)
                                if func_source and port_name in func_source:
                                    has_isinstance_assert = True

        assert func_body_found, f"Function '{func_name}' not found in {module_path}"
        assert has_isinstance_assert, (
            f"Function '{func_name}' in {module_path} MUST contain "
            f"`assert isinstance(..., {port_name})` for boundary validation."
        )


class TestBoundaryAssertionsSufficiency:
    """At least 5 factory methods MUST have boundary assertions."""

    def test_minimum_assertion_count(self) -> None:
        """At least 5 factory methods must have boundary assertions."""
        count = 0
        for module_path, func_name, port_name in EXPECTED_ASSERTIONS:
            source_file = SRC_ROOT / module_path
            if not source_file.exists():
                continue
            source = source_file.read_text()
            if f"isinstance(" in source and port_name in source:
                count += 1

        assert count >= 5, (
            f"Expected at least 5 factory methods with boundary assertions, "
            f"found {count}."
        )
