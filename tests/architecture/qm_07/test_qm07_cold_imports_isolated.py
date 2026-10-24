import pytest
"""Cold imports from a source checkout and an unrelated working directory.

Both src and the checkout root are explicit: QM-07 wheel isolation is BLOCKED
by core imports from scripts, recorded in test_qm07_cold_imports.py.
"""

import json
from pathlib import Path
import subprocess
import sys


@pytest.mark.architecture
def test_cold_imports(tmp_path: Path) -> None:
    modules = [
        "bioetl.infrastructure.quality",
        "bioetl.infrastructure.quality._baseline_validation",
        "bioetl.infrastructure.quality._decomposition_burndown_policy",
        "bioetl.infrastructure.quality._decomposition_owner_policy",
        "bioetl.infrastructure.quality._decomposition_program_policy",
        "bioetl.infrastructure.quality._decomposition_validation",
        "bioetl.infrastructure.quality._governance_validation",
        "bioetl.infrastructure.quality._grace_windows_validation",
        "bioetl.infrastructure.quality._primitives",
        "bioetl.infrastructure.quality._quarterly_targets_validation",
        "bioetl.infrastructure.quality.architecture_debt_artifact_tasks",
        "bioetl.infrastructure.quality.architecture_debt_reduction",
        "bioetl.infrastructure.quality.architecture_debt_task_generation",
        "bioetl.infrastructure.quality.architecture_debt_task_policy",
        "bioetl.infrastructure.quality.architecture_debt_task_support",
        "bioetl.infrastructure.quality.architecture_quality_scorecard",
        "bioetl.infrastructure.quality.architecture_quality_scoring",
        "bioetl.infrastructure.quality.budget_evaluator",
        "bioetl.infrastructure.quality.debt_scorecard",
        "bioetl.infrastructure.quality.debt_scorecard_validation",
        "bioetl.infrastructure.quality.exemptions_registry",
        "bioetl.infrastructure.quality.exemptions_registry_access",
        "bioetl.infrastructure.quality.exemptions_registry_paths",
        "bioetl.infrastructure.quality.exemptions_registry_policy",
        "bioetl.infrastructure.quality.exemptions_registry_targets",
        "bioetl.infrastructure.quality.exemptions_registry_validation",
        "bioetl.infrastructure.quality.inventory",
        "bioetl.infrastructure.quality.registry_sync_service",
        "bioetl.infrastructure.quality.report_formatter",
        "bioetl.infrastructure.quality.scoring",
    ]
    repo_root = Path(__file__).resolve().parents[3]
    quality_root = repo_root / "src/bioetl/infrastructure/quality"

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
