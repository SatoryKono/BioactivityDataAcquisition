"""Focused routing for composite fixtures and protocol-inventory config."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    build_shadow_compare,
)

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_composite_fixtures() -> None:
    """Composite fixture YAML selects the integration schema contract suite."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["tests/fixtures/composite/many_to_one_enricher.yaml"],
        repo_root=repo_root,
    )
    assert (
        "tests/integration/composite/test_composite_config_schema_contract.py"
        in report["selected"]
    )


def test_affected_targets_map_composition_protocol_inventory() -> None:
    """Protocol inventory edits select their completeness and drift tests."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["configs/quality/composition_protocol_inventory.yaml"],
        repo_root=repo_root,
    ) == ["tests/architecture/test_composition_protocol_inventory.py"]
