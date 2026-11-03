"""Focused shadow-compare routing for composite fixture YAML."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

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
