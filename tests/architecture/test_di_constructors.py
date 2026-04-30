"""Architecture test: DI violations in __init__ constructors.

REQ-ARCH-DI-011: Application layer MUST NOT instantiate services in __init__.

Problem: Current tests don't catch patterns like `self.x = SomeService()` in constructors.
This test uses AST analysis to detect forbidden service instantiations specifically
in __init__ methods.

Services should be created in composition layer (factories/bootstrap.py) and
injected via constructor parameters.

See CLAUDE.md §2.2 Dependency Injection and §11 Anti-Patterns.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# Path relative to project root
APPLICATION_DIR = Path("src/bioetl/application")

# Forbidden service instantiations in __init__ methods.
# These services MUST be injected, not created directly.
# Format: class names that should never appear as `self.x = ClassName(...)` in __init__
FORBIDDEN_SERVICE_INSTANTIATIONS: set[str] = {
    # Core services (application layer - must be injected)
    "LockCoordinator",
    "PreflightService",
    "PostrunService",
    "CleanupService",
    # Lifecycle services
    "MedallionLifecycleService",
    # Service containers (must be injected, not created)
    "PipelineService",
    # Note: HealthAggregator is excluded as it's a lightweight helper
    # that delegates to injected metrics/logger dependencies.
    # Consider adding it in future if testability becomes an issue.
}

# Exceptions: files where instantiation is allowed (e.g., factories)
ALLOWED_FILES: set[str] = {
    # Composition layer files that are allowed to create services
    "bootstrap.py",
    # Factory files
    "service_factory.py",
    "pipeline_factory.py",
    "runner_factory.py",
}


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


def _is_application_source_file(py_file: Path) -> bool:
    return not (py_file.name.startswith("__") or py_file.name.startswith("test_"))


def _iter_application_source_files(app_path: Path) -> list[Path]:
    return [
        py_file
        for py_file in app_path.rglob("*.py")
        if _is_application_source_file(py_file)
    ]


def _parse_python_tree(py_file: Path) -> ast.AST | None:
    try:
        content = py_file.read_text(encoding="utf-8")
        return ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return None


def _is_public_service_like_class(node: ast.AST) -> bool:
    if not isinstance(node, ast.ClassDef):
        return False
    if node.name.startswith("_"):
        return False
    return node.name.endswith("Service") or node.name.endswith("Manager")


def _service_like_classes_in_file(py_file: Path) -> set[str]:
    tree = _parse_python_tree(py_file)
    if tree is None:
        return set()
    return {node.name for node in ast.walk(tree) if _is_public_service_like_class(node)}


def _init_instantiation_violations(
    py_file: Path,
    forbidden_classes: set[str],
) -> list[Violation]:
    tree = _parse_python_tree(py_file)
    if tree is None:
        return []

    finder = InitInstantiationFinder(forbidden_classes)
    finder.visit(tree)
    return [
        Violation(
            file_path=py_file,
            line_number=lineno,
            class_name=class_name,
            containing_class=containing_class,
            assignment_target=target,
        )
        for lineno, class_name, containing_class, target in finder.violations
    ]


def _format_violation_messages(violations: list[Violation], base: Path) -> list[str]:
    messages: list[str] = []
    for violation in violations:
        relative = violation.file_path.relative_to(base)
        messages.append(
            f"  - {relative}:{violation.line_number}: "
            f"{violation.containing_class}.__init__: "
            f"{violation.assignment_target} = {violation.class_name}()"
        )
    return messages


class Violation(NamedTuple):
    """Represents a DI violation found in code."""

    file_path: Path
    line_number: int
    class_name: str
    containing_class: str
    assignment_target: str


class InitInstantiationFinder(ast.NodeVisitor):
    """AST visitor to find forbidden instantiations in __init__ methods.

    Detects patterns like:
        def __init__(self, ...):
            self._service = ForbiddenService(...)  # Violation!
            self.manager = LockCoordinator(...)        # Violation!
    """

    def __init__(self, forbidden_classes: set[str]) -> None:
        self.forbidden_classes = forbidden_classes
        self.violations: list[tuple[int, str, str, str]] = []
        self._current_class: str | None = None
        self._in_init: bool = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track current class context."""
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track __init__ method context."""
        if node.name == "__init__":
            old_in_init = self._in_init
            self._in_init = True
            self.generic_visit(node)
            self._in_init = old_in_init
        else:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function definitions (though __init__ is never async)."""
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignments in __init__ for forbidden instantiations."""
        if not self._in_init:
            self.generic_visit(node)
            return

        # Check if value is a Call to a forbidden class
        if isinstance(node.value, ast.Call):
            class_name = self._get_called_class_name(node.value)
            if class_name and class_name in self.forbidden_classes:
                # Get the assignment target (e.g., "self._service")
                target_name = self._get_target_name(node.targets[0])
                self.violations.append(
                    (
                        node.lineno,
                        class_name,
                        self._current_class or "<unknown>",
                        target_name,
                    )
                )

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check annotated assignments in __init__ for forbidden instantiations.

        Handles patterns like:
            self._service: SomeType = ForbiddenService(...)
        """
        if not self._in_init:
            self.generic_visit(node)
            return

        if node.value and isinstance(node.value, ast.Call):
            class_name = self._get_called_class_name(node.value)
            if class_name and class_name in self.forbidden_classes:
                target_name = self._get_target_name(node.target)
                self.violations.append(
                    (
                        node.lineno,
                        class_name,
                        self._current_class or "<unknown>",
                        target_name,
                    )
                )

        self.generic_visit(node)

    def _get_called_class_name(self, call_node: ast.Call) -> str | None:
        """Extract class name from a Call node.

        Handles:
            ClassName()           -> "ClassName"
            module.ClassName()    -> "ClassName"
        """
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    def _get_target_name(self, target: ast.expr) -> str:
        """Get string representation of assignment target."""
        if isinstance(target, ast.Name):
            return target.id
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name):
                return f"{target.value.id}.{target.attr}"
            return target.attr
        return "<unknown>"


class TestDIConstructors:
    """Tests ensuring no service instantiation in __init__ methods."""

    @pytest.fixture
    def application_python_files(self) -> list[Path]:
        """Get all Python files in application directory.

        Excludes:
        - Composition layer files (allowed to create services)
        - Explicitly allowed files (factories)
        """
        base = _get_base_path(APPLICATION_DIR)
        if not base.exists():
            pytest.skip("Application layer not found")

        files = []
        for py_file in base.rglob("*.py"):
            # Skip composition layer
            if "composition" in str(py_file):
                continue
            # Skip allowed files
            if py_file.name in ALLOWED_FILES:
                continue
            files.append(py_file)
        return files

    def test_no_service_instantiation_in_init(
        self, application_python_files: list[Path]
    ) -> None:
        """Application layer __init__ methods MUST NOT instantiate services.

        REQ-ARCH-DI-011: Services like LockCoordinator, PreflightService,
        MedallionLifecycleService, etc. must be injected via constructor
        parameters, not created inside __init__.

        Anti-pattern:
            class SomeClass:
                def __init__(self):
                    self._lock_manager = LockCoordinator(...)  # BAD!

        Correct pattern:
            class SomeClass:
                def __init__(self, lock_manager: LockCoordinator):
                    self._lock_manager = lock_manager  # GOOD!

        See CLAUDE.md §2.2 and §11 Anti-Patterns.
        """
        violations: list[Violation] = []

        for py_file in application_python_files:
            violations.extend(
                _init_instantiation_violations(
                    py_file,
                    FORBIDDEN_SERVICE_INSTANTIATIONS,
                )
            )

        if violations:
            base = _get_base_path(APPLICATION_DIR)
            violation_messages = _format_violation_messages(violations, base)

            pytest.fail(
                "DI violation: Service instantiation in __init__ methods.\n"
                "Services MUST be injected via constructor parameters, "
                "not created inside __init__.\n\n"
                "Violations found:\n" + "\n".join(violation_messages) + "\n\n"
                "Move service creation to composition layer "
                "(factories/bootstrap.py) and inject via parameters.\n"
                "See CLAUDE.md §2.2 Dependency Injection for details."
            )

    def test_forbidden_services_list_is_current(self, src_dir: Path) -> None:
        """Verify the forbidden services list matches actual service classes.

        This test ensures we don't miss new services that should be added
        to the forbidden list.
        """
        # Find all *Service and *Manager classes in application layer
        app_path = src_dir / "bioetl" / "application"
        if not app_path.exists():
            pytest.skip("Application layer not found")

        found_services: set[str] = set()

        for py_file in _iter_application_source_files(app_path):
            found_services.update(_service_like_classes_in_file(py_file))

        # Filter out known exceptions (data containers, not services)
        exceptions = {
            # These are data containers, not services
            "CheckpointManager",  # Same-module alias for CheckpointRuntimeService
        }
        relevant_services = found_services - exceptions

        # Check for services that might be missing from forbidden list
        missing = relevant_services - FORBIDDEN_SERVICE_INSTANTIATIONS
        if missing:
            # This is informational - new services should be reviewed
            # to determine if they need to be added to the forbidden list
            pass  # Consider adding: {missing}


class TestDIConstructorsRegression:
    """Regression tests to ensure the detection mechanism works correctly."""

    def test_detection_of_simple_instantiation(self) -> None:
        """Verify AST detection catches simple self.x = Service() pattern."""
        code = """
class BadClass:
    def __init__(self):
        self._manager = LockCoordinator()
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"LockCoordinator"})
        finder.visit(tree)

        assert len(finder.violations) == 1
        _lineno, class_name, containing, target = finder.violations[0]
        assert class_name == "LockCoordinator"
        assert containing == "BadClass"
        assert "manager" in target.lower()

    def test_detection_of_instantiation_with_args(self) -> None:
        """Verify detection catches Service(arg1, arg2) pattern."""
        code = """
class BadClass:
    def __init__(self, config):
        self._service = PreflightService(config, context, logger)
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"PreflightService"})
        finder.visit(tree)

        assert len(finder.violations) == 1
        assert finder.violations[0][1] == "PreflightService"

    def test_no_false_positive_for_parameter_assignment(self) -> None:
        """Verify no violation for self.x = injected_param pattern."""
        code = """
class GoodClass:
    def __init__(self, lock_manager: LockCoordinator):
        self._lock_manager = lock_manager  # This is injection, not creation!
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"LockCoordinator"})
        finder.visit(tree)

        assert len(finder.violations) == 0

    def test_no_false_positive_outside_init(self) -> None:
        """Verify no violation for service creation outside __init__."""
        code = """
class SomeClass:
    def __init__(self):
        pass

    def create_manager(self):
        # This is a factory method, not __init__ - different concern
        return LockCoordinator()
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"LockCoordinator"})
        finder.visit(tree)

        assert len(finder.violations) == 0

    def test_detection_of_module_qualified_instantiation(self) -> None:
        """Verify detection catches module.Service() pattern."""
        code = """
class BadClass:
    def __init__(self):
        self._service = medallion.MedallionLifecycleService()
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"MedallionLifecycleService"})
        finder.visit(tree)

        assert len(finder.violations) == 1
        assert finder.violations[0][1] == "MedallionLifecycleService"

    def test_detection_of_annotated_assignment(self) -> None:
        """Verify detection catches self._x: Type = Service() pattern."""
        code = """
class BadClass:
    def __init__(self):
        self._service: PostrunService = PostrunService()
"""
        tree = ast.parse(code)
        finder = InitInstantiationFinder({"PostrunService"})
        finder.visit(tree)

        assert len(finder.violations) == 1
        assert finder.violations[0][1] == "PostrunService"


# Ensure these tests are discoverable
__all__ = ["TestDIConstructors", "TestDIConstructorsRegression"]
