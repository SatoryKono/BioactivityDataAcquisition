"""Architecture test: validate GitHub Actions workflow YAML syntax.

Ensures all workflow files are structurally valid YAML with correct
GitHub Actions schema (jobs have runs-on/steps, steps have uses/run).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")


def _all_workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_workflow_is_valid_yaml(wf: Path) -> None:
    """Every workflow file must be parseable YAML."""
    content = wf.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_workflow_has_required_top_keys(wf: Path) -> None:
    """Every workflow must have 'on' (triggers) and 'jobs' keys."""
    data = yaml.safe_load(wf.read_text(encoding="utf-8"))
    # YAML parses unquoted 'on:' as boolean True
    assert "on" in data or True in data, f"{wf.name}: missing 'on:' trigger"
    assert "jobs" in data, f"{wf.name}: missing 'jobs:'"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_every_job_has_runs_on_and_steps(wf: Path) -> None:
    """Every job must define runs-on and steps."""
    data = yaml.safe_load(wf.read_text(encoding="utf-8"))
    jobs = data.get("jobs", {})
    for job_name, job_def in jobs.items():
        if not isinstance(job_def, dict):
            continue
        assert "runs-on" in job_def, f"{wf.name}:{job_name} missing 'runs-on'"
        assert "steps" in job_def, f"{wf.name}:{job_name} missing 'steps'"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_every_step_has_uses_or_run(wf: Path) -> None:
    """Every step must have 'uses' or 'run' (or both)."""
    data = yaml.safe_load(wf.read_text(encoding="utf-8"))
    jobs = data.get("jobs", {})
    for job_name, job_def in jobs.items():
        if not isinstance(job_def, dict):
            continue
        for i, step in enumerate(job_def.get("steps", [])):
            if not isinstance(step, dict):
                continue
            assert "uses" in step or "run" in step, (
                f"{wf.name}:{job_name} step[{i}] missing 'uses' or 'run'"
            )
