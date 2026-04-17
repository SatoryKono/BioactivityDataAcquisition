"""Architecture checks for naming/package consistency pre-merge gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_consistency_gate_script_runs_clean_in_check_mode() -> None:
    """Repository baseline should satisfy consistency gate."""
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "qa" / "check_naming_package_consistency.py"
    assert script.exists(), "scripts/engineering/qa/check_naming_package_consistency.py must exist"

    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, (
        "Naming/package consistency gate should pass on baseline.\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


def test_tests_workflow_runs_naming_package_consistency_gate() -> None:
    """Pre-merge tests workflow must run the consistency gate."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Pre-merge naming/package consistency gate" in workflow
    assert "scripts/engineering/qa/check_naming_package_consistency.py --check" in workflow
