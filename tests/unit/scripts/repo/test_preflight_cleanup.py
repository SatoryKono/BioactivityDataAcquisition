from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "engineering" / "repo" / "preflight_cleanup.sh"


def _run_cleanup(
    tmp_path: Path, *, allow_slow_delete: bool = False
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "BIOETL_PREFLIGHT_SLOW_FS": "1",
            "BIOETL_PREFLIGHT_SLOW_FS_MAX_TARGETS": "1",
            "BIOETL_PREFLIGHT_DETAIL_LIMIT": "5",
        }
    )
    if allow_slow_delete:
        env["BIOETL_PREFLIGHT_ALLOW_SLOW_FS_DELETE"] = "1"

    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash script not available on Windows"
)
def test_preflight_cleanup_skips_large_delete_on_slow_filesystem(
    tmp_path: Path,
) -> None:
    for index in range(2):
        (tmp_path / f"pkg_{index}" / "__pycache__").mkdir(parents=True)

    result = _run_cleanup(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Skipped cleanup on slow WSL mount" in result.stdout
    assert (tmp_path / "pkg_0" / "__pycache__").is_dir()
    assert (tmp_path / "pkg_1" / "__pycache__").is_dir()


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash script not available on Windows"
)
def test_preflight_cleanup_allows_large_delete_when_explicitly_overridden(
    tmp_path: Path,
) -> None:
    for index in range(2):
        (tmp_path / f"pkg_{index}" / "__pycache__").mkdir(parents=True)

    result = _run_cleanup(tmp_path, allow_slow_delete=True)

    assert result.returncode == 0, result.stderr
    assert "Cleanup complete" in result.stdout
    assert not (tmp_path / "pkg_0" / "__pycache__").exists()
    assert not (tmp_path / "pkg_1" / "__pycache__").exists()
