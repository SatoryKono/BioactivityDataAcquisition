#!/usr/bin/env python3
"""Canonical entrypoint for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
FETCH_SPEC = ["--from", "mcp-server-fetch==2025.4.7", "mcp-server-fetch"]


def _wrapper_command(script_name: str, workspace_root: Path) -> dict[str, Any]:
    wrapper = workspace_root / "scripts/ai/mcp" / script_name
    if os.name == "nt":
        return {
            "command": "powershell",
            "args": [
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                wrapper.with_suffix(".ps1").as_posix(),
            ],
        }
    return {"command": "bash", "args": [str(wrapper.with_suffix(".sh"))]}


def _canonical_servers(workspace_root: Path) -> dict[str, dict[str, Any]]:
    memory_file_path = workspace_root / "docs/00-project/ai/memory/mcp-memory.json"
    npm_cache_dir = str((workspace_root / ".cache" / "npm-cache").resolve())
    servers: dict[str, dict[str, Any]] = {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
            "env": {
                "MEMORY_FILE_PATH": str(memory_file_path),
                "NPM_CONFIG_CACHE": npm_cache_dir,
            },
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem@2026.1.14",
                str(workspace_root),
            ],
            "env": {"NPM_CONFIG_CACHE": npm_cache_dir},
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2025.12.18"],
            "env": {"NPM_CONFIG_CACHE": npm_cache_dir},
        },
        "fetch": {"command": "uvx", "args": FETCH_SPEC},
        "pdf": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-pdf@1.3.1", "--stdio"],
            "env": {"NPM_CONFIG_CACHE": npm_cache_dir},
        },
        "github": _wrapper_command("github-mcp-wrapper", workspace_root),
        "docker": _wrapper_command("mcp_docker_wrapper", workspace_root),
        "docker-docs": _wrapper_command("mcp_docker_docs_wrapper", workspace_root),
        "context7": _wrapper_command("mcp_context7_wrapper", workspace_root),
        "paper-search": _wrapper_command("mcp_paper_search_wrapper", workspace_root),
        "dockerhub": _wrapper_command("mcp_dockerhub_wrapper", workspace_root),
        "prometheus": _wrapper_command("mcp_prometheus_wrapper", workspace_root),
        "grafana": _wrapper_command("mcp_grafana_wrapper", workspace_root),
        "brave-search": _wrapper_command("mcp_brave_search_wrapper", workspace_root),
        "sonarqube": _wrapper_command("mcp_sonarqube_wrapper", workspace_root),
        "neo4j-cypher": _wrapper_command("mcp_neo4j_cypher_wrapper", workspace_root),
        "neo4j-memory": _wrapper_command("mcp_neo4j_memory_wrapper", workspace_root),
        "needle": _wrapper_command("mcp_needle_wrapper", workspace_root),
        "openaiDeveloperDocs": {
            "type": "http",
            "url": "https://developers.openai.com/mcp",
        },
    }

    # Preserve the committed config shape where the GitHub wrapper receives npm cache.
    servers["github"]["env"] = {"NPM_CONFIG_CACHE": npm_cache_dir}
    return servers


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    path.write_text(rendered, encoding="utf-8")


def _write_configs(output_root: Path, workspace_root: Path) -> tuple[Path, Path]:
    servers = _canonical_servers(workspace_root)
    codex_payload = {"mcpServers": deepcopy(servers)}
    vscode_payload = {"servers": deepcopy(servers)}

    mcp_path = output_root / ".mcp.json"
    vscode_path = output_root / ".vscode" / "mcp.json"
    _write_json(mcp_path, codex_payload)
    _write_json(vscode_path, vscode_payload)
    return mcp_path, vscode_path


def _run_codex_validation(workspace_root: Path) -> None:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("codex CLI not found; wrote workspace configs only.")
        return
    result = subprocess.run(
        [codex_bin, "mcp", "list"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"codex mcp list failed after writing configs: {stderr}")
    print("codex mcp list succeeded.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Directory where .mcp.json and .vscode/mcp.json should be written.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=REPO_ROOT,
        help="Workspace directory referenced inside the generated MCP server config.",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip post-write Codex CLI validation.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_root = args.root.resolve()
    workspace_root = args.workspace_root.resolve()
    mcp_path, vscode_path = _write_configs(output_root, workspace_root)
    print(f"Wrote {mcp_path}")
    print(f"Wrote {vscode_path}")

    if not args.skip_codex:
        _run_codex_validation(workspace_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
