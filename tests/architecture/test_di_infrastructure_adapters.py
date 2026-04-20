"""Architecture test: DI compliance for infrastructure adapter constructors.

REQ-ARCH-DI-012: Infrastructure adapter constructors MUST NOT unconditionally
instantiate cross-cutting helper services (ErrorService, AdapterMetricsRecorder).

These services should be accepted as optional constructor parameters with
inline creation only as a fallback when not injected (behind ``if ... is None``
guard). This enables composition-root injection via AdapterHelpersFactory.

Allowed pattern (conditional fallback):
    self._error_handler = (
        error_handler if error_handler is not None
        else ErrorService(logger, metrics=self._metrics)
    )

Forbidden pattern (unconditional):
    self._error_handler = ErrorService(logger, metrics=self._metrics)

See ai-selfreview-rules.md §2 Anti-Patterns (AP-001, DI-001).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

ADAPTERS_DIR = Path("src/bioetl/infrastructure/adapters")

# Cross-cutting services that MUST use conditional instantiation in adapters.
GUARDED_SERVICE_CLASSES: frozenset[str] = frozenset(
    {"ErrorService", "AdapterMetricsRecorder"}
)

# Files where unconditional instantiation is expected (class definitions).
DEFINITION_FILES: frozenset[str] = frozenset(
    {
        "error_handling.py",
        "base_metrics.py",
        "adapter_helpers_factory.py",
    }
)


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


class Violation(NamedTuple):
    """Unconditional service instantiation found in adapter constructor."""

    file_path: Path
    line_number: int
    service_class: str
    containing_class: str
    method_name: str


class _UnconditionalInstantiationFinder(ast.NodeVisitor):
    """AST visitor detecting unconditional service instantiation in init methods.

    Considers an instantiation *guarded* when it appears inside any ``If``
    node within the init body.  A top-level ``self.x = Service(...)``
    (outside any ``if``) is flagged as unconditional.
    """

    def __init__(self, guarded_classes: frozenset[str]) -> None:
        self._guarded = guarded_classes
        self.violations: list[tuple[int, str, str, str]] = []
        self._current_class: str | None = None
        self._in_init_method: str | None = None
        self._if_depth: int = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in ("__init__", "__post_init__"):
            old = self._in_init_method
            self._in_init_method = node.name
            self.generic_visit(node)
            self._in_init_method = old
        else:
            self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def _visit_guarded_branch(self, node: ast.AST) -> None:
        self._if_depth += 1
        self.generic_visit(node)
        self._if_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._visit_guarded_branch(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        # Inline ternary ``x if cond else Service(...)`` is guarded.
        self._visit_guarded_branch(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assignment(node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._check_assignment(node.value, node.lineno)
        self.generic_visit(node)

    # ------------------------------------------------------------------

    def _check_assignment(self, value: ast.expr, lineno: int) -> None:
        if self._in_init_method is None:
            return
        if self._if_depth > 0:
            return  # Inside an if-guard — allowed

        called = self._extract_class_name(value)
        if called and called in self._guarded:
            self.violations.append(
                (
                    lineno,
                    called,
                    self._current_class or "<module>",
                    self._in_init_method,
                )
            )

    @staticmethod
    def _extract_class_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None


class TestInfrastructureAdapterDI:
    """Ensure cross-cutting services use conditional instantiation."""

    @pytest.fixture()
    def adapter_python_files(self) -> list[Path]:
        base = _get_base_path(ADAPTERS_DIR)
        if not base.exists():
            pytest.skip("Infrastructure adapters directory not found")
        return [
            p
            for p in base.rglob("*.py")
            if p.name not in DEFINITION_FILES and not p.name.startswith("__")
        ]

    def test_no_unconditional_service_instantiation(
        self,
        adapter_python_files: list[Path],
    ) -> None:
        """Adapter __init__/__post_init__ MUST guard service instantiation.

        Cross-cutting helpers (ErrorService, AdapterMetricsRecorder) must be behind
        an ``if ... is None`` check so that AdapterHelpersFactory can inject
        pre-built instances from the composition root.
        """
        violations: list[Violation] = []

        for py_file in adapter_python_files:
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
            finder.visit(tree)

            for lineno, svc, cls, method in finder.violations:
                violations.append(Violation(py_file, lineno, svc, cls, method))

        if violations:
            base = _get_base_path(ADAPTERS_DIR)
            lines = [
                f"  - {v.file_path.relative_to(base)}:{v.line_number}: "
                f"{v.containing_class}.{v.method_name}: "
                f"unconditional {v.service_class}()"
                for v in violations
            ]
            pytest.fail(
                "Infrastructure DI violation: unconditional service "
                "instantiation in adapter constructors.\n"
                "Cross-cutting services MUST be guarded with "
                "`if <param> is None` for composition-root injection.\n\n"
                "Violations:\n" + "\n".join(lines) + "\n\n"
                "Fix: accept optional parameter and use conditional:\n"
                "  self._error_handler = (\n"
                "      error_handler if error_handler is not None\n"
                "      else ErrorService(...)\n"
                "  )"
            )


class TestInfrastructureAdapterDIDetection:
    """Regression tests for the AST detection mechanism."""

    def test_detects_unconditional(self) -> None:
        code = """
class BadAdapter:
    def __init__(self):
        self._error_handler = ErrorService(logger)
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 1
        assert finder.violations[0][1] == "ErrorService"

    def test_allows_guarded_if(self) -> None:
        code = """
class GoodAdapter:
    def __init__(self, error_handler=None):
        if error_handler is not None:
            self._error_handler = error_handler
        else:
            self._error_handler = ErrorService(logger)
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 0

    def test_allows_ternary(self) -> None:
        code = """
class GoodAdapter:
    def __init__(self, error_handler=None):
        self._error_handler = (
            error_handler if error_handler is not None
            else ErrorService(logger)
        )
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 0

    def test_ignores_outside_init(self) -> None:
        code = """
class SomeAdapter:
    def __init__(self):
        pass

    def setup(self):
        self._error_handler = ErrorService(logger)
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 0

    def test_detects_in_post_init(self) -> None:
        code = """
class BadDataclass:
    def __post_init__(self):
        self._adapter_metrics = AdapterMetricsRecorder(metrics, "provider")
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 1
        assert finder.violations[0][1] == "AdapterMetricsRecorder"

    def test_allows_injected_assignment(self) -> None:
        code = """
class GoodAdapter:
    def __init__(self, error_handler):
        self._error_handler = error_handler
"""
        tree = ast.parse(code)
        finder = _UnconditionalInstantiationFinder(GUARDED_SERVICE_CLASSES)
        finder.visit(tree)
        assert len(finder.violations) == 0
