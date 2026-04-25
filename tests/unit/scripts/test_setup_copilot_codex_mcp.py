"""Unit tests for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.ai.codex import setup_mcp


def test_main_uses_workspace_root_for_generated_server_paths(tmp_path: Path) -> None:
    """Generated server paths should follow the requested workspace root."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
        ]
    )

    assert exit_code == 0

    payload = json.loads((output_root / ".mcp.json").read_text(encoding="utf-8"))
    servers = payload["mcpServers"]
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"

    assert servers["filesystem"]["args"][-1] == str(workspace_root.resolve())
    assert servers["memory"]["env"]["MEMORY_FILE_PATH"] == str(
        (workspace_root / "docs/00-project/ai/memory/mcp-memory.json").resolve()
    )
    assert servers["github"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["needle"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_needle_wrapper{wrapper_suffix}"
        ).resolve()
    )
