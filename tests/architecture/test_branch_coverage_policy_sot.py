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
"""Branch-coverage gate must have one SOT (T-TEST-001 / #6775)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.architecture
def test_branch_coverage_is_hard_merge_truth_not_advisory() -> None:
    """test_matrix must not list branch_coverage under advisory_telemetry."""
    matrix = yaml.safe_load(
        (_REPO / "configs/quality/test_matrix.yaml").read_text(encoding="utf-8")
    )
    authority = matrix["test_lanes"]["authority_model"]
    hard = set(authority["hard_merge_truth"])
    advisory = set(authority["advisory_telemetry"])

    assert "branch_coverage" in hard
    assert "branch_coverage" not in advisory
    assert "coverage-verify" in hard

    branch_policy = authority["branch_coverage_policy"]
    assert branch_policy["policy"] == "blocking"
    assert int(branch_policy["hard_gate_threshold_percent"]) == 85


@pytest.mark.architecture
def test_module_coverage_gates_branch_policy_matches_matrix() -> None:
    """module_coverage_gates and ci surface matrix must agree on 85% blocking."""
    gates = yaml.safe_load(
        (_REPO / "configs/quality/module_coverage_gates.yaml").read_text(
            encoding="utf-8"
        )
    )
    surface = yaml.safe_load(
        (_REPO / "configs/quality/ci_coverage_surface_matrix.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert gates["branch_coverage"]["policy"] == "blocking"
    assert int(gates["branch_coverage"]["hard_gate_threshold_percent"]) == 85
    assert int(surface["threshold_policy"]["hard_branch_coverage_threshold"]) == 85
    assert surface["threshold_policy"]["enforced_in_job"] == "coverage-verify"


@pytest.mark.architecture
def test_branch_policy_does_not_hide_partial_branches_globally() -> None:
    """Branch debt must be closed by execution, not a global partial regex."""
    pyproject = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))

    assert "partial_also" not in pyproject["tool"]["coverage"]["report"]
