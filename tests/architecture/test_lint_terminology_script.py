"""Architecture tests for terminology linter CLI contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_lint_terminology_supports_check_without_paths() -> None:
    """CLI must allow --check with no positional paths."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "qa" / "lint_terminology.py"

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


def test_lint_terminology_wrapper_delegates_to_canonical() -> None:
    """Legacy wrapper path must delegate to canonical implementation."""
    repo_root = Path(__file__).resolve().parents[2]
    wrapper_path = repo_root / "src" / "tools" / "scripts" / "lint_terminology.py"

    assert wrapper_path.exists(), "src/tools/scripts/lint_terminology.py must exist"
    content = wrapper_path.read_text(encoding="utf-8")
    assert "runpy.run_path" in content
    assert "qa" in content
    assert "lint_terminology.py" in content
