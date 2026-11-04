"""Composition protocol inventory routing for the PR lane selector."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import affected_pytest_targets

pytestmark = pytest.mark.unit


def test_affected_targets_map_composition_protocol_inventory() -> None:
    """Protocol inventory edits select their completeness and drift tests."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["configs/quality/composition_protocol_inventory.yaml"],
        repo_root=repo_root,
    ) == ["tests/architecture/test_composition_protocol_inventory.py"]
