"""Owned hook interpreter selection must not silently escape its deployment."""

from __future__ import annotations

from pathlib import Path
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
    launch.assert_called_once_with(
        [str(Path(sys.executable)), "-m", "pytest", "--version"],
        cwd=tmp_path,
        check=False,
    )


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
