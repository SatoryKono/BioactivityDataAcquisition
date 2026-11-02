"""Test root/path seams in five scripts."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_root_path_seams() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Test five root/path seams from external cwd
        scripts = {
            "architecture_debt_reduction": "from scripts.engineering.quality.architecture_debt_reduction import build_architecture_debt_execution_plan; print(type(build_architecture_debt_execution_plan))",
            "architecture_debt_task_generation": "from scripts.engineering.quality.architecture_debt_task_generation import generate_architecture_debt_tasks_payload; print(type(generate_architecture_debt_tasks_payload))",
            "architecture_quality_scorecard": "from scripts.engineering.quality.architecture_quality_scorecard import build_architecture_quality_scorecard; print(type(build_architecture_quality_scorecard))",
            "debt_scorecard": "from scripts.engineering.quality.debt_scorecard import evaluate_debt_scorecard; print(type(evaluate_debt_scorecard))",
            "exemptions_registry_paths": "from scripts.engineering.quality.exemptions_registry_paths import resolve_registry_path; print(type(resolve_registry_path))",
        }
        for name, code in scripts.items():
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    f"import sys; sys.path.insert(0, {str(repo_root)!r}); sys.path.insert(0, {str(repo_root / 'src')!r}); "
                    + code,
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"{name} failed: {result.stderr}"
