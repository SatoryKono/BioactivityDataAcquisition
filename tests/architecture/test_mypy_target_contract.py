"""Strict mypy scope remains aligned after moving engineering quality modules."""

import ast
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


def test_pre_push_checks_all_strict_targets() -> None:
    config = yaml.safe_load(
        (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hook = next(
        hook
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
        if hook["id"] == "mypy-strict"
    )
    assert "--strict" in hook["entry"].split()
    assert all(target in hook["entry"].split() for target in TARGETS)


@pytest.mark.parametrize(
    ("path", "variable"),
    [
        ("scripts/engineering/ci/presubmit_gate.py", "_MYPY_TREES"),
        ("scripts/engineering/dev/zed_mypy.py", "cmd"),
    ],
)
def test_python_entrypoints_check_all_targets(path: str, variable: str) -> None:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == variable
            for target in node.targets
        )
    )
    values = [
        node.value
        for node in ast.walk(assignment.value)
        if isinstance(node, ast.Constant)
    ]
    assert all(target in values for target in TARGETS)


def test_quality_only_changes_require_type_checking() -> None:
    from scripts.engineering.ci.pr_gate import REQUIRED, classify_changes, load_catalog

    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    matrix = classify_changes(
        catalog,
        ["scripts/engineering/quality/debt_scorecard.py"],
        head_sha="a" * 40,
    )
    assert matrix["decisions"]["type-checking"]["decision"] == REQUIRED
