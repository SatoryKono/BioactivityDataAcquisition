"""Strict mypy scope remains aligned after moving engineering quality modules."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
TARGETS = ("src/bioetl", "src/memory", "scripts/engineering/quality")


@pytest.mark.parametrize(
    "name", ["pr-required.yml", "type-checking.yml", "type-checking-cold.yml"]
)
def test_mypy_workflows_check_all_strict_targets(name: str) -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
    )
    commands = [
        line
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        for line in str(step.get("run", "")).splitlines()
        if "mypy --config-file" in line
    ]
    assert commands
    for command in commands:
        assert "--strict" in command
        assert "--follow-imports=skip" not in command
        assert all(target in command.split() for target in TARGETS)


@pytest.mark.parametrize("name", ["run_mypy.sh", "run_mypy.ps1"])
def test_mypy_wrappers_default_to_all_strict_targets(name: str) -> None:
    lines = (
        (ROOT / "scripts/engineering/dev" / name)
        .read_text(encoding="utf-8")
        .splitlines()
    )
    defaults = [
        line
        for line in lines
        if line.startswith("DEFAULT_ARGS=(")
        or ("$ArgsList = @(" in line and "--strict" in line)
    ]
    assert len(defaults) == 1
    assert "--strict" in defaults[0]
    assert all(target in defaults[0] for target in TARGETS)
