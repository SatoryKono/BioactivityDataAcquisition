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
    devin_config = json.loads(
        (output_root / ".devin" / "config.json").read_text(encoding="utf-8")
    )
    gemini_settings = json.loads(
        (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    zed_payload = json.loads(
        (output_root / ".zed" / "mcp.json").read_text(encoding="utf-8")
    )
    servers = payload["mcpServers"]
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"
    removed_servers = {
        "sequential-thinking",
        "pdf",
        "needle",
        "docker-docs",
        "dockerhub",
        "paper-search",
        "openaiDeveloperDocs",
        "sonarqube",
        "chembl",
        "pubchem",
        "pubmed",
    }

    runtime_servers = codex_settings["mcpServers"]
    assert devin_config["mcpServers"] == runtime_servers
    assert qodo_payload["mcpServers"] == servers
    assert zed_payload["mcpServers"] == servers
    assert not removed_servers.intersection(servers)
    assert servers["filesystem"]["args"][-1] == "."
    assert runtime_servers["filesystem"]["args"][-1] == str(workspace_root.resolve())
    assert servers["memory"]["args"] == [
        "-y",
        "@modelcontextprotocol/server-memory@2026.1.26",
    ]
    assert (
        servers["memory"]["env"]["MEMORY_FILE_PATH"]
        == "docs/00-project/ai/memory/mcp-memory.json"
    )
    assert runtime_servers["memory"]["env"]["MEMORY_FILE_PATH"] == str(
        (workspace_root / "docs/00-project/ai/memory/mcp-memory.json").resolve()
    )
    assert servers["github"]["args"][0] == (
        f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
    )
    assert runtime_servers["github"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["docker"]["args"][0] == (
        f"scripts/ai/mcp/mcp_docker_wrapper{wrapper_suffix}"
    )
    assert servers["context7"]["args"][0] == (
        f"scripts/ai/mcp/mcp_context7_wrapper{wrapper_suffix}"
    )
    assert servers["grafana"]["args"][0] == (
        f"scripts/ai/mcp/mcp_grafana_wrapper{wrapper_suffix}"
    )
    assert servers["mermaid"]["args"][0] == (
        f"scripts/ai/mcp/mcp_mermaid_wrapper{wrapper_suffix}"
    )
    assert runtime_servers["mermaid"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_mermaid_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["biomoltechDocs"]["type"] == "http"
    assert servers["biomoltechDocs"]["url"] == "https://biomoltech.mintlify.app/mcp"
    assert servers["mintlify"]["url"] == "https://mcp.mintlify.com"
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert (
        gemini_settings["mcpServers"]["biomoltechDocs"]["httpUrl"]
        == "https://biomoltech.mintlify.app/mcp"
    )


def test_main_recreates_empty_workspace_json_configs(tmp_path: Path) -> None:
    """Empty local runtime config files should be treated as missing and rewritten."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()
    (output_root / ".codex").mkdir(parents=True)
    (output_root / ".devin").mkdir(parents=True)
    (output_root / ".gemini").mkdir(parents=True)
    (output_root / ".codex" / "settings.json").write_text("", encoding="utf-8")
    (output_root / ".devin" / "config.json").write_text("", encoding="utf-8")
    (output_root / ".gemini" / "settings.json").write_text("", encoding="utf-8")

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
    assert json.loads(
        (output_root / ".codex" / "settings.json").read_text(encoding="utf-8")
    )["mcpServers"]["filesystem"]["args"][-1] == str(workspace_root.resolve())
    assert json.loads(
        (output_root / ".devin" / "config.json").read_text(encoding="utf-8")
    )["mcpServers"]["filesystem"]["args"][-1] == str(workspace_root.resolve())
    assert json.loads(
        (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )["mcpServers"]["filesystem"]["args"][-1] == str(workspace_root.resolve())


def test_skip_codex_validation_still_updates_codex_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launcher setup should update Codex config without running slow CLI validation."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    fake_home = tmp_path / "home"
    workspace_root.mkdir()
    fake_home.mkdir()

    def fail_validation(_workspace_root: Path) -> None:
        raise AssertionError("Codex CLI validation should have been skipped")

    monkeypatch.setattr(setup_mcp.Path, "home", lambda: fake_home)
    monkeypatch.setattr(setup_mcp, "_run_codex_validation", fail_validation)

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex-validation",
            "--skip-gemini-settings",
        ]
    )

    assert exit_code == 0
    codex_config = fake_home / ".codex" / "config.toml"
    rendered = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.filesystem]" in rendered
    assert "[mcp_servers.memory]" in rendered
    # The workspace root appears in the filesystem server args, either as "." (portable)
    # or as an absolute path depending on the portable_workspace_paths flag
    assert "filesystem" in rendered
