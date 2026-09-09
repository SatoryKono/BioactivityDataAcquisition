# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
    "deepwiki",
    "ref",
    "ast-grep",
    "mcp-code-interpreter",
    "deja",
    "adr-analysis",
    "mutmut",
    "code-analyzer",
    "github-actions",
}

WRAPPER_SCRIPT_STEMS = {
    "filesystem": "mcp_filesystem_wrapper",
    "fetch": "mcp_fetch_wrapper",
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
    "deja": "mcp_deja_wrapper",
    "adr-analysis": "mcp_adr_analysis_wrapper",
    "mutmut": "mcp_mutmut_wrapper",
    "code-analyzer": "mcp_code_analyzer_wrapper",
    "github-actions": "mcp_github_actions_wrapper",
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
                    "biomoltechDocs": {"command": "old"},
                    "mintlify": {"command": "old"},
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
        "--profile",
        "full",
        # Path/wrapper assertions require stdio inventory, not shared HTTP rewrite.
        "--transport-mode",
        "stdio",
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
    assert codex_servers["filesystem"]["args"][0] != servers["filesystem"]["args"][0]
    assert "local-extra" in gemini_settings["mcpServers"]
    assert not {
        "sonarqube",
        "chembl",
        "pubchem",
        "pubmed",
        "biomoltechDocs",
        "mintlify",
    } & set(gemini_settings["mcpServers"])
    assert set(servers) == EXPECTED_MCP_SERVERS
    assert servers["memory"]["command"] in {"bash", "powershell"}
    assert servers["memory"]["args"][0].endswith(
        ("mcp_memory_wrapper.sh", "mcp_memory_wrapper.ps1")
    )
    assert (
        servers["memory"]["env"]["MEMORY_FILE_PATH"]
        == "docs/00-project/ai/memory/mcp-memory.json"
    )
    assert _posix(codex_servers["memory"]["env"]["MEMORY_FILE_PATH"]).endswith(
        "/docs/00-project/ai/memory/mcp-memory.json"
    )
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"
    portable_fs_wrapper = f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
    assert servers["filesystem"]["args"][0] == portable_fs_wrapper
    filesystem_wrapper = root / portable_fs_wrapper
    assert filesystem_wrapper.exists()
    codex_filesystem_wrapper = Path(str(codex_servers["filesystem"]["args"][0]))
    assert codex_filesystem_wrapper.exists()
    assert codex_filesystem_wrapper.resolve().samefile(filesystem_wrapper.resolve())
    assert servers["fetch"]["env"] == {
        "UV_CACHE_DIR": ".cache/uv-cache",
        "UV_TOOL_DIR": ".cache/uv-tools",
        "NPM_CONFIG_CACHE": ".cache/npm-cache",
    }
    _assert_platform_wrappers(servers)
    assert servers["deepwiki"]["type"] == "http"
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert servers["ref"]["type"] == "http"
    assert servers["ref"]["url"] == "https://api.ref.tools/mcp"
    assert servers["deja"]["env"]["NPM_CONFIG_CACHE"] == ".cache/npm-cache"
    assert servers["adr-analysis"]["env"] == {
        "PROJECT_PATH": ".",
        "ADR_PATH": "docs/02-architecture/decisions",
    }
    assert servers["mutmut"]["env"]["MUTMUT_PROJECT_PATH"] == "."
    assert servers["code-analyzer"]["env"]["PROJECT_PATH"] == "."


def test_devin_mcp_servers_are_subset_of_sanctioned_inventory() -> None:
    """Tracked Devin MCP keys must stay within the sanctioned full inventory (#6666)."""
    root = repo_root()
    from scripts.ai.codex import setup_mcp

    portable = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    devin = json.loads((root / ".devin/mcp_config.json").read_text(encoding="utf-8"))
    portable_names = set(portable["mcpServers"])
    devin_names = set(devin["mcpServers"])

    assert portable_names == EXPECTED_MCP_SERVERS
    assert devin_names <= portable_names
    assert devin_names == portable_names
    assert not (devin_names & setup_mcp.REMOVED_MCP_SERVER_NAMES)

    allowed_remote = setup_mcp.APPROVED_REMOTE_MCP_BASE_URLS
    for name, entry in devin["mcpServers"].items():
        url = entry.get("url", "")
        if isinstance(url, str) and url.startswith("https://"):
            assert url in allowed_remote, (
                f"unexpected remote MCP host for {name}: {url}"
            )
        elif isinstance(url, str) and url.startswith("http://"):
            assert url.startswith(("http://127.0.0.1:", "http://localhost:")), (
                f"non-localhost HTTP MCP for {name}: {url}"
            )


def test_tracked_mcp_projections_reject_workstation_paths() -> None:
    """Tracked portable MCP projections must be clone-location independent."""
    from scripts.ai.codex import setup_mcp

    root = repo_root()
    workspace_payload = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    scripts_payload = json.loads(
        (root / "scripts/ai/.mcp.json").read_text(encoding="utf-8")
    )
    zed_payload = json.loads((root / ".zed/mcp.json").read_text(encoding="utf-8"))
    devin_settings = json.loads(
        (root / ".devin/config.json").read_text(encoding="utf-8")
    )
    devin_payload = json.loads(
        (root / ".devin/mcp_config.json").read_text(encoding="utf-8")
    )

    expected_servers = workspace_payload["mcpServers"]
    assert scripts_payload["mcpServers"] == expected_servers
    assert zed_payload["mcpServers"] == expected_servers
    devin_servers = devin_payload["mcpServers"]
    assert set(devin_servers) == set(expected_servers)
    assert devin_payload == setup_mcp._render_devin_mcp_payload(root)
    shared_catalog = json.loads(
        (root / "scripts/ops/runtime/mcp/shared-servers.json").read_text(
            encoding="utf-8"
        )
    )["servers"]
    for server_name, entry in shared_catalog.items():
        server = devin_servers[server_name]
        assert server["url"] == f"http://127.0.0.1:{entry['port']}{entry['path']}"
        assert set(server) == {"url"}
    assert devin_servers["deepwiki"]["headers"] == {
        "x-deepwiki-api-key": "${env:DEEPWIKI_API_KEY}",
        "x-deepwiki-organisation-id": "${env:DEEPWIKI_ORGANISATION_ID}",
    }
    assert devin_servers["ref"]["headers"] == {
        "x-ref-api-key": "${env:REF_TOOL_API_KEY}"
    }
    assert set(devin_payload["mcpServers"]) == EXPECTED_MCP_SERVERS
    assert set(devin_settings) <= {
        "version",
        "permissions",
        "read_config_from",
        "hooks",
    }
    assert devin_settings["permissions"]["ask"] == [
        "Read(**/.env*)",
        "Write(**/.env*)",
    ]
    assert devin_settings["read_config_from"]["agents_standard"] is True

    absolute_path = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
    for payload in (
        workspace_payload,
        scripts_payload,
        zed_payload,
        devin_settings,
        devin_payload,
    ):
        assert not [
            value for value in _all_string_values(payload) if absolute_path.match(value)
        ]


def test_devin_launch_contract_uses_project_discovery() -> None:
    """The maintained launcher must use current project config discovery."""
    root = repo_root()
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    materializer = (
        root / "scripts/ops/runtime/mcp/apply-shared-to-devin.py"
    ).read_text(encoding="utf-8")

    assert "devin: devin-setup" in makefile
    assert "devin-check: devin-setup" in makefile
    assert "devin-mcp-start:" in makefile
    assert "$(DEVIN) $(DEVIN_ARGS)" in makefile
    assert "--config .devin/config.json" not in makefile
    assert '"mcp_config.local.json"' in materializer
    assert '"config.local.json"' not in materializer


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


def test_remote_mcp_servers_are_in_allowlist() -> None:
    """All remote HTTP MCP servers must be in the approved allowlist."""
    root = repo_root()
    setup_mcp_path = root / "scripts" / "ai" / "codex" / "setup_mcp.py"
    setup_mcp_content = setup_mcp_path.read_text(encoding="utf-8")

    # Extract the allowlist from the setup_mcp.py file
    allowlist_match = re.search(
        r"APPROVED_REMOTE_MCP_BASE_URLS = frozenset\(\s*\{([^}]+)\}\s*\)",
        setup_mcp_content,
        re.DOTALL,
    )
    assert allowlist_match, "APPROVED_REMOTE_MCP_BASE_URLS not found in setup_mcp.py"
    allowlist_urls = {
        url.strip().strip("\"'")
        for url in allowlist_match.group(1).split(",")
        if url.strip()
    }

    # Extract all _http_server calls to get the actual URLs used
    http_server_calls = re.findall(r'_http_server\("([^"]+)"\)', setup_mcp_content)
    actual_urls = set(http_server_calls)

    # Verify all actual URLs are in the allowlist
    unapproved_urls = actual_urls - allowlist_urls
    assert not unapproved_urls, (
        f"Remote MCP server URLs not in approved allowlist: {unapproved_urls}. "
        f"Add these to APPROVED_REMOTE_MCP_BASE_URLS in setup_mcp.py after security review."
    )

    # Verify allowlist is not empty (security guardrail)
    assert allowlist_urls, "APPROVED_REMOTE_MCP_BASE_URLS must not be empty"


def test_unapproved_remote_mcp_url_rejected() -> None:
    """Attempting to add an unapproved remote MCP URL should raise ValueError."""
    from scripts.ai.codex import setup_mcp

    with pytest.raises(ValueError) as exc_info:
        setup_mcp._http_server("https://unapproved.example.com/mcp")

    assert "not in approved allowlist" in str(exc_info.value)
    assert "https://unapproved.example.com/mcp" in str(exc_info.value)
