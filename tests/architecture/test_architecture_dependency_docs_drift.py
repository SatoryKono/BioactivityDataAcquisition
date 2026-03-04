"""Architecture tests for dependency-map docs-as-code drift guardrails."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_dependency_map_script_exists() -> None:
    script = Path("scripts/generate_architecture_dependency_map.py")
    assert script.exists(), "Missing dependency map generator script"


def test_mkdocs_nav_includes_dependency_map() -> None:
    mkdocs = Path("mkdocs.yml").read_text(encoding="utf-8")
    assert "02-architecture/generated/module-dependency-map.md" in mkdocs


def test_docs_workflow_checks_dependency_map_drift() -> None:
    workflow = Path(".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "Check architecture dependency docs drift" in workflow
    assert "scripts/generate_architecture_dependency_map.py --check" in workflow


def test_tests_workflow_checks_dependency_map_drift() -> None:
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Check architecture dependency docs drift" in workflow
    assert "scripts/generate_architecture_dependency_map.py --check" in workflow


def test_nightly_workflow_regenerates_dependency_map() -> None:
    workflow_path = Path(".github/workflows/architecture-docs-nightly.yml")
    assert workflow_path.exists(), "Missing nightly architecture docs workflow"

    workflow = workflow_path.read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "15 2 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "Regenerate architecture dependency map" in workflow
    assert "scripts/generate_architecture_dependency_map.py --update" in workflow
    assert "Upload architecture docs artifacts" in workflow
    assert "architecture-dependency-map-nightly" in workflow


def test_dependency_map_drift_check_passes_current_repo() -> None:
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_architecture_dependency_map.py",
            "--check",
        ],
        capture_output=True,
        env=env,
        text=True,
    )
    assert result.returncode == 0, (
        "Dependency-map docs drift check failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
