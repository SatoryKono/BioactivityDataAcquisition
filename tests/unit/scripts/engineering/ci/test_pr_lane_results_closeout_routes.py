"""Keep explicit closeout documentation routed without admitting unknown docs."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
RUNBOOK = "docs/05-operations/runbooks/ai-closeout-wrapper.md"


def test_closeout_runbook_selects_verifier_and_documentation_contracts() -> None:
    report = build_shadow_compare([RUNBOOK], repo_root=ROOT)
    assert not report["covers_full_suite"]
    assert {
        "tests/unit/scripts/repo/test_closeout_runtime.py",
        "tests/unit/scripts/repo/test_closeout_git_safety.py",
        "tests/unit/scripts/engineering/qa/test_proof_or_stop.py",
        "tests/architecture/test_proof_or_stop_contract.py",
        "tests/architecture/test_documentation_cleanup_inventory.py",
    } <= set(report["selected"])


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "src/memory/proof.py",
            {
                "tests/unit/scripts/engineering/qa/test_proof_or_stop.py",
                "tests/unit/scripts/repo/test_closeout_git_safety.py",
                "tests/unit/scripts/repo/test_closeout_runtime.py",
            },
        ),
        (
            "docs/00-project/ai/agents/README.md",
            {
                "tests/architecture/test_ai_runtime_governance_links.py",
                "tests/architecture/test_runtime_agent_docs_drift.py",
                "tests/architecture/test_documentation_cleanup_inventory.py",
            },
        ),
    ],
)
def test_closeout_core_and_reference_select_owning_contracts(
    path: str, expected: set[str]
) -> None:
    report = build_shadow_compare([path], repo_root=ROOT)
    assert not report["covers_full_suite"]
    assert expected <= set(report["selected"])


@pytest.mark.parametrize(
    "path",
    [
        "docs/05-operations/runbooks/ai-closeout-unreviewed.md",
        "docs/05-operations/runbooks/ai-closeout-wrapper.md.bak",
        "docs/00-project/ai/agents/README.md.bak",
        "src/memory/proof_unreviewed.py",
    ],
)
def test_nearby_unknown_closeout_docs_still_fail_closed(path: str) -> None:
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([path], repo_root=ROOT)


def test_known_closeout_route_does_not_hide_an_unknown_path() -> None:
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            [RUNBOOK, "docs/05-operations/runbooks/ai-closeout-unreviewed.md"],
            repo_root=ROOT,
        )
