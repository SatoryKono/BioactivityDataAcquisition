import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src"
DOMAIN_ROOT = SOURCE_ROOT / "bioetl" / "domain"
APPLICATION_ROOT = SOURCE_ROOT / "bioetl" / "application"
INFRASTRUCTURE_ROOT = SOURCE_ROOT / "bioetl" / "infrastructure"


@dataclass(frozen=True)
class ImportReference:
    module: str
    lineno: int


def _module_from_path(path: Path) -> tuple[str, bool]:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


def _resolve_module(
    current_module: str, *, module: str, level: int, is_package: bool
) -> str:
    if level == 0:
        return module

    current_parts = current_module.split(".")
    base_parts = current_parts if is_package else current_parts[:-1]
    if level > len(base_parts):
        return module
    prefix = base_parts[:-level]
    if module:
        prefix.extend(module.split("."))
    return ".".join(prefix)


def _collect_imports(path: Path) -> list[ImportReference]:
    code = path.read_text(encoding="utf-8")
    tree = ast.parse(code)
    current_module, is_package = _module_from_path(path)
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        imports.extend(
            _imports_from_node(
                node, current_module=current_module, is_package=is_package
            )
        )

    return imports


def _imports_from_node(
    node: ast.AST, *, current_module: str, is_package: bool
) -> list[ImportReference]:
    if isinstance(node, ast.Import):
        return [ImportReference(alias.name, node.lineno) for alias in node.names]

    if isinstance(node, ast.ImportFrom):
        return _imports_from_import_from(
            node, current_module=current_module, is_package=is_package
        )

    return []


def _imports_from_import_from(
    node: ast.ImportFrom, *, current_module: str, is_package: bool
) -> list[ImportReference]:
    module = _resolve_module(
        current_module,
        module=node.module or "",
        level=node.level,
        is_package=is_package,
    )

    references: list[ImportReference] = []
    if module:
        references.append(ImportReference(module, node.lineno))

    for alias in node.names:
        target = module
        if target:
            target = f"{target}.{alias.name}" if alias.name else target
        else:
            target = alias.name
        if target:
            references.append(ImportReference(target, node.lineno))

    return references


def _layer_segment(module: str, layer: str) -> str | None:
    parts = module.split(".")
    try:
        idx = parts.index(layer)
    except ValueError:
        return None
    if idx + 1 < len(parts):
        return parts[idx + 1]
    return None


def _format_violation(path: Path, lineno: int, message: str) -> str:
    return f"{path.as_posix()}:{lineno}: {message}"


def _assert_no_violations(violations: list[str]) -> None:
    if violations:
        formatted = "\n".join(sorted(set(violations)))
        pytest.fail(f"Forbidden imports detected:\n{formatted}")


def test_domain_has_no_outer_dependencies() -> None:
    violations: list[str] = []
    for file_path in sorted(DOMAIN_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("bioetl.infrastructure"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "domain must not depend on infrastructure "
                        f"(imported {reference.module})",
                    )
                )
            if reference.module.startswith("bioetl.application"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "domain must not depend on application "
                        f"(imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_application_avoids_infrastructure_implementations() -> None:
    violations: list[str] = []
    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            if "impl" in reference.module.split("."):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "application must not import infrastructure implementations "
                        f"(imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_infrastructure_does_not_depend_on_application() -> None:
    violations: list[str] = []
    for file_path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("bioetl.application"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "infrastructure must not import application layer "
                        f"(imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_infrastructure_impls_are_not_cross_used() -> None:
    violations: list[str] = []
    for file_path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        current_module, _ = _module_from_path(file_path)
        current_segment = _layer_segment(current_module, "infrastructure")

        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue
            if "impl" not in reference.module.split("."):
                continue

            target_segment = _layer_segment(reference.module, "infrastructure")
            if target_segment and target_segment != current_segment:
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "infrastructure modules must not depend on implementations "
                        f"from other modules (imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def _is_inside_type_checking(node: ast.AST, tree: ast.Module) -> bool:
    """Check if a node is inside an `if TYPE_CHECKING:` block."""

    class TypeCheckingVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.type_checking_ranges: list[tuple[int, int]] = []

        def visit_If(self, node: ast.If) -> None:
            # Check if this is `if TYPE_CHECKING:`
            is_type_checking = False
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                is_type_checking = True
            elif isinstance(node.test, ast.Attribute):
                if node.test.attr == "TYPE_CHECKING":
                    is_type_checking = True

            if is_type_checking:
                # Get the range of lines covered by this block
                start_line = node.lineno
                end_line = start_line
                for child in ast.walk(node):
                    if hasattr(child, "lineno"):
                        end_line = max(end_line, child.lineno)
                self.type_checking_ranges.append((start_line, end_line))

            self.generic_visit(node)

    visitor = TypeCheckingVisitor()
    visitor.visit(tree)

    if not hasattr(node, "lineno"):
        return False

    for start, end in visitor.type_checking_ranges:
        if start <= node.lineno <= end:
            return True
    return False


def _is_module_level_import(node: ast.AST, tree: ast.Module) -> bool:
    """Check if an import is at module level (not inside function/class/if)."""
    # Module level means it's a direct child of the module body
    return node in tree.body


def _collect_module_level_imports(path: Path) -> list[ImportReference]:
    """Collect only module-level imports, excluding TYPE_CHECKING blocks."""
    code = path.read_text(encoding="utf-8")
    tree = ast.parse(code)
    current_module, is_package = _module_from_path(path)
    imports: list[ImportReference] = []

    for node in tree.body:
        # Skip if inside TYPE_CHECKING block
        if _is_inside_type_checking(node, tree):
            continue

        imports.extend(
            _imports_from_node(
                node, current_module=current_module, is_package=is_package
            )
        )

    return imports


# Forbidden domain.schemas imports for infrastructure layer
FORBIDDEN_DOMAIN_SCHEMA_PATTERNS = [
    "bioetl.domain.schemas.chembl.raw_models",
    "bioetl.domain.schemas.pipeline_contracts",
]

# Allowed domain imports for infrastructure layer
ALLOWED_DOMAIN_PATTERNS = [
    "bioetl.domain.ports",
    "bioetl.domain.configs",
    "bioetl.domain.errors",
    "bioetl.domain.observability",
    "bioetl.domain.clients.base.contracts",
    "bioetl.domain.clients.contracts",
    "bioetl.domain.transform.contracts",
    "bioetl.domain.transform.merge",
    "bioetl.domain.transform.normalizers",
    "bioetl.domain.transform.serializers",
    "bioetl.domain.validation",
    "bioetl.domain.pipelines.contracts",
    "bioetl.domain.provider_registry",
    "bioetl.domain.providers",
    "bioetl.domain.models",
]


def test_infrastructure_does_not_import_domain_schemas_at_module_level() -> None:
    """Verify infrastructure layer doesn't directly import domain schemas at module level.

    Infrastructure may use domain schemas via:
    - TYPE_CHECKING blocks (for type hints only)
    - Lazy imports inside functions (for backward compatibility with deprecation warnings)

    But MUST NOT have module-level imports from:
    - domain.schemas.chembl.raw_models
    - domain.schemas.pipeline_contracts
    """
    violations: list[str] = []

    for file_path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        for reference in _collect_module_level_imports(file_path):
            for forbidden_pattern in FORBIDDEN_DOMAIN_SCHEMA_PATTERNS:
                if reference.module.startswith(forbidden_pattern):
                    violations.append(
                        _format_violation(
                            file_path,
                            reference.lineno,
                            f"infrastructure must not import {forbidden_pattern} at module level "
                            "(use TYPE_CHECKING for type hints or lazy import for backward compat). "
                            f"Found: {reference.module}",
                        )
                    )

    _assert_no_violations(violations)
