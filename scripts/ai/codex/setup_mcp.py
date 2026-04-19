#!/usr/bin/env python3
"""Canonical entrypoint for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
NPM_CACHE_DIR = "/tmp/npm-cache"
FETCH_SPEC = ["--from", "mcp-server-fetch==2025.4.7", "mcp-server-fetch"]


def _normalize_config_root(raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/")
    if os.name == "nt":
        match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", normalized)
        if match is not None:
            drive = match.group(1).upper()
            suffix = match.group(2)
            return Path(f"{drive}:/{suffix}")
    return Path(raw_path)


def _config_root_hint() -> Path:
    committed_config = REPO_ROOT / ".mcp.json"
    if committed_config.exists():
        try:
            payload = json.loads(committed_config.read_text(encoding="utf-8"))
            filesystem_root = payload["mcpServers"]["filesystem"]["args"][-1]
            return _normalize_config_root(str(filesystem_root))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            pass
    return REPO_ROOT


CONFIG_ROOT = _config_root_hint()
MEMORY_FILE_PATH = CONFIG_ROOT / "docs/00-project/ai/memory/mcp-memory.json"


def _wrapper_command(script_name: str) -> dict[str, Any]:
    wrapper = CONFIG_ROOT / "scripts/ai/mcp" / script_name
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


def _canonical_servers() -> dict[str, dict[str, Any]]:
    servers: dict[str, dict[str, Any]] = {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
            "env": {
                "MEMORY_FILE_PATH": str(MEMORY_FILE_PATH),
                "NPM_CONFIG_CACHE": NPM_CACHE_DIR,
            },
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem@2026.1.14",
                str(CONFIG_ROOT),
            ],
            "env": {"NPM_CONFIG_CACHE": NPM_CACHE_DIR},
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2025.12.18"],
            "env": {"NPM_CONFIG_CACHE": NPM_CACHE_DIR},
        },
        "fetch": {"command": "uvx", "args": FETCH_SPEC},
        "pdf": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-pdf@1.3.1", "--stdio"],
            "env": {"NPM_CONFIG_CACHE": NPM_CACHE_DIR},
        },
        "github": _wrapper_command("github-mcp-wrapper"),
        "docker": _wrapper_command("mcp_docker_wrapper"),
        "docker-docs": _wrapper_command("mcp_docker_docs_wrapper"),
        "context7": _wrapper_command("mcp_context7_wrapper"),
        "paper-search": _wrapper_command("mcp_paper_search_wrapper"),
        "dockerhub": _wrapper_command("mcp_dockerhub_wrapper"),
        "prometheus": _wrapper_command("mcp_prometheus_wrapper"),
        "grafana": _wrapper_command("mcp_grafana_wrapper"),
        "brave-search": _wrapper_command("mcp_brave_search_wrapper"),
        "sonarqube": _wrapper_command("mcp_sonarqube_wrapper"),
        "neo4j-cypher": _wrapper_command("mcp_neo4j_cypher_wrapper"),
        "neo4j-memory": _wrapper_command("mcp_neo4j_memory_wrapper"),
        "openaiDeveloperDocs": {
            "type": "http",
            "url": "https://developers.openai.com/mcp",
        },
    }

    # Preserve the committed config shape where the GitHub wrapper receives npm cache.
    servers["github"]["env"] = {"NPM_CONFIG_CACHE": NPM_CACHE_DIR}
    return servers


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    path.write_text(rendered, encoding="utf-8")


def _write_configs(output_root: Path) -> tuple[Path, Path]:
    servers = _canonical_servers()
    codex_payload = {"mcpServers": deepcopy(servers)}
    vscode_payload = {"servers": deepcopy(servers)}

    mcp_path = output_root / ".mcp.json"
    vscode_path = output_root / ".vscode" / "mcp.json"
    _write_json(mcp_path, codex_payload)
    _write_json(vscode_path, vscode_payload)
    return mcp_path, vscode_path


def _run_codex_validation() -> None:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("codex CLI not found; wrote workspace configs only.")
        return
    result = subprocess.run(
        [codex_bin, "mcp", "list"],
        cwd=CONFIG_ROOT,
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
        default=CONFIG_ROOT,
        help="Directory where .mcp.json and .vscode/mcp.json should be written.",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip post-write Codex CLI validation.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_root = args.root.resolve()
    mcp_path, vscode_path = _write_configs(output_root)
    print(f"Wrote {mcp_path}")
    print(f"Wrote {vscode_path}")

    if not args.skip_codex:
        _run_codex_validation()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
