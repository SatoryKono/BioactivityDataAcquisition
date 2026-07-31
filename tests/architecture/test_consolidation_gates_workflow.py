"""Architecture contracts for the consolidation quality workflow."""

from pathlib import Path

import pytest


CONSOLIDATION_WORKFLOW = Path(".github/workflows/consolidation-gates.yml")
pytestmark = pytest.mark.architecture


def test_consolidation_mypy_matches_canonical_product_scope() -> None:
    """The consolidation lane must not extend strict mypy to untyped tests."""
    workflow = CONSOLIDATION_WORKFLOW.read_text(encoding="utf-8")

    assert "--config-file pyproject.toml" in workflow
    assert "--strict" in workflow
    assert "--no-incremental" in workflow
    assert "src/bioetl" in workflow
    assert "mypy src tests" not in workflow
