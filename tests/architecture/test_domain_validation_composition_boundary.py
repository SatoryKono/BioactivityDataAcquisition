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
"""Architecture checks for the remediated composite validation seam."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

DOMAIN_FILE = Path("src/bioetl/domain/behavior/composite_validation_layer.py")
COMPOSITION_FACTORY_FILE = Path(
    "src/bioetl/composition/factories/dq/composite_validation.py"
)


def _load_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _get_method(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _find_constructor_calls(
    function_node: ast.FunctionDef,
    forbidden_names: set[str],
) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in forbidden_names:
                violations.append(f"{node.func.id}() at line {node.lineno}")
    return violations


def test_composite_validation_domain_module_has_no_factory_helper() -> None:
    """Composite validation assembly should not live in domain."""
    source = DOMAIN_FILE.read_text(encoding="utf-8")

    assert "def create_composite_validation_service" not in source, (
        "Domain module still exposes create_composite_validation_service(). "
        "Move assembly helpers to composition."
    )


def test_composite_validator_init_has_no_hardcoded_collaborators() -> None:
    """CompositeValidator.__init__ should not construct its own collaborators."""
    init_fn = _get_method(
        _load_tree(DOMAIN_FILE),
        "CompositeValidator",
        "__init__",
    )
    violations = _find_constructor_calls(
        init_fn,
        {
            "AggregationValidator",
            "CrossValidationValidator",
            "PreflightGovernor",
        },
    )

    assert not violations, (
        "CompositeValidator.__init__ still constructs dependencies:\n"
        + "\n".join(f"  - {violation}" for violation in violations)
    )


def test_validate_composite_has_no_method_level_governance_instantiation() -> None:
    """validate_composite() should pass governance data, not create a governor."""
    validate_fn = _get_method(
        _load_tree(DOMAIN_FILE),
        "CompositeValidator",
        "validate_composite",
    )
    violations = _find_constructor_calls(validate_fn, {"PreflightGovernor"})

    assert not violations, (
        "validate_composite() still instantiates PreflightGovernor:\n"
        + "\n".join(f"  - {violation}" for violation in violations)
    )


def test_composition_factory_exists_for_composite_validation_service() -> None:
    """Composition should own the convenience assembly seam."""
    source = COMPOSITION_FACTORY_FILE.read_text(encoding="utf-8")

    assert "def create_composite_validation_service" in source
