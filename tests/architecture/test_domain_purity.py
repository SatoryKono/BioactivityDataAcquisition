"""Architecture tests: Domain layer purity and immutability.

These tests ensure the domain layer follows pure function principles:
- Value Objects are immutable (frozen dataclasses)
- No direct I/O operations
- Low cyclomatic complexity
- No mutable default arguments

REQ-ARCH-010: Domain layer should be simple and testable.
REQ-ARCH-014: Domain entities must be immutable.

See CLAUDE.md §2 Architecture and §11 Anti-Patterns.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


class TestDomainImmutability:
    """Tests ensuring domain value objects are properly immutable."""

    def test_domain_value_objects_are_frozen(self, src_dir: Path) -> None:
        """Domain Value Objects (dataclasses) must be frozen.

        REQ-ARCH-014: Domain entities and value objects must be immutable
        to ensure side-effect-free behavior and thread safety.
        """
        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        violations = []

        for py_file in domain_path.rglob("*.py"):
            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for @dataclass decorator
                    is_dataclass = False
                    is_frozen = False

                    for decorator in node.decorator_list:
                        # Case 1: @dataclass
                        if (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "dataclass"
                        ):
                            is_dataclass = True
                            # Default is frozen=False

                        # Case 2: @dataclass(...)
                        elif isinstance(decorator, ast.Call):
                            func = decorator.func
                            if isinstance(func, ast.Name) and func.id == "dataclass":
                                is_dataclass = True
                                # Check keywords for frozen=True
                                for keyword in decorator.keywords:
                                    if (
                                        keyword.arg == "frozen"
                                        and isinstance(keyword.value, ast.Constant)
                                        and keyword.value.value is True
                                    ):
                                        is_frozen = True

                    if is_dataclass and not is_frozen:
                        violations.append(
                            f"{py_file.name}:{node.lineno} - {node.name} is not frozen"
                        )

        assert (
            not violations
        ), "Found mutable domain dataclasses (must be frozen=True):\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_no_mutable_defaults_in_frozen_dataclasses(self, src_dir: Path) -> None:
        """Frozen dataclasses should not have mutable default arguments.

        REQ-ARCH-016: Mutable defaults (list, dict, set) in dataclasses
        cause shared state issues even if the class is frozen.
        """
        bioetl_path = src_dir / "bioetl"
        if not bioetl_path.exists():
            pytest.skip("bioetl source not found")

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a dataclass
                    is_dataclass = False
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "dataclass"
                        ) or (
                            isinstance(decorator, ast.Call)
                            and (
                                isinstance(decorator.func, ast.Name)
                                and decorator.func.id == "dataclass"
                            )
                        ):
                            is_dataclass = True

                    if not is_dataclass:
                        continue

                    # Check fields for mutable defaults
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            if item.value:  # Has a default value
                                is_mutable = False
                                if isinstance(
                                    item.value, (ast.List, ast.Dict, ast.Set)
                                ):
                                    is_mutable = True
                                elif isinstance(item.value, ast.Call):
                                    # Check for simple calls like list(), dict(), set()
                                    if isinstance(
                                        item.value.func, ast.Name
                                    ) and item.value.func.id in ("list", "dict", "set"):
                                        is_mutable = True

                                if is_mutable:
                                    violations.append(
                                        f"{py_file.name}:{item.lineno} - Field "
                                        f"'{getattr(item.target, 'id', 'unknown')}' "
                                        f"in class '{node.name}' has a mutable default value."
                                    )

        assert not violations, (
            "Found mutable defaults in dataclasses "
            "(use field(default_factory=...) instead):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestDomainPurity:
    """Tests ensuring domain layer has no I/O or side effects."""

    def test_no_direct_io_in_domain(self, src_dir: Path) -> None:
        """Verify domain layer has no direct I/O operations.

        REQ-ARCH-003: Domain layer should be pure business logic without I/O.
        """
        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        # Patterns that indicate direct I/O
        io_patterns = [
            (r"\bopen\s*\(", "open() file access"),
            (r"Path\s*\([^)]+\)\s*\.\s*(read|write|mkdir|unlink)", "Path I/O methods"),
            (r"os\.(read|write|mkdir|remove|rename)", "os module I/O"),
            (r"shutil\.(copy|move|rmtree)", "shutil I/O operations"),
        ]

        # Excluded files
        excluded_files = {"__init__.py"}

        violations = []

        for py_file in domain_path.rglob("*.py"):
            if py_file.name in excluded_files:
                continue

            with py_file.open(encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue

                for pattern, description in io_patterns:
                    if re.search(pattern, line):
                        relative_path = py_file.relative_to(src_dir)
                        violations.append(
                            f"{relative_path}:{i} - {description}: {stripped[:60]}..."
                        )

        assert not violations, (
            "Domain layer should not have direct I/O operations.\n"
            "Found violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestDomainComplexity:
    """Tests ensuring domain layer maintains low complexity."""

    def test_cyclomatic_complexity_domain_layer(self, src_dir: Path) -> None:
        """Domain layer functions should have low cyclomatic complexity.

        REQ-ARCH-010: Domain logic should be simple and testable.
        Maximum CC = 5 for domain layer functions.
        """
        try:
            from radon.complexity import cc_visit
        except ImportError:
            pytest.skip("radon not installed")

        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        # Exemptions for specific functions (baseline)
        exemptions = {
            "__post_init__": 12,  # Dataclass post-init validation with complex context
            "SchemaEvolutionError": 7,  # Exception with detailed field tracking
        }

        violations = []
        max_cc = 5  # Strict threshold for domain layer

        for py_file in domain_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            with py_file.open(encoding="utf-8") as f:
                content = f.read()

            try:
                results = cc_visit(content)
                for item in results:
                    func_max_cc = exemptions.get(item.name, max_cc)
                    if item.complexity > func_max_cc:
                        violations.append(
                            f"{py_file}:{item.lineno} - {item.name}() "
                            f"has CC={item.complexity} (max={func_max_cc})"
                        )
            except SyntaxError:
                continue

        assert (
            not violations
        ), f"Domain layer has functions with CC > {max_cc}:\n" + "\n".join(violations)


class TestDomainProtocols:
    """Tests ensuring domain layer properly defines ports."""

    def test_domain_layer_uses_protocol_for_ports(self, src_dir: Path) -> None:
        """Domain layer should use Protocol for defining ports.

        REQ-ARCH-009: Ports should be defined using typing.Protocol
        for structural subtyping (duck typing with type safety).
        """
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("ports/ package not found")

        # Check at least one port file uses Protocol
        protocol_import_found = False
        protocol_class_found = False

        for port_file in ports_dir.glob("*.py"):
            if port_file.name == "__init__.py":
                continue
            with port_file.open(encoding="utf-8") as f:
                content = f.read()
                if "from typing" in content and "Protocol" in content:
                    protocol_import_found = True
                if "class" in content and "(Protocol)" in content:
                    protocol_class_found = True
                if protocol_import_found and protocol_class_found:
                    break

        assert (
            protocol_import_found
        ), "Domain ports should use typing.Protocol for interface definitions"
        assert (
            protocol_class_found
        ), "Port interfaces should be classes inheriting from Protocol"
