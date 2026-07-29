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
"""Architecture test for TransformerDependencyContext whitelist.

Enforces that TransformerDependencyContext does not become a God Object
service locator. Only shared technical collaborators are allowed.
"""

import pytest

import ast
import inspect
from pathlib import Path

pytestmark = pytest.mark.architecture

ALLOWED_FIELDS = {
    "tracer",
    "metrics",
    "identity_service",
    "pii_hasher",
    "data_normalizer",
    "contract_policy",
    "structural_policy",
}


def test_transformer_dependency_context_whitelist() -> None:
    """Check that TransformerDependencyContext only contains whitelisted fields."""
    types_file = Path("src/bioetl/application/core/base_transformer/types.py")
    assert types_file.exists(), f"{types_file} not found"

    tree = inspect.cleandoc(types_file.read_text(encoding="utf-8"))
    parsed = ast.parse(tree)

    context_class = None
    for node in parsed.body:
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "TransformerDependencyContext"
        ):
            context_class = node
            break

    assert context_class is not None, "TransformerDependencyContext class not found"

    actual_fields = set()
    for stmt in context_class.body:
        if isinstance(stmt, ast.AnnAssign):
            actual_fields.add(stmt.target.id)

    unapproved_fields = actual_fields - ALLOWED_FIELDS
    assert not unapproved_fields, (
        f"Unapproved fields found in TransformerDependencyContext: {unapproved_fields}. "
        "This bundle is restricted to shared technical collaborators ONLY. "
        "Do NOT add provider-specific or scalar configs. Requires architect approval."
    )

    missing_fields = ALLOWED_FIELDS - actual_fields
    assert not missing_fields, (
        f"Missing required fields from TransformerDependencyContext: {missing_fields}"
    )
