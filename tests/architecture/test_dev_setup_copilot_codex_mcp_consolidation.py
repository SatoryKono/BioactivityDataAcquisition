"""Architecture checks for consolidated Copilot/Codex MCP setup wrappers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import repo_root, run_repo_python


def _posix(path_str: str) -> str:
    return path_str.replace("\\", "/")


def _load_workspace_mcp_config(
    root: Path, tmp_path: Path
) -> tuple[dict[str, object], Path]:
    """Load generated config when backend works, else fall back to committed artifact."""
    result = run_repo_python(
        "scripts/engineering/dev/setup_copilot_codex_mcp.py",
        "--root",
        str(tmp_path),
        "--skip-codex",
        cwd=root,
    )
    if result.returncode == 0:
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        assert mcp_path.exists()
        return json.loads(mcp_path.read_text(encoding="utf-8")), tmp_path

    committed_path = root / ".vscode" / "mcp.json"
    assert committed_path.exists(), result.stderr
    return json.loads(committed_path.read_text(encoding="utf-8")), root


def _assert_shell_wrapper(
    server: dict[str, object],
    shell_name: str,
    expected_suffix: str,
) -> None:
    assert server["command"] in {shell_name, "bash", "powershell"}
    assert str(server["args"][-1]).endswith(expected_suffix)


def test_setup_backend_writes_expected_vscode_mcp_config(tmp_path: Path) -> None:
    """Workspace MCP config should match the canonical server layout."""
    root = repo_root()
    payload, _config_root = _load_workspace_mcp_config(root, tmp_path)
    servers = payload["servers"]
    assert set(servers) == {
        "memory",
        "filesystem",
        "sequential-thinking",
        "fetch",
        "pdf",
        "github",
        "docker",
        "docker-docs",
        "context7",
        "paper-search",
        "dockerhub",
        "prometheus",
        "grafana",
        "brave-search",
        "sonarqube",
        "neo4j-cypher",
        "neo4j-memory",
        "openaiDeveloperDocs",
    }
    assert servers["memory"]["command"] == "npx"
    assert _posix(servers["memory"]["env"]["MEMORY_FILE_PATH"]).endswith(
        "/docs/00-project/ai/memory/mcp-memory.json"
    )
    filesystem_scope = Path(str(servers["filesystem"]["args"][-1]))
    assert filesystem_scope.exists()
    assert filesystem_scope.resolve().samefile(root.resolve())
    assert servers["sequential-thinking"]["args"][1] == (
        "@modelcontextprotocol/server-sequential-thinking@2025.12.18"
    )
    assert servers["fetch"]["command"] == "uvx"
    assert servers["fetch"]["args"] == [
        "--from",
        "mcp-server-fetch==2025.4.7",
        "mcp-server-fetch",
    ]
    assert servers["pdf"]["command"] == "npx"
    assert servers["pdf"]["args"] == [
        "-y",
        "@modelcontextprotocol/server-pdf@1.3.1",
        "--stdio",
    ]
    if os.name == "nt":
        _assert_shell_wrapper(
            servers["github"], "powershell", "scripts/ai/mcp/github-mcp-wrapper.ps1"
        )
        _assert_shell_wrapper(
            servers["docker"], "powershell", "scripts/ai/mcp/mcp_docker_wrapper.ps1"
        )
        _assert_shell_wrapper(
            servers["docker-docs"],
            "powershell",
            "scripts/ai/mcp/mcp_docker_docs_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["context7"],
            "powershell",
            "scripts/ai/mcp/mcp_context7_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["paper-search"],
            "powershell",
            "scripts/ai/mcp/mcp_paper_search_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["dockerhub"],
            "powershell",
            "scripts/ai/mcp/mcp_dockerhub_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["prometheus"],
            "powershell",
            "scripts/ai/mcp/mcp_prometheus_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["grafana"],
            "powershell",
            "scripts/ai/mcp/mcp_grafana_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["brave-search"],
            "powershell",
            "scripts/ai/mcp/mcp_brave_search_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["sonarqube"],
            "powershell",
            "scripts/ai/mcp/mcp_sonarqube_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["neo4j-cypher"],
            "powershell",
            "scripts/ai/mcp/mcp_neo4j_cypher_wrapper.ps1",
        )
        _assert_shell_wrapper(
            servers["neo4j-memory"],
            "powershell",
            "scripts/ai/mcp/mcp_neo4j_memory_wrapper.ps1",
        )
    else:
        _assert_shell_wrapper(
            servers["github"], "bash", "scripts/ai/mcp/github-mcp-wrapper.sh"
        )
        _assert_shell_wrapper(
            servers["docker"], "bash", "scripts/ai/mcp/mcp_docker_wrapper.sh"
        )
        _assert_shell_wrapper(
            servers["docker-docs"],
            "bash",
            "scripts/ai/mcp/mcp_docker_docs_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["context7"], "bash", "scripts/ai/mcp/mcp_context7_wrapper.sh"
        )
        _assert_shell_wrapper(
            servers["paper-search"],
            "bash",
            "scripts/ai/mcp/mcp_paper_search_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["dockerhub"],
            "bash",
            "scripts/ai/mcp/mcp_dockerhub_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["prometheus"],
            "bash",
            "scripts/ai/mcp/mcp_prometheus_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["grafana"], "bash", "scripts/ai/mcp/mcp_grafana_wrapper.sh"
        )
        _assert_shell_wrapper(
            servers["brave-search"],
            "bash",
            "scripts/ai/mcp/mcp_brave_search_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["sonarqube"],
            "bash",
            "scripts/ai/mcp/mcp_sonarqube_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["neo4j-cypher"],
            "bash",
            "scripts/ai/mcp/mcp_neo4j_cypher_wrapper.sh",
        )
        _assert_shell_wrapper(
            servers["neo4j-memory"],
            "bash",
            "scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh",
        )
    assert servers["openaiDeveloperDocs"]["type"] == "http"
    assert servers["openaiDeveloperDocs"]["url"] == "https://developers.openai.com/mcp"


def test_setup_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/setup_copilot_codex_mcp.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/setup_copilot_codex_mcp.py" in content


def test_setup_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = repo_root()
    content = (root / "scripts/engineering/dev/setup_copilot_codex_mcp.ps1").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/setup_copilot_codex_mcp.py" in content


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
