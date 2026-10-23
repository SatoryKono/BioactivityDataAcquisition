import pytest
import subprocess
import os

def test_cold_imports():
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
    # Test isolated import from external cwd using PYTHONPATH pointing to repo root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

    for mod in modules:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_root}/src"
        res = subprocess.run(
            ["uv", "run", "python", "-c", f"import {mod}; print({mod}.__file__)"],
            capture_output=True,
            text=True,
            cwd="/tmp",
            env=env
        )
        assert res.returncode == 0, f"Failed to import {mod} from external cwd: {res.stderr}"
        assert f"src/bioetl/infrastructure/quality/" in res.stdout, f"Unexpected origin for {mod}: {res.stdout}"
