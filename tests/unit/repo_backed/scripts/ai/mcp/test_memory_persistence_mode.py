"""Protocol-level containment for the shared file-backed MCP memory server."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

WRAPPER = Path("scripts/ai/mcp/mcp_memory_wrapper.sh")

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def _run_wrapper(mode: str | None) -> subprocess.CompletedProcess[str]:
    """Set the mode inside Bash so Windows-to-WSL env bridging cannot alter it."""
    mode_setup = (
        "unset BIOETL_AI_MEMORY_MODE"
        if mode is None
        else f"export BIOETL_AI_MEMORY_MODE={shlex.quote(mode)}"
    )
    # Keep the path repo-relative: Windows Path.resolve() produces ``E:/...``,
    # while the configured ``bash`` may be WSL Bash and requires ``/mnt/e/...``.
    wrapper_path = shlex.quote(WRAPPER.as_posix())
    return subprocess.run(
        [
            "bash",
            "-c",
            f"{mode_setup}; exec {wrapper_path}",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )


@pytest.mark.parametrize("mode", [None, "off", "read-only"])
def test_mcp_memory_safe_modes_exit_before_server_start(mode: str | None) -> None:
    completed = _run_wrapper(mode)

    assert completed.returncode == 78
    assert "Persistent MCP memory is disabled" in completed.stderr
    assert "npx" not in completed.stderr


def test_mcp_memory_rejects_unknown_mode_without_server_start() -> None:
    completed = _run_wrapper("unsafe")

    assert completed.returncode == 64
    assert "Invalid BIOETL_AI_MEMORY_MODE" in completed.stderr


def test_mcp_memory_default_store_is_scoped_and_untracked() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")

    # Scope via the resolved interpreter so Windows/venv paths stay consistent.
    assert '"${MEMORY_PYTHON}" -m memory.mcp_scope' in wrapper
    assert '--repo-root "${REPO_ROOT}"' in wrapper
    assert '--seed "${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"' in wrapper
    assert 'export MEMORY_FILE_PATH="$(' in wrapper


def test_mcp_memory_wrapper_is_git_executable() -> None:
    """Safe-mode contracts require the wrapper to be executable (mode 100755).

    Without the executable bit, ``exec ./mcp_memory_wrapper.sh`` returns 126
    instead of the documented safe-mode exits 78/64.
    """
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "-s", "--", WRAPPER.as_posix()],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Format: <mode> <object> <stage><tab><path>
    mode = result.stdout.split(maxsplit=1)[0]
    assert mode == "100755", (
        f"expected git mode 100755, got {mode!r}: {result.stdout!r}"
    )
