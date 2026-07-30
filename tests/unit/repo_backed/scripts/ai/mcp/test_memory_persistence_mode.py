"""Protocol-level containment for the shared file-backed MCP memory server."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

WRAPPER = Path("scripts/ai/mcp/mcp_memory_wrapper.sh")
_UNSET_MODE = "__BIOETL_MODE_UNSET__"


def _run_wrapper(mode: str | None) -> subprocess.CompletedProcess[str]:
    """Set the mode inside Bash so Windows-to-WSL env bridging cannot alter it."""
    return subprocess.run(
        [
            "bash",
            "-c",
            (
                'if [[ "$1" == "$3" ]]; then '
                "unset BIOETL_AI_MEMORY_MODE; "
                "else export BIOETL_AI_MEMORY_MODE=\"$1\"; fi; "
                'exec "$2"'
            ),
            "bash",
            mode if mode is not None else _UNSET_MODE,
            WRAPPER.resolve().as_posix(),
            _UNSET_MODE,
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
