"""Architecture tests: Factory Helper Restrictions.

This test ensures that certain domain modules do not contain factory helpers (create_* functions),
enforcing the 'factories only in composition' rule for specific services.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture


def test_no_factory_helpers_in_specific_domain_services(src_dir: Path) -> None:
    """Targeted check for forbidden factory helpers in domain services.

    Ensures that:
    - aggregation_validator.py does not have create_aggregation_validator()
    - cross_validation_validator.py does not have create_cross_validation_validator()
    - preflight_governance.py does not have create_preflight_governance_service()
    """
    forbidden_factories = {
        "bioetl/domain/services/aggregation_validator.py": [
            "create_aggregation_validator"
        ],
        "bioetl/domain/services/cross_validation_validator.py": [
            "create_cross_validation_validator"
        ],
        "bioetl/domain/services/preflight_governance.py": [
            "create_preflight_governance_service"
        ],
    }

    violations = []

    for rel_path, factory_names in forbidden_factories.items():
        file_path = src_dir / rel_path.replace("/", "\\")
        if not file_path.exists():
            continue

        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in factory_names:
                violations.append(
                    f"{rel_path} contains forbidden factory function: {node.name}"
                )

    assert not violations, "\n".join(violations)
