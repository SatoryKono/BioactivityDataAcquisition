# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: validate GitHub Actions workflow YAML syntax.

Ensures all workflow files are structurally valid YAML with correct
GitHub Actions schema (jobs have runs-on/steps, steps have uses/run).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"


def _all_workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_workflow_is_valid_yaml(
    wf: Path, workflow_yaml_cache: dict[Path, object]
) -> None:
    """Every workflow file must be parseable YAML."""
    data = workflow_yaml_cache[wf]
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_workflow_has_no_utf8_bom(
    wf: Path,
    workflow_text_cache: dict[Path, str],
) -> None:
    """Workflow keys must not be prefixed by hidden UTF-8 BOM characters."""
    assert not workflow_text_cache[wf].startswith("\ufeff"), (
        f"{wf.name}: remove the UTF-8 BOM before the top-level name key"
    )


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_workflow_has_required_top_keys(
    wf: Path,
    workflow_yaml_cache: dict[Path, object],
) -> None:
    """Every workflow must have 'on' (triggers) and 'jobs' keys."""
    data = workflow_yaml_cache[wf]
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"
    # YAML parses unquoted 'on:' as boolean True
    assert "on" in data or True in data, f"{wf.name}: missing 'on:' trigger"
    assert "jobs" in data, f"{wf.name}: missing 'jobs:'"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_event_does_not_mix_paths_and_paths_ignore(
    wf: Path,
    workflow_yaml_cache: dict[Path, object],
) -> None:
    """GitHub forbids paths and paths-ignore on the same event."""
    data = workflow_yaml_cache[wf]
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"
    triggers = data.get("on", data.get(True))
    if not isinstance(triggers, dict):
        return

    for event_name, event_config in triggers.items():
        if not isinstance(event_config, dict):
            continue
        assert not ({"paths", "paths-ignore"} <= event_config.keys()), (
            f"{wf.name}:{event_name} cannot define both paths and paths-ignore"
        )


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_every_job_has_runs_on_and_steps(
    wf: Path,
    workflow_yaml_cache: dict[Path, object],
) -> None:
    """Every job must define runs-on and steps."""
    data = workflow_yaml_cache[wf]
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"
    jobs = data.get("jobs", {})
    for job_name, job_def in jobs.items():
        if not isinstance(job_def, dict):
            continue
        # Reusable workflow jobs use `uses:` and must not declare sibling runs-on/steps.
        if "uses" in job_def:
            continue
        assert "runs-on" in job_def, f"{wf.name}:{job_name} missing 'runs-on'"
        assert "steps" in job_def, f"{wf.name}:{job_name} missing 'steps'"


@pytest.mark.parametrize("wf", _all_workflow_files(), ids=lambda p: p.name)
def test_every_step_has_uses_or_run(
    wf: Path,
    workflow_yaml_cache: dict[Path, object],
) -> None:
    """Every step must have 'uses' or 'run' (or both)."""
    data = workflow_yaml_cache[wf]
    assert isinstance(data, dict), f"{wf.name}: not a YAML mapping"
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
