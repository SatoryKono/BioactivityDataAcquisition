"""Architecture checks for consolidated Copilot/Codex MCP setup wrappers."""

from __future__ import annotations

import pytest

import json
import os
import re
from pathlib import Path

from tests.helpers import repo_root, run_repo_python


pytestmark = pytest.mark.architecture

EXPECTED_MCP_SERVERS = {
    "memory",
    "filesystem",
    "fetch",
    "github",
    "docker",
    "context7",
    "prometheus",
    "grafana",
    "brave-search",
    "neo4j-cypher",
    "neo4j-memory",
    "mermaid",
    "biomoltechDocs",
    "mintlify",
    "deepwiki",
    "ref",
    "ast-grep",
    "mcp-code-interpreter",
}

WRAPPER_SCRIPT_STEMS = {
    "github": "github-mcp-wrapper",
    "docker": "mcp_docker_wrapper",
    "context7": "mcp_context7_wrapper",
    "ast-grep": "mcp_ast_grep_wrapper",
    "mcp-code-interpreter": "mcp_code_interpreter_wrapper",
    "prometheus": "mcp_prometheus_wrapper",
    "grafana": "mcp_grafana_wrapper",
    "brave-search": "mcp_brave_search_wrapper",
    "neo4j-cypher": "mcp_neo4j_cypher_wrapper",
    "neo4j-memory": "mcp_neo4j_memory_wrapper",
    "mermaid": "mcp_mermaid_wrapper",
}


def _posix(path_str: str) -> str:
    return path_str.replace("\\", "/")


def _all_string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            item for nested in value.values() for item in _all_string_values(nested)
        ]
    if isinstance(value, list):
        return [item for nested in value for item in _all_string_values(nested)]
    return []


def _load_workspace_mcp_config(
    root: Path, tmp_path: Path
) -> tuple[
    dict[str, object], dict[str, object], dict[str, object], dict[str, object], Path
]:
    """Load generated config when backend works, else fall back to committed artifact."""
    gemini_settings_path = tmp_path / ".gemini" / "settings.json"
    gemini_settings_path.parent.mkdir(parents=True)
    gemini_settings_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "sonarqube": {"command": "old"},
                    "chembl": {"command": "old"},
                    "pubchem": {"command": "old"},
                    "pubmed": {"command": "old"},
                    "local-extra": {"command": "kept"},
                }
            }
        ),
        encoding="utf-8",
    )
    result = run_repo_python(
        "-m",
        "scripts.engineering.dev",
        "setup-mcp",
        "--root",
        str(tmp_path),
        "--skip-codex",
        cwd=root,
    )
    if result.returncode == 0:
        vscode_path = tmp_path / ".vscode" / "mcp.json"
        qodo_path = tmp_path / ".qodo" / "mcp.json"
        codex_settings_path = tmp_path / ".codex" / "settings.json"
        assert vscode_path.exists()
        assert qodo_path.exists()
        assert codex_settings_path.exists()
        assert gemini_settings_path.exists()
        return (
            json.loads(vscode_path.read_text(encoding="utf-8")),
            json.loads(qodo_path.read_text(encoding="utf-8")),
            json.loads(codex_settings_path.read_text(encoding="utf-8")),
            json.loads(gemini_settings_path.read_text(encoding="utf-8")),
            tmp_path,
        )

    committed_vscode_path = root / ".vscode" / "mcp.json"
    committed_codex_settings_path = root / ".codex" / "settings.json"
    committed_gemini_settings_path = root / ".gemini" / "settings.json"
    assert committed_vscode_path.exists(), result.stderr
    assert committed_codex_settings_path.exists(), result.stderr
    assert committed_gemini_settings_path.exists(), result.stderr
    committed_qodo_payload = json.loads(
        (root / ".mcp.json").read_text(encoding="utf-8")
    )
    return (
        json.loads(committed_vscode_path.read_text(encoding="utf-8")),
        committed_qodo_payload,
        json.loads(committed_codex_settings_path.read_text(encoding="utf-8")),
        json.loads(committed_gemini_settings_path.read_text(encoding="utf-8")),
        root,
    )


def _assert_shell_wrapper(
    server: dict[str, object],
    shell_name: str,
    expected_suffix: str,
) -> None:
    assert server["command"] in {shell_name, "bash", "powershell"}
    assert _posix(str(server["args"][-1])).endswith(expected_suffix)


def _assert_platform_wrappers(servers: dict[str, object]) -> None:
    shell_name = "powershell" if os.name == "nt" else "bash"
    suffix = ".ps1" if os.name == "nt" else ".sh"

    for server_name, script_stem in WRAPPER_SCRIPT_STEMS.items():
        _assert_shell_wrapper(
            servers[server_name],
            shell_name,
            f"scripts/ai/mcp/{script_stem}{suffix}",
        )


def test_setup_backend_writes_expected_vscode_mcp_config(tmp_path: Path) -> None:
    """Workspace MCP config should match the canonical server layout."""
    root = repo_root()
    payload, qodo_payload, codex_settings, gemini_settings, _config_root = (
        _load_workspace_mcp_config(root, tmp_path)
    )
    servers = payload["servers"]
    codex_servers = codex_settings["mcpServers"]
    assert qodo_payload["mcpServers"] == servers
    assert codex_servers["filesystem"]["args"][-1] != servers["filesystem"]["args"][-1]
    assert "local-extra" in gemini_settings["mcpServers"]
    assert not {
        "sonarqube",
        "chembl",
        "pubchem",
        "pubmed",
    } & set(gemini_settings["mcpServers"])
    assert set(servers) == EXPECTED_MCP_SERVERS
    assert servers["memory"]["command"] == "npx"
    assert (
        servers["memory"]["env"]["MEMORY_FILE_PATH"]
        == "docs/00-project/ai/memory/mcp-memory.json"
    )
    assert _posix(codex_servers["memory"]["env"]["MEMORY_FILE_PATH"]).endswith(
        "/docs/00-project/ai/memory/mcp-memory.json"
    )
    assert servers["filesystem"]["args"][-1] == "."
    filesystem_scope = root / str(servers["filesystem"]["args"][-1])
    assert filesystem_scope.exists()
    assert filesystem_scope.resolve().samefile(root.resolve())
    codex_filesystem_scope = Path(str(codex_servers["filesystem"]["args"][-1]))
    assert codex_filesystem_scope.exists()
    assert codex_filesystem_scope.resolve().samefile(root.resolve())
    assert servers["fetch"]["command"] == "uvx"
    assert servers["fetch"]["args"] == [
        "--from",
        "mcp-server-fetch==2025.4.7",
        "mcp-server-fetch",
    ]
    _assert_platform_wrappers(servers)
    assert servers["biomoltechDocs"]["type"] == "http"
    assert servers["biomoltechDocs"]["url"] == "https://biomoltech.mintlify.app/mcp"
    assert servers["mintlify"]["type"] == "http"
    assert servers["mintlify"]["url"] == "https://mcp.mintlify.com"
    assert servers["deepwiki"]["type"] == "http"
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert servers["ref"]["type"] == "http"
    assert servers["ref"]["url"] == "https://api.ref.tools/mcp"


def test_tracked_mcp_projections_reject_workstation_paths() -> None:
    """Tracked portable MCP projections must be clone-location independent."""
    root = repo_root()
    workspace_payload = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    scripts_payload = json.loads(
        (root / "scripts/ai/.mcp.json").read_text(encoding="utf-8")
    )
    devin_payload = json.loads(
        (root / ".devin/config.json").read_text(encoding="utf-8")
    )

    expected_servers = workspace_payload["mcpServers"]
    assert scripts_payload["mcpServers"] == expected_servers
    assert devin_payload["mcpServers"] == expected_servers
    assert set(devin_payload["mcpServers"]) == EXPECTED_MCP_SERVERS
    assert devin_payload["mcpServers"]["filesystem"]["args"][-1] == "."
    assert devin_payload["devin"]["org_id"]
    assert devin_payload["shell"] == {"setup_complete": True}

    absolute_path = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
    for payload in (workspace_payload, scripts_payload, devin_payload):
        assert not [
            value for value in _all_string_values(payload) if absolute_path.match(value)
        ]


def test_setup_router_is_the_supported_public_entrypoint() -> None:
    """Public MCP setup should be exposed through the dev router only."""
    root = repo_root()
    router = (root / "scripts" / "engineering" / "dev" / "__main__.py").read_text(
        encoding="utf-8"
    )
    assert 'module_command("scripts.ai.codex.setup_mcp")' in router
    assert not (root / "scripts/engineering/dev/setup_copilot_codex_mcp.sh").exists()
    assert not (root / "scripts/engineering/dev/setup_copilot_codex_mcp.ps1").exists()


def test_legacy_setup_command_fails_with_guidance() -> None:
    """Legacy setup command should fail fast with maintained-path guidance."""
    result = run_repo_python("-m", "scripts.engineering.dev", "setup")

    assert result.returncode == 2
    assert "legacy `python -m scripts.engineering.dev setup` command is retired" in (
        result.stderr
    )
    assert "make install" in result.stderr
    assert "setup-mcp" in result.stderr


def test_github_mcp_wrappers_load_repo_env() -> None:
    """GitHub MCP wrappers should load repo .env before fallback auth."""
    root = repo_root()
    sh_content = (root / "scripts/ai/mcp/github-mcp-wrapper.sh").read_text(
        encoding="utf-8"
    )
    ps_content = (root / "scripts/ai/mcp/github-mcp-wrapper.ps1").read_text(
        encoding="utf-8"
    )

    assert "load_repo_env.sh" in sh_content
    assert "load_repo_env.ps1" in ps_content
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in sh_content
    assert "GITHUB_TOKEN" in sh_content
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in ps_content
    assert "GITHUB_TOKEN" in ps_content
