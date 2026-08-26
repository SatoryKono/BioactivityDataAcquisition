"""Closeout gates for the vendor-neutral AI memory architecture program."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.registry import load_memory_registry, validate_memory_registry

pytestmark = pytest.mark.architecture


def test_registry_is_complete_and_memory_runtime_stays_outside_bioetl() -> None:
    assert validate_memory_registry(load_memory_registry()) == []
    assert not Path("src/bioetl/memory").exists()


def test_memory_pretest_gate_is_blocking() -> None:
    script = Path("scripts/engineering/dev/pretest_guardrails.sh").read_text(
        encoding="utf-8"
    )
    assert "memory.tooling.validate" in script
    assert "memory.tooling.prune --json --check" in script


def test_shared_mcp_memory_requires_explicit_write_enablement() -> None:
    bash_wrapper = Path("scripts/ai/mcp/mcp_memory_wrapper.sh").read_text(
        encoding="utf-8"
    )
    powershell_wrapper = Path("scripts/ai/mcp/mcp_memory_wrapper.ps1").read_text(
        encoding="utf-8"
    )
    assert "BIOETL_AI_MEMORY_MODE:-off" in bash_wrapper
    assert "'off'" in powershell_wrapper
    assert "read-write" in bash_wrapper
    assert "read-write" in powershell_wrapper
    assert r".venv-win\Scripts\python.exe" in powershell_wrapper
    assert ".venv-win/Scripts/python.exe" in bash_wrapper
    win = bash_wrapper.index(".venv-win/Scripts/python.exe")
    posix = bash_wrapper.index(".venv/bin/python")
    assert posix < win
    assert "$explicitMemoryMode" in powershell_wrapper
    assert r"$repoRoot\src" in powershell_wrapper


def test_memory_workflow_helper_prefers_windows_venv() -> None:
    """run_workflow.sh must discover .venv-win on native Windows (#9121)."""
    script = Path("scripts/memory/run_workflow.sh").read_text(encoding="utf-8")
    assert ".venv-win/Scripts/python.exe" in script
    win = script.index(".venv-win/Scripts/python.exe")
    posix = script.index(".venv/bin/python")
    assert win < posix
