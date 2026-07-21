"""Unit tests for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.ai.codex import setup_mcp


pytestmark = pytest.mark.unit


def _to_bash_path(path: Path) -> str:
    value = path.as_posix()
    if len(value) >= 3 and value[1] == ":" and value[2] == "/":
        return f"/mnt/{value[0].lower()}{value[2:]}"
    return value


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
    expected_servers = {
        "memory",
        "filesystem",
        "fetch",
        "github",
        "docker",
        "context7",
        "ast-grep",
        "mcp-code-interpreter",
        "prometheus",
        "grafana",
        "brave-search",
        "neo4j-cypher",
        "neo4j-memory",
        "mermaid",
        "deja",
        "adr-analysis",
        "mutmut",
        "code-analyzer",
        "github-actions",
        "deepwiki",
        "ref",
    }
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
        "biomoltechDocs",
        "mintlify",
    }

    runtime_servers = codex_settings["mcpServers"]
    devin_servers = devin_config["mcpServers"]
    assert set(servers) == expected_servers
    assert devin_servers == servers
    assert qodo_payload["mcpServers"] == servers
    assert zed_payload["mcpServers"] == servers
    assert not removed_servers.intersection(servers)
    assert not removed_servers.intersection(gemini_settings["mcpServers"])
    assert servers["filesystem"]["args"][-1] == "."
    assert devin_servers["filesystem"]["args"][-1] == "."
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
    assert servers["fetch"]["args"] == [
        "--python",
        "3.13",
        "--from",
        "mcp-server-fetch==2025.4.7",
        "mcp-server-fetch",
    ]
    assert runtime_servers["fetch"]["args"] == servers["fetch"]["args"]
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
    for server_name, wrapper_stem in {
        "deja": "mcp_deja_wrapper",
        "adr-analysis": "mcp_adr_analysis_wrapper",
        "mutmut": "mcp_mutmut_wrapper",
        "code-analyzer": "mcp_code_analyzer_wrapper",
        "github-actions": "mcp_github_actions_wrapper",
    }.items():
        assert servers[server_name]["args"][0] == (
            f"scripts/ai/mcp/{wrapper_stem}{wrapper_suffix}"
        )
        assert runtime_servers[server_name]["args"][0] == str(
            (
                workspace_root / f"scripts/ai/mcp/{wrapper_stem}{wrapper_suffix}"
            ).resolve()
        )
    assert servers["deja"]["env"]["NPM_CONFIG_CACHE"] == ".cache/npm-cache"
    assert servers["adr-analysis"]["env"] == {
        "PROJECT_PATH": ".",
        "ADR_PATH": "docs/02-architecture/decisions",
    }
    assert runtime_servers["adr-analysis"]["env"] == {
        "PROJECT_PATH": str(workspace_root.resolve()),
        "ADR_PATH": str((workspace_root / "docs/02-architecture/decisions").resolve()),
    }
    assert servers["mutmut"]["env"]["MUTMUT_PROJECT_PATH"] == "."
    assert servers["code-analyzer"]["env"]["PROJECT_PATH"] == "."
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert servers["ref"]["type"] == "http"
    assert servers["ref"]["url"] == "https://api.ref.tools/mcp"
    assert (
        gemini_settings["mcpServers"]["ref"]["httpUrl"] == "https://api.ref.tools/mcp"
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
    assert (
        json.loads(
            (output_root / ".devin" / "config.json").read_text(encoding="utf-8")
        )["mcpServers"]["filesystem"]["args"][-1]
        == "."
    )
    assert json.loads(
        (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )["mcpServers"]["filesystem"]["args"][-1] == str(workspace_root.resolve())


def test_devin_projection_is_portable_across_workspace_roots(
    tmp_path: Path,
) -> None:
    """Tracked Devin MCP data should be stable and preserve Devin-owned settings."""
    generated: list[dict[str, object]] = []
    for name in ("first-clone", "second-clone"):
        workspace_root = tmp_path / name / "workspace"
        output_root = tmp_path / name / "output"
        workspace_root.mkdir(parents=True)
        devin_path = output_root / ".devin" / "config.json"
        devin_path.parent.mkdir(parents=True)
        devin_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "devin": {"org_id": "org-test"},
                    "shell": {"setup_complete": True},
                    "theme_mode": "light",
                    "mcpServers": {"stale": {"command": "old"}},
                }
            ),
            encoding="utf-8",
        )

        assert (
            setup_mcp.main(
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
            == 0
        )
        generated.append(json.loads(devin_path.read_text(encoding="utf-8")))

    assert generated[0] == generated[1]
    assert generated[0]["devin"] == {"org_id": "org-test"}
    assert generated[0]["shell"] == {"setup_complete": True}
    assert generated[0]["theme_mode"] == "light"
    assert generated[0]["mcpServers"]["filesystem"]["args"][-1] == "."


def test_skip_codex_validation_still_updates_codex_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launcher setup should update Codex config without running slow CLI validation."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    fake_home = tmp_path / "home"
    workspace_root.mkdir()
    fake_home.mkdir()
    codex_dir = fake_home / ".codex"
    codex_dir.mkdir()
    codex_config = codex_dir / "config.toml"
    codex_config.write_text(
        """
[mcp_servers.pycharm]
url = "http://127.0.0.1:64342/sse"

[mcp_servers.biomoltechDocs]
url = "https://retired.invalid/mcp"

[mcp_servers.mintlify]
url = "https://retired.invalid/mcp"
""".lstrip(),
        encoding="utf-8",
    )

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
    rendered = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.pycharm]" in rendered
    assert "[mcp_servers.biomoltechDocs]" not in rendered
    assert "[mcp_servers.mintlify]" not in rendered
    assert "[mcp_servers.filesystem]" in rendered
    assert "[mcp_servers.memory]" in rendered
    assert "[mcp_servers.ref]" in rendered
    assert 'url = "https://api.ref.tools/mcp"' in rendered
    assert 'env_http_headers = { x-ref-api-key = "REF_TOOL_API_KEY" }' in rendered
    assert "?apiKey=" not in rendered
    # The workspace root appears in the filesystem server args, either as "." (portable)
    # or as an absolute path depending on the portable_workspace_paths flag
    assert "filesystem" in rendered


def test_ensure_mcp_reuses_current_config_and_repairs_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal launches should reuse current MCP state and repair actual drift."""
    root = Path(__file__).resolve().parents[3]
    workspace_root = tmp_path / "workspace"
    fake_home = tmp_path / "runtime-home"
    workspace_root.mkdir()
    fake_home.mkdir()
    monkeypatch.setattr(setup_mcp.Path, "home", lambda: fake_home)

    assert (
        setup_mcp.main(
            [
                "--root",
                str(workspace_root),
                "--workspace-root",
                str(workspace_root),
                "--skip-codex-validation",
                "--skip-gemini-settings",
            ]
        )
        == 0
    )

    runtime_env = os.environ.copy()
    runtime_env.update(
        {
            "HOME": _to_bash_path(fake_home),
            "REPO_ROOT": _to_bash_path(workspace_root),
            "CODEX_VALIDATE_MCP_LIST": "0",
        }
    )
    ensure_script = _to_bash_path(
        root / "scripts/ai/codex/helper/ensure-mcp.sh"
    )
    codex_config = fake_home / ".codex/config.toml"
    initial_codex_config = codex_config.read_text(encoding="utf-8")
    bash_root = _to_bash_path(root)

    unchanged = subprocess.run(
        ["bash", ensure_script, "--ensure"],
        cwd=bash_root,
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert unchanged.returncode == 0, unchanged.stderr
    assert "[mcp] MCP config is ready" in unchanged.stdout
    if "(unchanged)" in unchanged.stdout:
        assert codex_config.read_text(encoding="utf-8") == initial_codex_config

    workspace_config = workspace_root / ".mcp.json"
    drifted = json.loads(workspace_config.read_text(encoding="utf-8"))
    drifted["mcpServers"]["filesystem"]["args"][-1] = "unexpected-scope"
    workspace_config.write_text(json.dumps(drifted), encoding="utf-8")

    repaired = subprocess.run(
        ["bash", ensure_script, "--ensure"],
        cwd=bash_root,
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert repaired.returncode == 0, repaired.stderr
    assert "[mcp] MCP config is ready (refreshed)" in repaired.stdout
    repaired_payload = json.loads(workspace_config.read_text(encoding="utf-8"))
    assert repaired_payload["mcpServers"]["filesystem"]["args"][-1] == "."
