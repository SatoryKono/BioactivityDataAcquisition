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
import importlib.util
import re
from pathlib import Path

import pytest

from bioetl.infrastructure.quality import (
    build_module_path_key,
    get_registry_values,
    resolve_registry_value,
)


def _dataclass_flags(node: ast.ClassDef) -> tuple[bool, bool]:
    is_dataclass = False
    is_frozen = False
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            is_dataclass = True
            continue
        if not isinstance(decorator, ast.Call):
            continue
        if not (
            isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass"
        ):
            continue
        is_dataclass = True
        for keyword in decorator.keywords:
            if (
                keyword.arg == "frozen"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
            ):
                is_frozen = True
    return is_dataclass, is_frozen


def _has_mutable_default(node: ast.AnnAssign) -> bool:
    if node.value is None:
        return False
    if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
        return True
    return (
        isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id in {"list", "dict", "set"}
    )


def _io_violations_in_content(
    *,
    content: str,
    relative_path: Path,
    io_patterns: list[tuple[str, str]],
) -> list[str]:
    violations: list[str] = []
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        for pattern, description in io_patterns:
            if re.search(pattern, line):
                violations.append(
                    f"{relative_path}:{lineno} - {description}: {stripped[:60]}..."
                )
    return violations


def _complexity_violations_for_content(
    *,
    py_file: Path,
    content: str,
    src_dir: Path,
    exemptions: object,
    default_max_cc: int,
) -> list[str]:
    from radon.complexity import cc_visit

    violations: list[str] = []
    try:
        results = cc_visit(content)
    except SyntaxError:
        return violations

    for item in results:
        func_max_cc = resolve_registry_value(
            exemptions,
            module_path=build_module_path_key(py_file, src_root=src_dir),
            symbol_name=item.name,
        )
        if func_max_cc is None:
            func_max_cc = default_max_cc
        if item.complexity > func_max_cc:
            violations.append(
                f"{py_file}:{item.lineno} - {item.name}() "
                f"has CC={item.complexity} (max={func_max_cc})"
            )
    return violations


def _iter_class_defs(tree: ast.AST) -> list[ast.ClassDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _iter_domain_class_defs(
    source_ast_cache: dict,
    *,
    domain_path: Path,
) -> list[tuple[Path, ast.ClassDef]]:
    return [
        (py_file, node)
        for py_file, tree in source_ast_cache.items()
        if domain_path in py_file.parents
        for node in _iter_class_defs(tree)
    ]


def _non_frozen_dataclass_violation(
    *,
    py_file: Path,
    node: ast.ClassDef,
    mutable_service_exemptions: set[str],
) -> str | None:
    is_dataclass, is_frozen = _dataclass_flags(node)
    if not is_dataclass or is_frozen:
        return None
    if node.name in mutable_service_exemptions:
        return None
    return f"{py_file.name}:{node.lineno} - {node.name} is not frozen"


def _mutable_default_violations_for_class(
    *,
    py_file: Path,
    node: ast.ClassDef,
) -> list[str]:
    violations: list[str] = []
    is_dataclass, _is_frozen = _dataclass_flags(node)
    if not is_dataclass:
        return violations
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and _has_mutable_default(item):
            violations.append(
                f"{py_file.name}:{item.lineno} - Field "
                f"'{getattr(item.target, 'id', 'unknown')}' "
                f"in class '{node.name}' has a mutable default value."
            )
    return violations


class TestDomainImmutability:
    """Tests ensuring domain value objects are properly immutable."""

    # Domain service classes that are legitimately mutable (not value objects)
    MUTABLE_SERVICE_EXEMPTIONS = {
        # Service classes that hold configuration/dependencies
        "ActivityAggregator",  # Service with aggregation strategies
        "NormalizationResult",  # Result dataclass from service (could be frozen, but exempted)
        "NormalizationService",  # Service with validation logic
        "ValueValidator",  # Service with validation configuration
    }

    def test_domain_value_objects_are_frozen(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """Domain Value Objects (dataclasses) must be frozen.

        REQ-ARCH-014: Domain entities and value objects must be immutable
        to ensure side-effect-free behavior and thread safety.
        """
        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        violations = []

        for py_file, node in _iter_domain_class_defs(
            source_ast_cache, domain_path=domain_path
        ):
            violation = _non_frozen_dataclass_violation(
                py_file=py_file,
                node=node,
                mutable_service_exemptions=self.MUTABLE_SERVICE_EXEMPTIONS,
            )
            if violation is not None:
                violations.append(violation)

        assert not violations, (
            "Found mutable domain dataclasses (must be frozen=True):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_mutable_defaults_in_frozen_dataclasses(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """Frozen dataclasses should not have mutable default arguments.

        REQ-ARCH-016: Mutable defaults (list, dict, set) in dataclasses
        cause shared state issues even if the class is frozen.
        """
        violations = []

        for py_file, tree in source_ast_cache.items():
            for node in _iter_class_defs(tree):
                violations.extend(
                    _mutable_default_violations_for_class(
                        py_file=py_file,
                        node=node,
                    )
                )

        assert not violations, (
            "Found mutable defaults in dataclasses "
            "(use field(default_factory=...) instead):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestDomainPurity:
    """Tests ensuring domain layer has no I/O or side effects."""

    def test_no_direct_io_in_domain(
        self,
        src_dir: Path,
        source_content_cache: dict,
    ) -> None:
        """Verify domain layer has no direct I/O operations.

        REQ-ARCH-003: Domain layer should be pure business logic without I/O.
        """
        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        # Patterns that indicate direct I/O
        io_patterns = [
            (r"\bopen\s*\(", "open() file access"),
            (
                r"Path\s*\([^)]+\)\s*\.\s*(read|write|mkdir|unlink|exists)",
                "Path I/O methods",
            ),
            (r"os\.(read|write|mkdir|remove|rename)", "os module I/O"),
            (r"shutil\.(copy|move|rmtree)", "shutil I/O operations"),
        ]

        # Excluded files
        excluded_files = {"__init__.py"}

        violations = []

        for py_file, content in source_content_cache.items():
            if domain_path not in py_file.parents:
                continue
            if py_file.name in excluded_files:
                continue
            violations.extend(
                _io_violations_in_content(
                    content=content,
                    relative_path=py_file.relative_to(src_dir),
                    io_patterns=io_patterns,
                )
            )

        assert not violations, (
            "Domain layer should not have direct I/O operations.\n"
            "Found violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestDomainComplexity:
    """Tests ensuring domain layer maintains low complexity."""

    def test_cyclomatic_complexity_domain_layer(
        self,
        src_dir: Path,
        source_content_cache: dict,
    ) -> None:
        """Domain layer functions should have low cyclomatic complexity.

        REQ-ARCH-010: Domain logic should be simple and testable.
        Maximum CC = 5 for domain layer functions.
        """
        if importlib.util.find_spec("radon.complexity") is None:
            pytest.skip("radon not installed")

        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        exemptions = get_registry_values("domain_complexity")

        violations = []
        max_cc = 5  # Strict threshold for domain layer

        for py_file, content in source_content_cache.items():
            if domain_path not in py_file.parents:
                continue
            if py_file.name.startswith("__"):
                continue
            violations.extend(
                _complexity_violations_for_content(
                    py_file=py_file,
                    content=content,
                    src_dir=src_dir,
                    exemptions=exemptions,
                    default_max_cc=max_cc,
                )
            )

        assert not violations, (
            f"Domain layer has functions with CC > {max_cc}:\n" + "\n".join(violations)
        )


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

        assert protocol_import_found, (
            "Domain ports should use typing.Protocol for interface definitions"
        )
        assert protocol_class_found, (
            "Port interfaces should be classes inheriting from Protocol"
        )
