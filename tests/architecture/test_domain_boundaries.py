"""Architectural tests for domain layer boundaries.

These tests verify that the domain layer remains pure and free from:
- Infrastructure dependencies (pandas, pandera, yaml, requests, etc.)
- Other layer dependencies (application, infrastructure, interfaces)
- Poor documentation practices (missing docstrings, type hints)

The domain layer should only contain:
- Pure business logic
- Domain entities and value objects
- Contracts (ABCs, Protocols)
- Domain services
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src"
DOMAIN_ROOT = SOURCE_ROOT / "bioetl" / "domain"

# Forbidden external packages that domain should never use directly
FORBIDDEN_EXTERNAL_PACKAGES = frozenset(
    {
        "pandas",
        "pandera",
        "yaml",
        "requests",
        "httpx",
        "aiohttp",
        "sqlalchemy",
        "boto3",
        "botocore",
    }
)

# Forbidden internal layer imports
FORBIDDEN_LAYER_PREFIXES = (
    "bioetl.infrastructure",
    "bioetl.application",
    "bioetl.interfaces",
)

# Classes/functions that are considered internal (not public API)
INTERNAL_NAME_PREFIXES = ("_",)

# Classes exempt from docstring requirements (e.g., simple dataclasses)
DOCSTRING_EXEMPT_CLASSES: frozenset[str] = frozenset()

# Classes exempt from type hints requirements
TYPE_HINTS_EXEMPT_CLASSES: frozenset[str] = frozenset()


# =============================================================================
# AST Helpers
# =============================================================================


@dataclass(frozen=True)
class ImportViolation:
    """Represents a forbidden import violation."""

    file_path: Path
    lineno: int
    module: str
    reason: str

    def __str__(self) -> str:
        return (
            f"{self.file_path.as_posix()}:{self.lineno}: {self.reason} ({self.module})"
        )


@dataclass(frozen=True)
class DocstringViolation:
    """Represents a missing docstring violation."""

    file_path: Path
    lineno: int
    class_name: str

    def __str__(self) -> str:
        return (
            f"{self.file_path.as_posix()}:{self.lineno}: "
            f"class '{self.class_name}' missing docstring"
        )


@dataclass(frozen=True)
class TypeHintViolation:
    """Represents a missing type hint violation."""

    file_path: Path
    lineno: int
    class_name: str
    method_name: str
    issue: str

    def __str__(self) -> str:
        return (
            f"{self.file_path.as_posix()}:{self.lineno}: "
            f"'{self.class_name}.{self.method_name}' {self.issue}"
        )


@dataclass
class TypeCheckingBlockFinder(ast.NodeVisitor):
    """Finds line ranges covered by TYPE_CHECKING blocks."""

    type_checking_ranges: list[tuple[int, int]] = field(default_factory=list)

    def visit_If(self, node: ast.If) -> None:
        is_type_checking = False

        # Check for `if TYPE_CHECKING:`
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            is_type_checking = True
        # Check for `if typing.TYPE_CHECKING:`
        elif isinstance(node.test, ast.Attribute) and node.test.attr == "TYPE_CHECKING":
            is_type_checking = True

        if is_type_checking:
            start_line = node.lineno
            end_line = start_line
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    end_line = max(end_line, child.lineno)
            self.type_checking_ranges.append((start_line, end_line))

        self.generic_visit(node)


def _is_inside_type_checking(lineno: int, tree: ast.Module) -> bool:
    """Check if a line number is inside a TYPE_CHECKING block."""
    finder = TypeCheckingBlockFinder()
    finder.visit(tree)

    for start, end in finder.type_checking_ranges:
        if start <= lineno <= end:
            return True
    return False


def _iter_python_files(root: Path) -> Iterator[Path]:
    """Iterate over all Python files in a directory, excluding __pycache__."""
    for path in root.rglob("*.py"):
        if "__pycache__" not in path.parts:
            yield path


def _is_public_class(node: ast.ClassDef) -> bool:
    """Check if a class is part of the public API."""
    return not node.name.startswith(INTERNAL_NAME_PREFIXES)


def _is_public_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a method is part of the public API."""
    # Skip private methods and dunder methods (except __init__)
    if node.name.startswith("_") and node.name != "__init__":
        return False
    return True


def _has_docstring(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a node has a docstring."""
    if not node.body:
        return False

    first_stmt = node.body[0]
    if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant):
        return isinstance(first_stmt.value.value, str)
    return False


def _check_method_type_hints(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Check if a method has proper type hints. Returns list of issues."""
    issues: list[str] = []

    # Check return annotation (except for __init__)
    if method.name != "__init__" and method.returns is None:
        issues.append("missing return type annotation")

    # Check argument annotations
    args = method.args
    all_args = args.args + args.posonlyargs + args.kwonlyargs

    for arg in all_args:
        # Skip 'self' and 'cls'
        if arg.arg in ("self", "cls"):
            continue
        if arg.annotation is None:
            issues.append(f"parameter '{arg.arg}' missing type annotation")

    # Check *args and **kwargs
    if args.vararg and args.vararg.annotation is None:
        issues.append(f"parameter '*{args.vararg.arg}' missing type annotation")
    if args.kwarg and args.kwarg.annotation is None:
        issues.append(f"parameter '**{args.kwarg.arg}' missing type annotation")

    return issues


# =============================================================================
# Import Analysis
# =============================================================================


def _extract_import_module(node: ast.Import | ast.ImportFrom) -> Iterable[str]:
    """Extract module names from an import statement."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
    elif isinstance(node, ast.ImportFrom) and node.module:
        yield node.module


def _check_forbidden_imports(
    file_path: Path, tree: ast.Module
) -> list[ImportViolation]:
    """Check for forbidden imports in a file."""
    violations: list[ImportViolation] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        # Skip TYPE_CHECKING imports for pandas (allowed for type hints)
        if _is_inside_type_checking(node.lineno, tree):
            continue

        for module in _extract_import_module(node):
            # Check forbidden external packages
            for forbidden in FORBIDDEN_EXTERNAL_PACKAGES:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    violations.append(
                        ImportViolation(
                            file_path=file_path,
                            lineno=node.lineno,
                            module=module,
                            reason=f"forbidden external package '{forbidden}'",
                        )
                    )

            # Check forbidden layer imports
            for prefix in FORBIDDEN_LAYER_PREFIXES:
                if module.startswith(prefix):
                    layer = prefix.split(".")[-1]
                    violations.append(
                        ImportViolation(
                            file_path=file_path,
                            lineno=node.lineno,
                            module=module,
                            reason=f"domain must not depend on {layer} layer",
                        )
                    )

    return violations


# =============================================================================
# Docstring Analysis
# =============================================================================


def _check_class_docstrings(
    file_path: Path, tree: ast.Module
) -> list[DocstringViolation]:
    """Check that all public classes have docstrings."""
    violations: list[DocstringViolation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        if not _is_public_class(node):
            continue

        if node.name in DOCSTRING_EXEMPT_CLASSES:
            continue

        if not _has_docstring(node):
            violations.append(
                DocstringViolation(
                    file_path=file_path,
                    lineno=node.lineno,
                    class_name=node.name,
                )
            )

    return violations


# =============================================================================
# Type Hint Analysis
# =============================================================================


def _check_class_type_hints(
    file_path: Path, tree: ast.Module
) -> list[TypeHintViolation]:
    """Check that all public methods in public classes have type hints."""
    violations: list[TypeHintViolation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        if not _is_public_class(node):
            continue

        if node.name in TYPE_HINTS_EXEMPT_CLASSES:
            continue

        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if not _is_public_method(item):
                continue

            issues = _check_method_type_hints(item)
            for issue in issues:
                violations.append(
                    TypeHintViolation(
                        file_path=file_path,
                        lineno=item.lineno,
                        class_name=node.name,
                        method_name=item.name,
                        issue=issue,
                    )
                )

    return violations


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def domain_files() -> list[Path]:
    """Return all Python files in the domain layer."""
    return sorted(_iter_python_files(DOMAIN_ROOT))


@pytest.fixture(scope="module")
def domain_trees(domain_files: list[Path]) -> dict[Path, ast.Module]:
    """Parse all domain files into AST trees."""
    trees: dict[Path, ast.Module] = {}
    for file_path in domain_files:
        try:
            code = file_path.read_text(encoding="utf-8")
            trees[file_path] = ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {file_path}: {e}")
    return trees


# =============================================================================
# Tests
# =============================================================================


class TestDomainForbiddenImports:
    """Tests for forbidden imports in the domain layer."""

    def test_domain_has_no_forbidden_external_packages(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify domain layer doesn't import forbidden external packages.

        Forbidden packages include:
        - pandas (except in TYPE_CHECKING blocks)
        - pandera
        - yaml
        - requests, httpx, aiohttp
        - sqlalchemy
        - boto3, botocore
        """
        all_violations: list[ImportViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_forbidden_imports(file_path, tree)
            # Filter to only external package violations
            external_violations = [
                v for v in violations if "forbidden external package" in v.reason
            ]
            all_violations.extend(external_violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(
                f"Domain layer must not import external I/O packages:\n{formatted}"
            )

    def test_domain_has_no_infrastructure_imports(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify domain layer doesn't import from infrastructure layer."""
        all_violations: list[ImportViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_forbidden_imports(file_path, tree)
            infra_violations = [
                v for v in violations if "infrastructure layer" in v.reason
            ]
            all_violations.extend(infra_violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(f"Domain layer must not depend on infrastructure:\n{formatted}")

    def test_domain_has_no_application_imports(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify domain layer doesn't import from application layer."""
        all_violations: list[ImportViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_forbidden_imports(file_path, tree)
            app_violations = [v for v in violations if "application layer" in v.reason]
            all_violations.extend(app_violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(f"Domain layer must not depend on application:\n{formatted}")

    def test_domain_has_no_interfaces_imports(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify domain layer doesn't import from interfaces layer."""
        all_violations: list[ImportViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_forbidden_imports(file_path, tree)
            iface_violations = [v for v in violations if "interfaces layer" in v.reason]
            all_violations.extend(iface_violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(f"Domain layer must not depend on interfaces:\n{formatted}")

    def test_domain_has_no_dynamic_infrastructure_imports(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify domain doesn't use importlib to import infrastructure.

        Dynamic imports via importlib.import_module() can bypass static
        analysis and violate layer boundaries. Domain should never
        dynamically import from infrastructure, application, or interfaces.
        """
        violations: list[str] = []

        for file_path in domain_files:
            code = file_path.read_text(encoding="utf-8")

            # Check for importlib.import_module calls with forbidden layer references
            if "importlib.import_module" in code:
                for forbidden_layer in ("infrastructure", "application", "interfaces"):
                    if forbidden_layer in code:
                        violations.append(
                            f"{file_path.as_posix()}: dynamic import of "
                            f"{forbidden_layer} via importlib.import_module"
                        )
                        break

        if violations:
            pytest.fail(
                "Domain must not dynamically import other layers:\n"
                + "\n".join(violations)
            )


class TestDomainDocumentation:
    """Tests for documentation requirements in the domain layer."""

    def test_public_classes_have_docstrings(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify all public classes in domain have docstrings.

        Public classes are those whose names don't start with underscore.
        A docstring is a string literal as the first statement in the class body.
        """
        all_violations: list[DocstringViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_class_docstrings(file_path, tree)
            all_violations.extend(violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(f"Public classes in domain must have docstrings:\n{formatted}")


class TestDomainTypeHints:
    """Tests for type hint requirements in the domain layer."""

    def test_public_methods_have_type_hints(
        self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
    ) -> None:
        """Verify all public methods in public classes have type hints.

        This checks:
        - Return type annotations (except for __init__)
        - Parameter type annotations (except self/cls)
        - *args and **kwargs annotations
        """
        all_violations: list[TypeHintViolation] = []

        for file_path in domain_files:
            tree = domain_trees[file_path]
            violations = _check_class_type_hints(file_path, tree)
            all_violations.extend(violations)

        if all_violations:
            formatted = "\n".join(str(v) for v in sorted(all_violations, key=str))
            pytest.fail(f"Public methods in domain must have type hints:\n{formatted}")


class TestDomainStructure:
    """Tests for domain layer structure and organization."""

    def test_domain_directory_exists(self) -> None:
        """Verify domain directory exists."""
        assert DOMAIN_ROOT.exists(), f"Domain root not found: {DOMAIN_ROOT}"
        assert DOMAIN_ROOT.is_dir(), f"Domain root is not a directory: {DOMAIN_ROOT}"

    def test_domain_has_init_file(self) -> None:
        """Verify domain has __init__.py."""
        init_file = DOMAIN_ROOT / "__init__.py"
        assert init_file.exists(), f"Domain __init__.py not found: {init_file}"

    def test_domain_submodules_have_init_files(self, domain_files: list[Path]) -> None:
        """Verify all domain subdirectories have __init__.py files."""
        subdirs: set[Path] = set()

        for file_path in domain_files:
            # Get all parent directories up to domain root
            current = file_path.parent
            while current != DOMAIN_ROOT and current.is_relative_to(DOMAIN_ROOT):
                subdirs.add(current)
                current = current.parent

        missing_inits: list[str] = []
        for subdir in sorted(subdirs):
            init_file = subdir / "__init__.py"
            if not init_file.exists():
                missing_inits.append(subdir.relative_to(DOMAIN_ROOT).as_posix())

        if missing_inits:
            pytest.fail(
                "Domain subdirectories missing __init__.py:\n"
                + "\n".join(f"  - {path}" for path in missing_inits)
            )


# =============================================================================
# Comprehensive Summary Test
# =============================================================================


def test_domain_boundaries_summary(
    domain_files: list[Path], domain_trees: dict[Path, ast.Module]
) -> None:
    """Comprehensive test that summarizes all domain boundary violations.

    This test collects all violations from import checks, docstring checks,
    and type hint checks, then reports them together for a complete picture.
    """
    import_violations: list[ImportViolation] = []
    docstring_violations: list[DocstringViolation] = []
    type_hint_violations: list[TypeHintViolation] = []

    for file_path in domain_files:
        tree = domain_trees[file_path]
        import_violations.extend(_check_forbidden_imports(file_path, tree))
        docstring_violations.extend(_check_class_docstrings(file_path, tree))
        type_hint_violations.extend(_check_class_type_hints(file_path, tree))

    # Build summary report
    sections: list[str] = []

    if import_violations:
        sections.append(
            "IMPORT VIOLATIONS:\n"
            + "\n".join(f"  {v}" for v in sorted(import_violations, key=str))
        )

    if docstring_violations:
        sections.append(
            "DOCSTRING VIOLATIONS:\n"
            + "\n".join(f"  {v}" for v in sorted(docstring_violations, key=str))
        )

    if type_hint_violations:
        sections.append(
            "TYPE HINT VIOLATIONS:\n"
            + "\n".join(f"  {v}" for v in sorted(type_hint_violations, key=str))
        )

    if sections:
        total = (
            len(import_violations)
            + len(docstring_violations)
            + len(type_hint_violations)
        )
        summary = (
            f"Domain boundary violations found ({total} total):\n"
            f"  - {len(import_violations)} import violations\n"
            f"  - {len(docstring_violations)} docstring violations\n"
            f"  - {len(type_hint_violations)} type hint violations\n\n"
            + "\n\n".join(sections)
        )
        pytest.fail(summary)
