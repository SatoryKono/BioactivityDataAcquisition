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


def test_consolidation_snapshot_lane_runs_executable_contract() -> None:
    """Snapshot artifacts must be validated by an executable test module."""
    workflow = CONSOLIDATION_WORKFLOW.read_text(encoding="utf-8")

    assert (
        "pytest "
        "tests/unit/infrastructure/schemas/"
        "test_composite_config_invariants_source_of_truth.py"
    ) in workflow
    assert "tests/snapshots" not in workflow
