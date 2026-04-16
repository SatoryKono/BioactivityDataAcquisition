#!/usr/bin/env python3
"""Canonical setup backend for Copilot/Codex MCP configuration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NPM_CONFIG_CACHE = "/tmp/npm-cache"
MEMORY_FILE_RELATIVE_PATH = Path("docs/00-project/ai/memory/mcp-memory.json")
OPENAI_DEVELOPER_DOCS_URL = "https://developers.openai.com/mcp"
FETCH_MCP_VERSION = "2025.4.7"
PDF_MCP_VERSION = "1.3.1"

GITHUB_TOKEN_HINT = (
    "GitHub MCP uses GITHUB_PERSONAL_ACCESS_TOKEN from repo .env/.env.local "
    "automatically when present. Shell values still override repo env."
)


def _github_server(root: Path) -> dict[str, object]:
    if os.name != "nt":
        wrapper_path = str((root / ".claude" / "github-mcp-wrapper.sh").resolve())
        return {
            "command": "bash",
            "args": [wrapper_path],
            "env": {"NPM_CONFIG_CACHE": NPM_CONFIG_CACHE},
        }

    if os.name == "nt":
        wrapper_path = str((root / ".claude" / "github-mcp-wrapper.ps1").resolve())
        return {
            "command": "powershell",
            "args": [
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                wrapper_path,
            ],
            "env": {"NPM_CONFIG_CACHE": NPM_CONFIG_CACHE},
        }


def _fetch_server() -> dict[str, object]:
    return {
        "command": "uvx",
        "args": [
            "--from",
            f"mcp-server-fetch=={FETCH_MCP_VERSION}",
            "mcp-server-fetch",
        ],
    }


def _pdf_server() -> dict[str, object]:
    return {
        "command": "npx",
        "args": [
            "-y",
            f"@modelcontextprotocol/server-pdf@{PDF_MCP_VERSION}",
            "--stdio",
        ],
        "env": {"NPM_CONFIG_CACHE": NPM_CONFIG_CACHE},
    }


def _wrapper_server(root: Path, script_name: str) -> dict[str, object]:
    if os.name == "nt":
        ps1_script_path = root / "scripts" / "ops" / f"{Path(script_name).stem}.ps1"
        return {
            "command": "powershell",
            "args": [
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1_script_path.resolve()),
            ],
        }

    script_path = root / "scripts" / "ops" / script_name
    return {"command": "bash", "args": [str(script_path.resolve())]}


def _core_servers(root: Path) -> dict[str, dict[str, object]]:
    memory_file_path = str((root / MEMORY_FILE_RELATIVE_PATH).resolve())
    root_path = str(root)
    return {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
            "env": {
                "MEMORY_FILE_PATH": memory_file_path,
                "NPM_CONFIG_CACHE": NPM_CONFIG_CACHE,
            },
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem@2026.1.14",
                root_path,
            ],
            "env": {"NPM_CONFIG_CACHE": NPM_CONFIG_CACHE},
        },
        "sequential-thinking": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-sequential-thinking@2025.12.18",
            ],
            "env": {"NPM_CONFIG_CACHE": NPM_CONFIG_CACHE},
        },
        "fetch": _fetch_server(),
        "pdf": _pdf_server(),
        "github": _github_server(root),
        "docker": _wrapper_server(root, "mcp_docker_wrapper.sh"),
        "docker-docs": _wrapper_server(root, "mcp_docker_docs_wrapper.sh"),
        "context7": _wrapper_server(root, "mcp_context7_wrapper.sh"),
        "paper-search": _wrapper_server(root, "mcp_paper_search_wrapper.sh"),
        "dockerhub": _wrapper_server(root, "mcp_dockerhub_wrapper.sh"),
        "prometheus": _wrapper_server(root, "mcp_prometheus_wrapper.sh"),
        "grafana": _wrapper_server(root, "mcp_grafana_wrapper.sh"),
        "brave-search": _wrapper_server(root, "mcp_brave_search_wrapper.sh"),
        "sonarqube": _wrapper_server(root, "mcp_sonarqube_wrapper.sh"),
        "neo4j-cypher": _wrapper_server(root, "mcp_neo4j_cypher_wrapper.sh"),
        "neo4j-memory": _wrapper_server(root, "mcp_neo4j_memory_wrapper.sh"),
        "openaiDeveloperDocs": {
            "type": "http",
            "url": OPENAI_DEVELOPER_DOCS_URL,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure core MCP servers for VS Code and Codex CLI."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project root path",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip Codex MCP registration steps",
    )
    return parser


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write keeps MCP config deterministic and avoids partial files.
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def _write_project_configs(root: Path) -> None:
    servers = _core_servers(root)

    vscode_mcp_path = root / ".vscode" / "mcp.json"
    print(f"[1/3] Writing VS Code MCP config: {vscode_mcp_path}")
    _write_json_atomic(vscode_mcp_path, {"servers": servers})

    project_mcp_path = root / ".mcp.json"
    print(f"[2/3] Writing project MCP config: {project_mcp_path}")
    _write_json_atomic(project_mcp_path, {"mcpServers": servers})


def _codex_registration(root: Path) -> int:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("[3/3] Codex CLI not found. Skipping Codex MCP registration.")
        print("[3/3] Done.")
        print(GITHUB_TOKEN_HINT)
        return 0

    print("[3/3] Refreshing Codex MCP registrations")
    for server_name, server_config in _core_servers(root).items():
        subprocess.run(
            [codex_bin, "mcp", "remove", server_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        url = server_config.get("url")
        if isinstance(url, str):
            add_result = subprocess.run(
                [codex_bin, "mcp", "add", server_name, "--url", url],
                check=False,
            )
        else:
            add_command = [codex_bin, "mcp", "add", server_name]
            env = server_config.get("env", {})
            if isinstance(env, dict):
                for env_name, env_value in env.items():
                    add_command.extend(["--env", f"{env_name}={env_value}"])

            command = server_config["command"]
            args = server_config["args"]
            add_result = subprocess.run(
                [*add_command, "--", command, *args],
                check=False,
            )
        if add_result.returncode != 0:
            print(f"[FAIL] Unable to register {server_name} MCP in Codex.")
            return add_result.returncode
        print(f"      {server_name} MCP registered in Codex.")

    print("[3/3] Done.")
    print(GITHUB_TOKEN_HINT)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    _write_project_configs(root)

    if args.skip_codex:
        print("[3/3] Skipping Codex MCP registration (requested).")
        print("[3/3] Done.")
        print(GITHUB_TOKEN_HINT)
        return 0

    return _codex_registration(root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
