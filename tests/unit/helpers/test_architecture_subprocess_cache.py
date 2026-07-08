from __future__ import annotations

import pickle
import subprocess
from pathlib import Path

import pytest

from tests.architecture import conftest as architecture_conftest

pytestmark = pytest.mark.unit


def _write_cache_payload(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)


def test_load_subprocess_disk_cache_ignores_nonzero_returncodes(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "subprocess-cache.pkl"
    command = ["python", "-m", "scripts.schema", "generate-config-matrix", "--check"]
    _write_cache_payload(
        cache_path,
        {
            "command": command,
            "returncode": 1,
            "stdout": "[drift] mismatch: docs\\04-reference\\config_comparison_matrix.csv",
            "stderr": "",
        },
    )

    assert (
        architecture_conftest._load_subprocess_disk_cache(cache_path, command) is None
    )


def test_load_subprocess_disk_cache_returns_successful_result(tmp_path: Path) -> None:
    cache_path = tmp_path / "subprocess-cache.pkl"
    command = ["python", "-m", "scripts.schema", "generate-config-matrix", "--check"]
    _write_cache_payload(
        cache_path,
        {
            "command": command,
            "returncode": 0,
            "stdout": "[ok] config matrix artifacts are up to date",
            "stderr": "",
        },
    )

    result = architecture_conftest._load_subprocess_disk_cache(cache_path, command)

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.args == command
    assert result.returncode == 0
    assert result.stdout == "[ok] config matrix artifacts are up to date"
    assert result.stderr == ""


def test_store_subprocess_disk_cache_skips_nonzero_returncodes(tmp_path: Path) -> None:
    cache_path = tmp_path / "subprocess-cache.pkl"
    architecture_conftest._store_subprocess_disk_cache(
        cache_path,
        command=["python", "-m", "scripts.schema", "generate-config-matrix", "--check"],
        result=subprocess.CompletedProcess(
            args=[
                "python",
                "-m",
                "scripts.schema",
                "generate-config-matrix",
                "--check",
            ],
            returncode=1,
            stdout="[drift] mismatch",
            stderr="",
        ),
    )

    assert not cache_path.exists()


def test_effective_subprocess_timeout_detects_windows_pycharm_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PyCharm may be detectable only through the runner script argv."""
    monkeypatch.setattr(architecture_conftest.sys, "platform", "win32")
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(
        architecture_conftest.sys,
        "argv",
        [r"C:\Program Files\JetBrains\PyCharm\helpers\pycharm\_jb_pytest_runner.py"],
    )

    assert architecture_conftest._effective_subprocess_timeout(60) == 180.0


def test_effective_subprocess_timeout_keeps_non_pycharm_windows_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-PyCharm runs should keep the caller's explicit timeout."""
    monkeypatch.setattr(architecture_conftest.sys, "platform", "win32")
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(architecture_conftest.sys, "argv", ["pytest"])

    assert architecture_conftest._effective_subprocess_timeout(60) == 60
