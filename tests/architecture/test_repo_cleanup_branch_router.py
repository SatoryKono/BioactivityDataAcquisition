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
import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_repo_router_exposes_cleanup_branch_candidates_command() -> None:
    root = Path(__file__).resolve().parents[2]
    router = (root / "scripts" / "engineering" / "repo" / "__main__.py").read_text(
        encoding="utf-8"
    )

    assert '"cleanup-branch-candidates": "cleanup_branch_candidates.sh"' in router
    assert (
        "cleanup-branch-candidates  Preview or apply curated local branch cleanup plan"
        in router
    )
    assert "generate-branch-cleanup-inventory" in router
    assert "apply-branch-cleanup" in router


def test_repo_readme_prefers_canonical_cleanup_branch_candidates_route() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "scripts" / "engineering" / "repo" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "python -m scripts.engineering.repo <command> [args...]" in readme
    assert "`cleanup-branch-candidates`" in readme
    assert "bash scripts/engineering/repo/cleanup_branch_candidates.sh" in readme
