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
"""repo_backed marker must stay inside the dedicated unit subtree (TEST-SYS-05 / #7027)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_UNIT = _REPO / "tests" / "unit"
_REPO_BACKED = _UNIT / "repo_backed"
_MARKER_RE = re.compile(r"pytest\.mark\.repo_backed|@pytest\.mark\.repo_backed")


@pytest.mark.architecture
def test_repo_backed_marker_only_under_unit_repo_backed_subtree() -> None:
    offenders: list[str] = []
    for path in _UNIT.rglob("*.py"):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not _MARKER_RE.search(text):
            continue
        try:
            path.relative_to(_REPO_BACKED)
        except ValueError:
            offenders.append(path.relative_to(_REPO).as_posix())
    assert not offenders, (
        "pytest.mark.repo_backed is only allowed under tests/unit/repo_backed/:\n"
        + "\n".join(offenders)
    )


@pytest.mark.architecture
def test_unit_parallel_safe_excludes_repo_backed_marker_expression() -> None:
    import yaml

    matrix = yaml.safe_load(
        (_REPO / "configs/quality/test_matrix.yaml").read_text(encoding="utf-8")
    )
    suite = matrix["test_lanes"]["lanes"]["unit-parallel-safe"]
    assert isinstance(suite, dict), "unit-parallel-safe suite must exist"
    marker = str(suite.get("marker_expression") or "")
    assert "not repo_backed" in marker
    runner_options = [str(x) for x in (suite.get("runner_options") or [])]
    assert "S7-crosscutting-architecture-a" not in runner_options
    assert "S7-crosscutting-architecture-guardrails" not in runner_options
    # Membership rules documented after TEST-SYS-05.
    description = str(suite.get("description") or "")
    assert "repo_backed" in description
    assert "forbid_global_xdist" in description or "shard-scoped" in description
