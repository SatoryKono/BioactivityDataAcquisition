"""Owned hook interpreter selection must not silently escape its deployment."""

from __future__ import annotations

from pathlib import Path
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.engineering.dev import run_project_python as launcher

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", ["", "relative-interpreter", "missing-absolute"])
def test_invalid_owned_interpreter_never_falls_back_or_launches(
    tmp_path, monkeypatch, capsys, value
):
    if value == "missing-absolute":
        value = str(tmp_path / "private-interpreter-sentinel")
    monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", value)
    monkeypatch.setattr(sys, "argv", ["run_project_python.py", "-m", "pytest"])
    launch = Mock(side_effect=AssertionError("invalid override must not launch"))
    monkeypatch.setattr(launcher, "subprocess", SimpleNamespace(run=launch))
    assert launcher.main() == 2
    launch.assert_not_called()
    assert "private-interpreter-sentinel" not in capsys.readouterr().err


def test_owned_interpreter_and_child_failure_are_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", sys.executable)
    monkeypatch.setattr(launcher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["run_project_python.py", "-m", "pytest", "--version"]
    )
    launch = Mock(return_value=SimpleNamespace(returncode=7))
    monkeypatch.setattr(launcher, "subprocess", SimpleNamespace(run=launch))
    assert launcher.main() == 7
    launch.assert_called_once()
    assert launch.call_args.args == (
        [str(Path(sys.executable)), "-m", "pytest", "--version"],
    )
    assert launch.call_args.kwargs["cwd"] == tmp_path
    assert launch.call_args.kwargs["check"] is False
    assert launch.call_args.kwargs["env"]["PYTHONPATH"].split(os.pathsep)[:2] == [
        str(tmp_path / "src"),
        str(tmp_path),
    ]


@pytest.mark.parametrize("inherited", [False, True])
def test_child_imports_current_worktree_before_foreign_sources(
    tmp_path, monkeypatch, capfd, inherited
):
    current = tmp_path / "current"
    foreign = tmp_path / "foreign"
    (current / "src").mkdir(parents=True)
    foreign.mkdir()
    module = "owned_hook_source_probe"
    (current / "src" / f"{module}.py").write_text("print('current-worktree')\n")
    (foreign / f"{module}.py").write_text("print('foreign-worktree')\n")
    monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", sys.executable)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    if inherited:
        monkeypatch.setenv("PYTHONPATH", str(foreign))
    else:
        monkeypatch.delenv("PYTHONPATH", raising=False)
    original_path = os.environ.get("PYTHONPATH")
    monkeypatch.setattr(launcher, "REPO_ROOT", current)
    monkeypatch.setattr(sys, "argv", ["run_project_python.py", "-m", module])
    assert launcher.main() == 0
    assert capfd.readouterr().out.strip() == "current-worktree"
    assert os.environ.get("PYTHONPATH") == original_path


def test_interpreter_execution_error_is_controlled(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BIOETL_HOOK_PROJECT_PYTHON", sys.executable)
    monkeypatch.setattr(launcher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_project_python.py", "-m", "pytest"])
    monkeypatch.setattr(
        launcher,
        "subprocess",
        SimpleNamespace(run=Mock(side_effect=OSError("private-execution-sentinel"))),
    )
    assert launcher.main() == 2
    assert "private-execution-sentinel" not in capsys.readouterr().err
