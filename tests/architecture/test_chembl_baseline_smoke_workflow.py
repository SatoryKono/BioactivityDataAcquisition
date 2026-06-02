"""Architecture tests for the dedicated ChemblBaseline smoke workflow."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture

WORKFLOW_PATH = Path(".github/workflows/chembl-baseline-smoke.yml")


def _load_workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_chembl_baseline_smoke_workflow_exists_and_supports_ci_entrypoints() -> None:
    assert WORKFLOW_PATH.exists(), "ChemblBaseline smoke workflow must exist"

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "workflow_dispatch:" in workflow


def test_chembl_baseline_smoke_workflow_pins_runner_permissions_and_concurrency() -> (
    None
):
    payload = _load_workflow()

    assert payload["permissions"] == {"contents": "read"}
    assert payload["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }

    jobs = payload["jobs"]
    assert isinstance(jobs, dict)
    assert jobs
    assert all(job["runs-on"] == "ubuntu-24.04" for job in jobs.values())


def test_chembl_baseline_smoke_workflow_covers_python_312_and_313() -> None:
    payload = _load_workflow()
    matrix = payload["jobs"]["baseline-cli-runner-smoke"]["strategy"]["matrix"]

    assert matrix["python-version"] == ["3.12", "3.13"]


def test_chembl_baseline_smoke_workflow_uses_pinned_artifacts_and_summary() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "uses: ./.github/actions/setup-python-uv" in workflow
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    )
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "chembl-baseline-cli-runner-${{ matrix.python-version }}" in workflow
    assert "chembl-baseline-reconciliation" in workflow
    assert "chembl-baseline-architecture" in workflow
