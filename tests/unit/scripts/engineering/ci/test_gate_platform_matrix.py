"""The matrix reflects live workflows without requiring retired CI inputs."""

from __future__ import annotations

import pytest

from scripts.engineering.ci import report_gate_platform_matrix as matrix

pytestmark = pytest.mark.unit


def test_matrix_checks_current_workflow_content(tmp_path, monkeypatch):
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    workflow = workflows / "example.yml"
    workflow.write_text(
        "name: Example\non: [pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(matrix, "GITHUB", workflows)
    monkeypatch.setattr(matrix, "OUTPUT", tmp_path / "matrix.md")
    monkeypatch.setattr("sys.argv", ["gate-platform-matrix"])
    assert matrix.main() == 0
    output = matrix.OUTPUT.read_text(encoding="utf-8")
    assert "example.yml:test" in output
    assert "pull_request" in output
    assert "CircleCI" not in output
    monkeypatch.setattr("sys.argv", ["gate-platform-matrix", "--check"])
    assert matrix.main() == 0
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("ubuntu-latest", "ubuntu-24.04"),
        encoding="utf-8",
    )
    assert matrix.main() == 1
