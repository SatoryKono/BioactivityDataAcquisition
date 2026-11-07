"""Protocol-level containment for the shared file-backed MCP memory server."""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_WINDOWS_BASH_SKIP = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="bash-based MCP memory wrapper is not reliable on native Windows shells",
)

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


@_WINDOWS_BASH_SKIP
@pytest.mark.parametrize("mode", [None, "off", "read-only"])
def test_mcp_memory_safe_modes_exit_before_server_start(mode: str | None) -> None:
    completed = _run_wrapper(mode)

    assert completed.returncode == 78
    assert "Persistent MCP memory is disabled" in completed.stderr
    assert "npx" not in completed.stderr


@_WINDOWS_BASH_SKIP
def test_mcp_memory_rejects_unknown_mode_without_server_start() -> None:
    completed = _run_wrapper("unsafe")

    assert completed.returncode == 64
    assert "Invalid BIOETL_AI_MEMORY_MODE" in completed.stderr


@_WINDOWS_BASH_SKIP
def test_mcp_memory_read_write_does_not_require_npm_cache(tmp_path: Path) -> None:
    """The Python wrapper must start even when npm's cache cannot be created."""
    root = Path(__file__).resolve().parents[6]
    workspace = tmp_path / "workspace"
    for relative in (
        "scripts/ai/mcp/mcp_memory_wrapper.sh",
        "scripts/ai/mcp/support/load_repo_env.sh",
        "scripts/ai/mcp/support/token_validation.sh",
        "scripts/ops/support/load_repo_env.sh",
        "src/memory/__init__.py",
        "src/memory/fs_confine.py",
        "src/memory/mcp_scope.py",
        "src/memory/mcp_server.py",
        "src/memory/storage.py",
    ):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    npm_cache = blocked_parent / "npm-cache"
    seed = workspace / "docs/seed.json"
    seed.parent.mkdir(parents=True)
    seed.write_text('{"entities":[],"relations":[]}\n', encoding="utf-8")
    seed_before = seed.read_bytes()
    graph = workspace / ".cache/mcp-memory/graph.json"
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "create_entities",
                "arguments": {
                    "entities": [
                        {"name": "fixture", "entityType": "note", "observations": []}
                    ]
                },
            },
        },
    ]
    completed = subprocess.run(
        ["bash", str(workspace / WRAPPER)],
        cwd=workspace,
        input="\n".join(json.dumps(request) for request in requests) + "\n",
        env={
            **os.environ,
            "BIOETL_AI_MEMORY_MODE": "read-write",
            "BIOETL_MCP_VALIDATE_ONLY": "0",
            "BIOETL_REPO_ENV_LOADED": "0",
            "BIOETL_WSL_VENV_DIR": str(Path(sys.executable).parent.parent),
            "NPM_CONFIG_CACHE": str(npm_cache),
            "MEMORY_SEED_PATH": str(seed),
            "MEMORY_FILE_PATH": str(graph),
        },
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    replies = [json.loads(line) for line in completed.stdout.splitlines()]
    assert replies[0]["result"]["serverInfo"]["name"] == "bioetl-memory"
    assert not replies[1]["result"].get("isError")
    assert (
        json.loads(graph.read_text(encoding="utf-8"))["entities"][0]["name"]
        == "fixture"
    )
    assert seed.read_bytes() == seed_before
    assert not npm_cache.exists()


def test_mcp_memory_default_store_is_scoped_and_untracked() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")

    # Scope via the resolved interpreter so Windows/venv paths stay consistent.
    assert '"${MEMORY_PYTHON}" -m memory.mcp_scope' in wrapper
    assert '--repo-root "${REPO_ROOT}"' in wrapper
    assert (
        "MEMORY_SEED_PATH:-${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
        in wrapper
    )
    assert 'scope_args+=(--target "${MEMORY_FILE_PATH}")' in wrapper
    assert 'if ! MEMORY_FILE_PATH="$(' in wrapper
    assert 'export MEMORY_FILE_PATH\nexec' in wrapper


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
