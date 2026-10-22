import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

def load_sync_control():
    path = Path(".github/actions/setup-python-uv/sync_control.py")
    spec = importlib.util.spec_from_file_location("sync_control", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sync_control = load_sync_control()

def test_sync_control_valid_args():
    with patch("subprocess.run") as mock_run:
        sync_control.run_sync(["sync", "--frozen", "--only-group", "ci-control"])
        mock_run.assert_called_once_with(
            ["uv", "sync", "--frozen", "--only-group", "ci-control"],
            check=True,
            shell=False,
        )

def test_sync_control_shlex_parsing():
    with patch("subprocess.run") as mock_run:
        sync_control.run_sync(["sync", "--frozen", "--only-group", "ci-control"])
        mock_run.assert_called_once_with(
            ["uv", "sync", "--frozen", "--only-group", "ci-control"],
            check=True,
            shell=False,
        )

def test_sync_control_rejects_nul(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", "ci-control\0"])
    assert exc.value.code == 1
    assert "NUL character" in capsys.readouterr().err

def test_sync_control_rejects_empty(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", "''"])
    assert exc.value.code == 1
    assert "Empty string" in capsys.readouterr().err

def test_sync_control_rejects_uv_override(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["UV_CACHE_DIR=/tmp", "sync"])
    assert exc.value.code == 1
    assert "UV_* overrides" in capsys.readouterr().err

def test_sync_control_rejects_unknown_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--all-extras", "--only-group", "ci-control"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err

def test_sync_control_requires_ci_control_group(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--only-group", "dev"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err

def test_sync_control_validates_only_group_following_arg(capsys):
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--only-group"])
    assert exc.value.code == 1
    assert "--only-group must be followed by ci-control" in capsys.readouterr().err

def test_sync_control_subprocess_failure(capsys):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(2, ["uv"])
        with pytest.raises(SystemExit) as exc:
            sync_control.run_sync(["sync", "--only-group", "ci-control"])
        assert exc.value.code == 2
        assert "uv sync failed" in capsys.readouterr().err
