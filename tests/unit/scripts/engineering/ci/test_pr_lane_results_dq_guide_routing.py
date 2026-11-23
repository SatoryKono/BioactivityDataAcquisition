"""Focused routing coverage for the DQ configuration guide."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    build_shadow_compare,
)

pytestmark = pytest.mark.unit


def test_dq_guide_routes_to_configuration_tests() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    changed = "docs/03-guides/dq-configuration.md"
    owners = {
        "tests/architecture/test_documentation_residual_keyword_guards.py",
        "tests/architecture/test_tech_debt_issue_6038_governance_taxonomy.py",
        "tests/unit/infrastructure/config/test_dq_config_loader.py",
        "tests/unit/infrastructure/config/test_pipeline_config_loader_extended.py",
    }
    assert owners <= set(affected_pytest_targets([changed], repo_root=repo_root))
    assert owners <= set(
        build_shadow_compare([changed], repo_root=repo_root)["selected"]
    )
