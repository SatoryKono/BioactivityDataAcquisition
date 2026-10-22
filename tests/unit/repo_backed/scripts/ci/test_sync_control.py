"""Exact-argv guards for the ci-control uv sync wrapper."""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from scripts.engineering.ci import sync_control

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_ALLOWED_UV_ENV = {"UV_CACHE_DIR", "UV_PYTHON"}


def _clear_blocked_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("UV_") and key not in _ALLOWED_UV_ENV:
            monkeypatch.delenv(key, raising=False)


def test_sync_control_valid_args(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_blocked_uv(monkeypatch)
    monkeypatch.setenv("UV_PYTHON", "3.12")
    monkeypatch.setenv("UV_CACHE_DIR", "/tmp/uv-cache")
    with patch("subprocess.run") as mock_run:
        sync_control.run_sync(["sync", "--frozen", "--only-group", "ci-control"])
        mock_run.assert_called_once_with(
            ["uv", "sync", "--frozen", "--only-group", "ci-control"],
            check=True,
            shell=False,
        )


def test_sync_control_does_not_split_a_single_token() -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync --frozen --only-group ci-control"])
    assert exc.value.code == 1


def test_sync_control_rejects_nul(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", "ci-control\0"])
    assert exc.value.code == 1
    assert "NUL character" in capsys.readouterr().err


def test_sync_control_rejects_empty(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", ""])
    assert exc.value.code == 1
    assert "Empty string" in capsys.readouterr().err


def test_sync_control_rejects_uv_override(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["UV_CACHE_DIR=/tmp", "sync"])
    assert exc.value.code == 1
    assert "UV_* overrides" in capsys.readouterr().err


def test_sync_control_rejects_uv_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("UV_INDEX_URL", "https://example.invalid/simple")
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", "--only-group", "ci-control"])
    assert exc.value.code == 1
    assert "UV_INDEX_URL" in capsys.readouterr().err


def test_sync_control_rejects_unknown_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--all-extras", "--only-group", "ci-control"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err


def test_sync_control_requires_ci_control_group(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--frozen", "--only-group", "dev"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err


def test_sync_control_rejects_missing_frozen(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["sync", "--only-group", "ci-control"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err


def test_sync_control_rejects_reordered_argv(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        sync_control.run_sync(["--only-group", "ci-control", "sync", "--frozen"])
    assert exc.value.code == 1
    assert "not in the whitelist" in capsys.readouterr().err


def test_sync_control_subprocess_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_blocked_uv(monkeypatch)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(2, ["uv"])
        with pytest.raises(SystemExit) as exc:
            sync_control.run_sync(["sync", "--frozen", "--only-group", "ci-control"])
        assert exc.value.code == 2
        assert "uv sync failed" in capsys.readouterr().err


def test_sync_control_module_entrypoint_uses_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_blocked_uv(monkeypatch)
    with patch.object(sys, "argv", ["sync_control.py", "sync", "--frozen"]):
        with pytest.raises(SystemExit) as exc:
            sync_control.run_sync(sys.argv[1:])
    assert exc.value.code == 1
