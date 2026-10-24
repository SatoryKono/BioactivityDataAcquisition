"""Cold imports from a source checkout and an unrelated working directory.

Both src and the checkout root are explicit: QM-07 wheel isolation is BLOCKED
by core imports from scripts, recorded in test_qm07_cold_imports.py.
"""

import json
from pathlib import Path
import subprocess
import sys


import pytest

@pytest.mark.architecture
def test_cold_imports(tmp_path: Path) -> None:
    modules = [
        "scripts.engineering.quality",
        "scripts.engineering.quality._baseline_validation",
        "scripts.engineering.quality._decomposition_burndown_policy",
        "scripts.engineering.quality._decomposition_owner_policy",
        "scripts.engineering.quality._decomposition_program_policy",
        "scripts.engineering.quality._decomposition_validation",
        "scripts.engineering.quality._governance_validation",
        "scripts.engineering.quality._grace_windows_validation",
        "scripts.engineering.quality._primitives",
        "scripts.engineering.quality._quarterly_targets_validation",
        "scripts.engineering.quality.architecture_debt_artifact_tasks",
        "scripts.engineering.quality.architecture_debt_reduction",
        "scripts.engineering.quality.architecture_debt_task_generation",
        "scripts.engineering.quality.architecture_debt_task_policy",
        "scripts.engineering.quality.architecture_debt_task_support",
        "scripts.engineering.quality.architecture_quality_scorecard",
        "scripts.engineering.quality.architecture_quality_scoring",
        "scripts.engineering.quality.budget_evaluator",
        "scripts.engineering.quality.debt_scorecard",
        "scripts.engineering.quality.debt_scorecard_validation",
        "scripts.engineering.quality.exemptions_registry",
        "scripts.engineering.quality.exemptions_registry_access",
        "scripts.engineering.quality.exemptions_registry_paths",
        "scripts.engineering.quality.exemptions_registry_policy",
        "scripts.engineering.quality.exemptions_registry_targets",
        "scripts.engineering.quality.exemptions_registry_validation",
        "scripts.engineering.quality.inventory",
        "scripts.engineering.quality.registry_sync_service",
        "scripts.engineering.quality.report_formatter",
        "scripts.engineering.quality.scoring",
    ]
    repo_root = Path(__file__).resolve().parents[3]
    quality_root = repo_root / "scripts/engineering/quality"

    for module in modules:
        # -I ignores inherited PYTHONPATH and cwd. Each module gets a fresh process.
        code = (
            "import importlib, json, sys; "
            f"sys.path[:0] = {list(map(str, (repo_root / 'src', repo_root)))!r}; "
            f"module = importlib.import_module({module!r}); "
            "print(json.dumps(module.__file__))"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"Failed to import {module}: {result.stderr}"
        expected = quality_root / (
            "__init__.py"
            if module.endswith(".quality")
            else module.rsplit(".", 1)[1] + ".py"
        )
        assert Path(json.loads(result.stdout)).resolve() == expected.resolve(), (
            f"Unexpected origin for {module}: {result.stdout}"
        )
