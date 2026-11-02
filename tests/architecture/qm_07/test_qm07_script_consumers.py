"""Test actual script consumers roles and outputs."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

@pytest.mark.architecture
def test_script_consumers_report_architecture_quality_scorecard() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Test report_architecture_quality_scorecard import without --help
        # Import check
        code = "from scripts.engineering.qa.report_architecture_quality_scorecard import __name__; print(__name__)"
        result = subprocess.run(
            [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(repo_root)!r}); sys.path.insert(0, {str(repo_root / 'src')!r}); " + code],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"import failed: {result.stderr}"
