"""Architecture checks for consolidated Copilot/Codex MCP setup wrappers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _posix(path_str: str) -> str:
    return path_str.replace("\\", "/")


def _load_workspace_mcp_config(
    root: Path, tmp_path: Path
) -> tuple[dict[str, object], Path]:
    """Load generated config when backend works, else fall back to committed artifact."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/engineering/dev/setup_copilot_codex_mcp.py",
            "--root",
            str(tmp_path),
            "--skip-codex",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        mcp_path = tmp_path / ".vscode" / "mcp.json"
        assert mcp_path.exists()
        return json.loads(mcp_path.read_text(encoding="utf-8")), tmp_path

    committed_path = root / ".vscode" / "mcp.json"
    assert committed_path.exists(), result.stderr
    return json.loads(committed_path.read_text(encoding="utf-8")), root


def test_setup_backend_writes_expected_vscode_mcp_config(tmp_path: Path) -> None:
    """Workspace MCP config should match the canonical server layout."""
    root = _project_root()
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
    assert _posix(servers["filesystem"]["args"][-1]).endswith(
        "/BioactivityDataAcquisition2"
    )
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
        assert servers["github"]["command"] == "powershell"
        assert "scripts/ai/mcp" in servers["github"]["args"][-1]
        assert "github-mcp-wrapper.ps1" in servers["github"]["args"][-1]
        assert servers["docker"]["command"] == "powershell"
        assert servers["docker-docs"]["command"] == "powershell"
        assert servers["context7"]["command"] == "powershell"
        assert servers["paper-search"]["command"] == "powershell"
        assert servers["dockerhub"]["command"] == "powershell"
        assert servers["prometheus"]["command"] == "powershell"
        assert servers["grafana"]["command"] == "powershell"
        assert servers["brave-search"]["command"] == "powershell"
        assert servers["sonarqube"]["command"] == "powershell"
        assert servers["neo4j-cypher"]["command"] == "powershell"
        assert servers["neo4j-memory"]["command"] == "powershell"
        assert "mcp_docker_wrapper.ps1" in servers["docker"]["args"][-1]
        assert "mcp_docker_docs_wrapper.ps1" in servers["docker-docs"]["args"][-1]
        assert "mcp_context7_wrapper.ps1" in servers["context7"]["args"][-1]
        assert "mcp_paper_search_wrapper.ps1" in servers["paper-search"]["args"][-1]
        assert "mcp_dockerhub_wrapper.ps1" in servers["dockerhub"]["args"][-1]
        assert "mcp_prometheus_wrapper.ps1" in servers["prometheus"]["args"][-1]
        assert "mcp_grafana_wrapper.ps1" in servers["grafana"]["args"][-1]
        assert "mcp_brave_search_wrapper.ps1" in servers["brave-search"]["args"][-1]
        assert "mcp_sonarqube_wrapper.ps1" in servers["sonarqube"]["args"][-1]
        assert "mcp_neo4j_cypher_wrapper.ps1" in servers["neo4j-cypher"]["args"][-1]
        assert "wrapper.ps1" in servers["neo4j-memory"]["args"][-1]
    else:
        assert servers["github"]["command"] == "bash"
        assert servers["github"]["args"][-1].endswith(
            "scripts/ai/mcp/github-mcp-wrapper.sh"
        )
        assert servers["docker"]["command"] == "bash"
        assert servers["docker-docs"]["command"] == "bash"
        assert servers["context7"]["command"] == "bash"
        assert servers["paper-search"]["command"] == "bash"
        assert servers["dockerhub"]["command"] == "bash"
        assert servers["prometheus"]["command"] == "bash"
        assert servers["grafana"]["command"] == "bash"
        assert servers["brave-search"]["command"] == "bash"
        assert servers["sonarqube"]["command"] == "bash"
        assert servers["neo4j-cypher"]["command"] == "bash"
        assert servers["neo4j-memory"]["command"] == "bash"
        assert servers["docker"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_docker_wrapper.sh"
        )
        assert servers["docker-docs"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_docker_docs_wrapper.sh"
        )
        assert servers["context7"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_context7_wrapper.sh"
        )
        assert servers["paper-search"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_paper_search_wrapper.sh"
        )
        assert servers["dockerhub"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_dockerhub_wrapper.sh"
        )
        assert servers["prometheus"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_prometheus_wrapper.sh"
        )
        assert servers["grafana"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_grafana_wrapper.sh"
        )
        assert servers["brave-search"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_brave_search_wrapper.sh"
        )
        assert servers["sonarqube"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_sonarqube_wrapper.sh"
        )
        assert servers["neo4j-cypher"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_neo4j_cypher_wrapper.sh"
        )
        assert servers["neo4j-memory"]["args"][-1].endswith(
            "scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh"
        )
    assert servers["openaiDeveloperDocs"]["type"] == "http"
    assert servers["openaiDeveloperDocs"]["url"] == "https://developers.openai.com/mcp"


def test_setup_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/engineering/dev/setup_copilot_codex_mcp.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/setup_copilot_codex_mcp.py" in content


def test_setup_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/engineering/dev/setup_copilot_codex_mcp.ps1").read_text(
        encoding="utf-8"
    )
    assert "scripts/engineering/dev/setup_copilot_codex_mcp.py" in content


def test_github_mcp_wrappers_load_repo_env() -> None:
    """GitHub MCP wrappers should load repo .env before fallback auth."""
    root = _project_root()
    sh_content = (root / "scripts/ai/mcp/github-mcp-wrapper.sh").read_text(
        encoding="utf-8"
    )
    ps_content = (root / "scripts/ai/mcp/github-mcp-wrapper.ps1").read_text(
        encoding="utf-8"
    )

    assert "load_repo_env.sh" in sh_content
    assert "load_repo_env.ps1" in ps_content
