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
"""unit-fast must not absorb scripts/repo_backed surfaces (T-TEST-003 / #6774)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = _REPO / "configs/quality/test_matrix.yaml"


@pytest.mark.architecture
def test_unit_fast_lane_excludes_scripts_repo_backed_and_subprocess() -> None:
    """unit-fast marker/path rules must keep pure unit lane free of tooling noise."""
    payload = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    lane = payload["test_lanes"]["lanes"]["unit-fast"]
    marker = str(lane["marker_expression"])
    args = [str(a) for a in lane["pytest_args"]]

    assert "not repo_backed" in marker
    assert "not subprocess_backed" in marker
    assert "tests/unit/scripts" in " ".join(args) or any(
        a.endswith("tests/unit/scripts")
        or a == "tests/unit/scripts"
        or a.startswith("--ignore=tests/unit/scripts")
        for a in args
    )
    assert any(
        "--ignore=tests/unit/scripts" == a
        or a.startswith("--ignore=tests/unit/scripts")
        for a in args
    )
    assert any("--ignore=tests/unit/repo_backed" == a for a in args)


@pytest.mark.architecture
def test_unit_scripts_and_repo_backed_lanes_exist() -> None:
    """FS/tooling suites must have dedicated named lanes (not dropped)."""
    payload = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    lanes = payload["test_lanes"]["lanes"]
    assert "unit-scripts-tooling" in lanes
    assert "repo-backed-unit" in lanes
    assert lanes["unit-scripts-tooling"]["paths"] == ["tests/unit/scripts/"]
    assert lanes["repo-backed-unit"]["paths"] == ["tests/unit/repo_backed/"]
