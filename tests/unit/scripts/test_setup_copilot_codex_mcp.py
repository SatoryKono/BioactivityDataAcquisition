"""Unit tests for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import pytest

import json
import os
from pathlib import Path

from scripts.ai.codex import setup_mcp


pytestmark = pytest.mark.unit


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
        ]
    )

    assert exit_code == 0

    payload = json.loads((output_root / ".mcp.json").read_text(encoding="utf-8"))
    qodo_payload = json.loads(
        (output_root / ".qodo" / "mcp.json").read_text(encoding="utf-8")
    )
    codex_settings = json.loads(
        (output_root / ".codex" / "settings.json").read_text(encoding="utf-8")
    )
    gemini_settings = json.loads(
        (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    servers = payload["mcpServers"]
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"

    assert codex_settings["mcpServers"] == servers
    assert qodo_payload["mcpServers"] == servers
    assert servers["filesystem"]["args"][-1] == str(workspace_root.resolve())
    assert servers["sequential-thinking"]["args"] == [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking@2025.12.18",
    ]
    assert servers["pdf"]["args"] == [
        "-y",
        "@modelcontextprotocol/server-pdf@1.3.1",
        "--stdio",
    ]
    assert servers["memory"]["env"]["MEMORY_FILE_PATH"] == str(
        (workspace_root / "docs/00-project/ai/memory/mcp-memory.json").resolve()
    )
    assert servers["github"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["mermaid"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_mermaid_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["docker-docs"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_docker_docs_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["paper-search"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_paper_search_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["dockerhub"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_dockerhub_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["needle"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_needle_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["biomoltechDocs"]["type"] == "http"
    assert servers["biomoltechDocs"]["url"] == "https://biomoltech.mintlify.app/mcp"
    assert servers["openaiDeveloperDocs"]["type"] == "http"
    assert servers["openaiDeveloperDocs"]["url"] == "https://developers.openai.com/mcp"
    assert servers["mintlify"]["url"] == "https://mcp.mintlify.com"
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert (
        gemini_settings["mcpServers"]["openaiDeveloperDocs"]["httpUrl"]
        == "https://developers.openai.com/mcp"
    )
