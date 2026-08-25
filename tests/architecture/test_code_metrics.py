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
"""Tests for code quality metrics.

Enforces size and complexity limits across the codebase.
Implements CLAUDE.md §6.3.1 requirements.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.infrastructure.quality import (
    build_module_path_key,
    get_registry_values,
    resolve_registry_value,
)


pytestmark = pytest.mark.architecture


def _layer_path(src_dir: Path, layer: str) -> Path:
    return src_dir / "bioetl" / layer


def _iter_layer_python_items(
    src_dir: Path,
    layer: str,
    source_content_cache: dict | None = None,
) -> list[tuple[Path, str]]:
    layer_path = _layer_path(src_dir, layer)
    if not layer_path.exists():
        pytest.skip(f"{layer} layer not found")
    if source_content_cache is not None:
        return [
            (p, c)
            for p, c in source_content_cache.items()
            if layer_path in p.parents and not p.name.startswith("__")
        ]
    return [
        (p, p.read_text(encoding="utf-8"))
        for p in layer_path.rglob("*.py")
        if not p.name.startswith("__")
    ]


def _module_registry_value(
    registry: dict,
    src_dir: Path,
    py_file: Path,
    *,
    symbol_name: str | None = None,
    legacy_name: str | None = None,
) -> int | None:
    return resolve_registry_value(
        registry,
        module_path=build_module_path_key(py_file, src_root=src_dir),
        symbol_name=symbol_name,
        legacy_name=legacy_name,
    )


def _line_span(node: ast.AST) -> tuple[int, int, int]:
    start_line = node.lineno
    end_line = getattr(node, "end_lineno", None) or start_line
    return start_line, end_line, end_line - start_line + 1


def _iter_ast_items(
    source_ast_cache: dict,
    node_types: tuple[type[ast.AST], ...],
) -> list[tuple[Path, ast.AST]]:
    items: list[tuple[Path, ast.AST]] = []
    for py_file, tree in source_ast_cache.items():
        if py_file.name.startswith("__"):
            continue
        for node in ast.walk(tree):
            if isinstance(node, node_types):
                items.append((py_file, node))
    return items


class TestFileSizeLimits:
    """Enforce maximum file size limits by layer."""

    # Layer-specific limits (in lines of code)
    LAYER_LIMITS = {
        "domain": 305,  # Domain should be small and focused
        "application": 411,  # Application can be larger
        "composition": 350,  # Composition is wiring only (buffer below hard cap)
        "infrastructure": 443,  # Infrastructure adapters may be complex
        "interfaces": 418,  # CLI and entry points
    }

    # Exemptions are managed in configs/quality/architecture_metric_exemptions.yaml
    EXEMPTIONS = get_registry_values("file_size_limits")

    def test_domain_files_under_limit(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Domain layer files must be under 300 LOC."""
        self._check_layer(
            src_dir, "domain", self.LAYER_LIMITS["domain"], source_content_cache
        )
        assert self.LAYER_LIMITS["domain"] == 305

    def test_application_files_under_limit(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Application layer files must be under 500 LOC."""
        self._check_layer(
            src_dir,
            "application",
            self.LAYER_LIMITS["application"],
            source_content_cache,
        )
        assert self.LAYER_LIMITS["application"] == 411

    def test_composition_files_under_limit(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Composition layer files must be under 400 LOC."""
        self._check_layer(
            src_dir,
            "composition",
            self.LAYER_LIMITS["composition"],
            source_content_cache,
        )
        assert self.LAYER_LIMITS["composition"] == 350

    def test_infrastructure_files_under_limit(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Infrastructure layer files must be under 600 LOC."""
        self._check_layer(
            src_dir,
            "infrastructure",
            self.LAYER_LIMITS["infrastructure"],
            source_content_cache,
        )
        assert self.LAYER_LIMITS["infrastructure"] == 443

    def test_interfaces_files_under_limit(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Interfaces layer files must be under 400 LOC."""
        self._check_layer(
            src_dir, "interfaces", self.LAYER_LIMITS["interfaces"], source_content_cache
        )
        assert self.LAYER_LIMITS["interfaces"] == 418

    def _check_layer(
        self,
        src_dir: Path,
        layer: str,
        limit: int,
        source_content_cache: dict | None = None,
    ) -> None:
        """Check all files in a layer against the limit."""
        violations = []
        for py_file, content in _iter_layer_python_items(
            src_dir, layer, source_content_cache
        ):
            file_limit = _module_registry_value(
                self.EXEMPTIONS,
                src_dir,
                py_file,
                legacy_name=py_file.name,
            )
            if file_limit is None:
                file_limit = limit

            loc = len(content.splitlines())
            if loc > file_limit:
                violations.append(
                    f"{py_file.relative_to(src_dir)}: {loc} LOC (limit: {file_limit})"
                )

        assert not violations, f"Files exceeding LOC limit in {layer}:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


class TestFunctionComplexity:
    """Enforce cyclomatic complexity limits.

    Uses radon for complexity analysis.
    """

    MAX_COMPLEXITY = {
        "domain": 5,  # Domain must be simple
        "application": 10,  # Application can be complexity
        "infrastructure": 15,  # Adapters may need branching
    }

    # Exemptions are managed in configs/quality/architecture_metric_exemptions.yaml
    EXEMPTIONS = get_registry_values("function_complexity")

    def test_domain_complexity(self, src_dir: Path, source_content_cache: dict) -> None:
        """Domain functions must have CC <= 5."""
        self._check_layer(
            src_dir, "domain", self.MAX_COMPLEXITY["domain"], source_content_cache
        )
        assert self.MAX_COMPLEXITY["domain"] == 5

    def test_application_complexity(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Application functions must have CC <= 10."""
        self._check_layer(
            src_dir,
            "application",
            self.MAX_COMPLEXITY["application"],
            source_content_cache,
        )
        assert self.MAX_COMPLEXITY["application"] == 10

    def test_infrastructure_complexity(
        self, src_dir: Path, source_content_cache: dict
    ) -> None:
        """Infrastructure functions must have CC <= 15."""
        self._check_layer(
            src_dir,
            "infrastructure",
            self.MAX_COMPLEXITY["infrastructure"],
            source_content_cache,
        )
        assert self.MAX_COMPLEXITY["infrastructure"] == 15

    def _check_layer(
        self,
        src_dir: Path,
        layer: str,
        max_cc: int,
        source_content_cache: dict | None = None,
    ) -> None:
        """Check all functions in a layer for complexity."""
        try:
            from radon.complexity import cc_visit
        except ImportError:
            pytest.skip("radon not installed")

        violations = []
        for py_file, content in _iter_layer_python_items(
            src_dir, layer, source_content_cache
        ):
            try:
                results = cc_visit(content)
                for item in results:
                    func_max_cc = _module_registry_value(
                        self.EXEMPTIONS,
                        src_dir,
                        py_file,
                        symbol_name=item.name,
                    )
                    if func_max_cc is None:
                        func_max_cc = max_cc
                    if item.complexity > func_max_cc:
                        violations.append(
                            f"{py_file.relative_to(src_dir)}:{item.lineno} - {item.name}() "
                            f"CC={item.complexity} (max={func_max_cc})"
                        )
            except SyntaxError:
                continue

        assert not violations, (
            f"Functions with CC > {max_cc} in {layer}:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestFunctionLength:
    """Enforce maximum function length."""

    MAX_LINES = 100  # Maximum lines per function

    EXEMPTIONS = get_registry_values("function_length")

    # Ratchet policy: the current measured baseline is zero functions above 100 LOC.
    # Any new violation should fail immediately instead of being absorbed by a stale debt budget.
    MAX_VIOLATIONS = 0

    def _function_length_violation(
        self,
        src_dir: Path,
        py_file: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str | None:
        start_line, _, func_lines = _line_span(node)
        max_lines = _module_registry_value(
            self.EXEMPTIONS,
            src_dir,
            py_file,
            symbol_name=node.name,
        )
        if max_lines is None:
            max_lines = self.MAX_LINES
        if func_lines <= max_lines:
            return None
        return (
            f"{py_file.relative_to(src_dir)}:{start_line} - {node.name}() "
            f"is {func_lines} lines (max={max_lines})"
        )

    def test_functions_under_100_lines(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """All functions must be under 100 lines (with exemptions)."""
        violations = [
            violation
            for py_file, node in _iter_ast_items(
                source_ast_cache, (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            for violation in [self._function_length_violation(src_dir, py_file, node)]
            if violation is not None
        ]

        if len(violations) > self.MAX_VIOLATIONS:
            pytest.fail(
                f"Too many long functions ({len(violations)}, max={self.MAX_VIOLATIONS}):\n"
                + "\n".join(f"  - {v}" for v in violations[:15])
            )


class TestClassSize:
    """Enforce maximum class size limits."""

    MAX_CLASS_LINES = 300  # Maximum lines per class
    MAX_METHODS_PER_CLASS = 20  # Maximum methods per class

    METHOD_EXEMPTIONS = get_registry_values("class_method_count")

    EXEMPTIONS = get_registry_values("class_size")

    def _public_method_count(self, node: ast.ClassDef) -> int:
        return sum(
            1
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not item.name.startswith("_")
        )

    def _class_size_violation(
        self,
        src_dir: Path,
        py_file: Path,
        node: ast.ClassDef,
    ) -> str | None:
        start_line, _, class_lines = _line_span(node)
        max_lines = _module_registry_value(
            self.EXEMPTIONS,
            src_dir,
            py_file,
            symbol_name=node.name,
        )
        if max_lines is None:
            max_lines = self.MAX_CLASS_LINES
        if class_lines <= max_lines:
            return None
        return (
            f"{py_file.relative_to(src_dir)}:{start_line} - {node.name} "
            f"is {class_lines} lines (max={max_lines})"
        )

    def _class_method_violation(
        self,
        src_dir: Path,
        py_file: Path,
        node: ast.ClassDef,
    ) -> str | None:
        public_method_count = self._public_method_count(node)
        max_methods = _module_registry_value(
            self.METHOD_EXEMPTIONS,
            src_dir,
            py_file,
            symbol_name=node.name,
        )
        if max_methods is None:
            max_methods = self.MAX_METHODS_PER_CLASS
        if public_method_count <= max_methods:
            return None
        return (
            f"{py_file.relative_to(src_dir)} - {node.name} has "
            f"{public_method_count} public methods "
            f"(max={max_methods})"
        )

    def test_classes_under_300_lines(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """All classes must be under 300 lines (with exemptions)."""
        violations = [
            violation
            for py_file, node in _iter_ast_items(source_ast_cache, (ast.ClassDef,))
            for violation in [self._class_size_violation(src_dir, py_file, node)]
            if violation is not None
        ]

        if violations:
            pytest.fail(
                "Classes exceeding line limit:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )

    def test_classes_under_20_methods(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """Classes should not have more than 20 public methods."""
        violations = [
            violation
            for py_file, node in _iter_ast_items(source_ast_cache, (ast.ClassDef,))
            for violation in [self._class_method_violation(src_dir, py_file, node)]
            if violation is not None
        ]

        if violations:
            pytest.fail(
                "Classes with too many methods:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )


class TestGodObjectDetection:
    """Detect god objects via delegation pattern analysis.

    God objects are large classes with low delegation that try to do everything
    themselves. This test enforces that large classes (>300 lines) must delegate
    to injected dependencies, not implement all logic internally.

    Implements CLAUDE.md §2.3 god object detection requirements.
    """

    MIN_CLASS_LINES_FOR_CHECK = 300  # Only check large classes
    MIN_DELEGATION_CALLS = 3  # Minimum self._component.method() patterns

    EXEMPTIONS = get_registry_values("god_object")

    def _class_line_count(self, class_node: ast.ClassDef) -> int:
        start_line = class_node.lineno
        end_line = class_node.end_lineno or start_line
        return end_line - start_line + 1

    def _is_exempt_class(
        self, src_dir: Path, py_file: Path, class_node: ast.ClassDef
    ) -> bool:
        return (
            resolve_registry_value(
                self.EXEMPTIONS,
                module_path=build_module_path_key(py_file, src_root=src_dir),
                symbol_name=class_node.name,
            )
            is not None
        )

    def _iter_candidate_classes(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> list[tuple[Path, ast.ClassDef, int]]:
        candidates: list[tuple[Path, ast.ClassDef, int]] = []
        for py_file, tree in source_ast_cache.items():
            if py_file.name.startswith("__"):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if self._is_exempt_class(src_dir, py_file, node):
                    continue
                class_lines = self._class_line_count(node)
                if class_lines >= self.MIN_CLASS_LINES_FOR_CHECK:
                    candidates.append((py_file, node, class_lines))
        return candidates

    def _delegation_violation(
        self,
        py_file: Path,
        class_node: ast.ClassDef,
        class_lines: int,
        delegation_count: int,
    ) -> str:
        return (
            f"{py_file.name}:{class_node.lineno} - {class_node.name} "
            f"({class_lines} lines, {delegation_count} delegations) "
            f"- large class with low delegation (potential god object)"
        )

    def test_large_classes_have_delegation(
        self,
        src_dir: Path,
        source_ast_cache: dict,
    ) -> None:
        """Large classes (>300 LOC) must show delegation patterns.

        Delegation is identified by:
        - Injected dependencies (self._<component>)
        - Method calls on dependencies (self._<component>.<method>())
        - Use of composition over monolithic implementation

        Exemptions are allowed for specific patterns (see EXEMPTIONS dict).
        """
        violations = []
        for py_file, node, class_lines in self._iter_candidate_classes(
            src_dir, source_ast_cache
        ):
            delegation_count = self._count_delegation_calls(node)
            if delegation_count < self.MIN_DELEGATION_CALLS:
                violations.append(
                    self._delegation_violation(
                        py_file,
                        node,
                        class_lines,
                        delegation_count,
                    )
                )

        if violations:
            pytest.fail(
                "Potential god objects detected (large classes with low delegation):\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nOptions to fix:\n"
                + "  1. Extract logic to specialized services and delegate\n"
                + "  2. Add to EXEMPTIONS with documented reason\n"
                + "  3. Reduce class size below 300 lines"
            )

    def _count_delegation_calls(self, class_node: ast.ClassDef) -> int:
        """Count self._component.method() patterns in class.

        Delegation is indicated by:
        - Attribute access on private attributes: self._foo.bar()
        - Method calls on composed objects

        Returns:
            Number of unique delegation patterns found.
        """
        delegations = {
            pattern
            for node in ast.walk(class_node)
            if (pattern := self._delegation_pattern(node)) is not None
        }
        return len(delegations)

    def _delegation_pattern(self, node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return None
        value = node.func.value
        if not isinstance(value, ast.Attribute):
            return None
        if not isinstance(value.value, ast.Name) or value.value.id != "self":
            return None
        if not value.attr.startswith("_"):
            return None
        return f"{value.attr}.{node.func.attr}"
