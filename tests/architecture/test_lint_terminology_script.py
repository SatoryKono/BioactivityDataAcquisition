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
"""Architecture tests for terminology linter CLI contract."""

from __future__ import annotations

import pytest

import subprocess
import sys
from pathlib import Path


pytestmark = pytest.mark.architecture


def test_lint_terminology_supports_check_without_paths() -> None:
    """CLI must allow --check with no positional paths."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "engineering" / "qa" / "lint_terminology.py"

    assert script_path.exists(), "scripts/engineering/qa/lint_terminology.py must exist"

    result = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    combined_output = f"{result.stdout}\n{result.stderr}".lower()
    assert "the following arguments are required: paths" not in combined_output
    assert (
        "terminology violation" in result.stdout.lower()
        or "no terminology violations found" in result.stdout.lower()
    ), "Expected lint output, got argument parser or unexpected response"
