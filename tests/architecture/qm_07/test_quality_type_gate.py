"""GitHub Actions owns the full strict quality type gate (K6)."""

from pathlib import Path
import shlex

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.architecture
def test_required_github_gate_checks_quality_with_full_strict_scope():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    )
    steps = [step for job in workflow["jobs"].values() for step in job.get("steps", [])]
    gates = [step for step in steps if step.get("id") == "mypy"]
    assert len(gates) == 1
    gate = gates[0]
    assert not gate.get("continue-on-error", False)
    command = gate["run"].replace("\\\n", " ")
    args = shlex.split(
        next(
            line
            for line in command.splitlines()
            if "uv run" in line and "mypy --config-file" in line
        )
    )
    assert {
        "--strict",
        "src/bioetl",
        "src/memory",
        "scripts/engineering/quality",
    } <= set(args)
    assert 'exit "$status"' in command
