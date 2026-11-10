"""Keep issue 12553 evidence routed without accepting unrelated audit paths."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
CONTRACT = "tests/unit/scripts/engineering/qa/test_runtime_acceptance_12553.py"


@pytest.mark.parametrize(
    "path",
    [
        "reports/audit-runs/12553-runtime-acceptance/evidence.zip",
        "reports/audit-runs/12553-runtime-acceptance/.gitattributes",
        "reports/audit-runs/12553-runtime-acceptance/qualified-files-config-final-events.json.gz",
        "scripts/engineering/qa/runtime_acceptance_12553.py",
        "scripts/engineering/qa/runtime_acceptance_12553_coverage.py",
        "tests/helpers/runtime_acceptance_12553.py",
    ],
)
def test_runtime_evidence_selects_owning_contract(path):
    report = build_shadow_compare([path], repo_root=ROOT)
    assert any(
        CONTRACT == target or CONTRACT.startswith(target.rstrip("/") + "/")
        for target in report["selected"]
    )
    assert not report["covers_full_suite"]


def test_runtime_workflow_selects_policy_guards():
    report = build_shadow_compare(
        [".github/workflows/runtime-acceptance-12553.yml"], repo_root=ROOT
    )
    assert (
        "tests/architecture/test_github_actions_runtime_policy.py" in report["selected"]
    )
    assert "tests/architecture/test_gha_disabled_map_10263.py" in report["selected"]
    assert CONTRACT in report["selected"]


def test_unrelated_audit_path_still_fails_closed():
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            ["reports/audit-runs/unrelated/evidence.zip"], repo_root=ROOT
        )
