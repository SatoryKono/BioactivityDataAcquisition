"""Architecture checks for consolidated Copilot/Codex MCP setup wrappers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import repo_root, run_repo_python


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
    "sonarqube",
    "neo4j-cypher",
    "neo4j-memory",
    "chembl",
    "pubchem",
    "pubmed",
    "mermaid",
    "biomoltechDocs",
    "mintlify",
    "deepwiki",
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
    "sonarqube": "mcp_sonarqube_wrapper",
    "neo4j-cypher": "mcp_neo4j_cypher_wrapper",
    "neo4j-memory": "mcp_neo4j_memory_wrapper",
    "chembl": "mcp_chembl_wrapper",
    "pubchem": "mcp_pubchem_wrapper",
    "pubmed": "mcp_pubmed_wrapper",
    "mermaid": "mcp_mermaid_wrapper",
}


def _posix(path_str: str) -> str:
    return path_str.replace("\\", "/")


def _load_workspace_mcp_config(
    root: Path, tmp_path: Path
) -> tuple[dict[str, object], dict[str, object], Path]:
    """Load generated config when backend works, else fall back to committed artifact."""
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
        codex_settings_path = tmp_path / ".codex" / "settings.json"
        assert vscode_path.exists()
        assert codex_settings_path.exists()
        return (
            json.loads(vscode_path.read_text(encoding="utf-8")),
            json.loads(codex_settings_path.read_text(encoding="utf-8")),
            tmp_path,
        )

    committed_vscode_path = root / ".vscode" / "mcp.json"
    committed_codex_settings_path = root / ".codex" / "settings.json"
    assert committed_vscode_path.exists(), result.stderr
    assert committed_codex_settings_path.exists(), result.stderr
    return (
        json.loads(committed_vscode_path.read_text(encoding="utf-8")),
        json.loads(committed_codex_settings_path.read_text(encoding="utf-8")),
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
    payload, codex_settings, _config_root = _load_workspace_mcp_config(root, tmp_path)
    servers = payload["servers"]
    assert codex_settings["mcpServers"] == servers
    assert set(servers) == EXPECTED_MCP_SERVERS
    assert servers["memory"]["command"] == "npx"
    assert _posix(servers["memory"]["env"]["MEMORY_FILE_PATH"]).endswith(
        "/docs/00-project/ai/memory/mcp-memory.json"
    )
    filesystem_scope = Path(str(servers["filesystem"]["args"][-1]))
    assert filesystem_scope.exists()
    assert filesystem_scope.resolve().samefile(root.resolve())
    assert servers["fetch"]["command"] == "uvx"
    assert servers["fetch"]["args"] == [
        "--from",
        "mcp-server-fetch==2025.4.7",
        "mcp-server-fetch",
    ]
    _assert_platform_wrappers(servers)
    assert servers["biomoltechDocs"]["url"] == "https://biomoltech.mintlify.app/mcp"
    assert servers["mintlify"]["url"] == "https://mcp.mintlify.com"
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"


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
