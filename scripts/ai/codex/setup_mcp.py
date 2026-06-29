#!/usr/bin/env python3
"""Canonical entrypoint for AI assistant MCP workspace setup."""

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
FETCH_SPEC = ["--from", "mcp-server-fetch==2025.4.7", "mcp-server-fetch"]
MANAGED_BLOCK_BEGIN = "# === BEGIN MANAGED MCP SERVERS ==="
MANAGED_BLOCK_END = "# === END MANAGED MCP SERVERS ==="
CACHE_DIR_NAME = ".cache"


def _wrapper_command(script_name: str, workspace_root: Path) -> dict[str, Any]:
    is_windows = os.name == "nt"
    shell = "powershell" if is_windows else "bash"
    suffix = ".ps1" if is_windows else ".sh"
    wrapper = (workspace_root / "scripts/ai/mcp" / script_name).with_suffix(suffix)
    resolved_wrapper = wrapper.resolve()
    wrapper_arg = str(resolved_wrapper)

    return {"command": shell, "args": [wrapper_arg]}


def _http_server(url: str) -> dict[str, Any]:
    return {"type": "http", "url": url}


def _npx_server(*args: str, npm_cache_dir: str) -> dict[str, Any]:
    return {
        "command": "npx",
        "args": ["-y", *args],
        "env": {"NPM_CONFIG_CACHE": npm_cache_dir},
    }


def _canonical_servers(workspace_root: Path) -> dict[str, dict[str, Any]]:
    workspace_root_str = str(workspace_root)
    memory_file_path = str(
        (workspace_root / "docs/00-project/ai/memory/mcp-memory.json").resolve()
    )
    cache_root = (workspace_root / CACHE_DIR_NAME).resolve()

    npm_cache_dir = str((cache_root / "npm-cache").resolve())
    uv_cache_dir = str((cache_root / "uv-cache").resolve())
    uv_tool_dir = str((cache_root / "uv-tools").resolve())
    servers: dict[str, dict[str, Any]] = {
        "memory": _npx_server(
            "@modelcontextprotocol/server-memory@2026.1.26",
            npm_cache_dir=npm_cache_dir,
        ),
        "filesystem": _npx_server(
            "@modelcontextprotocol/server-filesystem@2026.1.14",
            workspace_root_str,
            npm_cache_dir=npm_cache_dir,
        ),
        "sequential-thinking": _npx_server(
            "@modelcontextprotocol/server-sequential-thinking@2025.12.18",
            npm_cache_dir=npm_cache_dir,
        ),
        "fetch": {
            "command": "uvx",
            "args": FETCH_SPEC,
            "env": {"UV_CACHE_DIR": uv_cache_dir, "UV_TOOL_DIR": uv_tool_dir},
        },
        "pdf": _npx_server(
            "@modelcontextprotocol/server-pdf@1.3.1",
            "--stdio",
            npm_cache_dir=npm_cache_dir,
        ),
        "github": _wrapper_command("github-mcp-wrapper", workspace_root),
        "docker": _wrapper_command("mcp_docker_wrapper", workspace_root),
        "docker-docs": _wrapper_command("mcp_docker_docs_wrapper", workspace_root),
        "context7": _wrapper_command("mcp_context7_wrapper", workspace_root),
        "paper-search": _wrapper_command("mcp_paper_search_wrapper", workspace_root),
        "dockerhub": _wrapper_command("mcp_dockerhub_wrapper", workspace_root),
        "ast-grep": _wrapper_command("mcp_ast_grep_wrapper", workspace_root),
        "mcp-code-interpreter": _wrapper_command(
            "mcp_code_interpreter_wrapper", workspace_root
        ),
        "prometheus": _wrapper_command("mcp_prometheus_wrapper", workspace_root),
        "grafana": _wrapper_command("mcp_grafana_wrapper", workspace_root),
        "brave-search": _wrapper_command("mcp_brave_search_wrapper", workspace_root),
        "sonarqube": _wrapper_command("mcp_sonarqube_wrapper", workspace_root),
        "neo4j-cypher": _wrapper_command("mcp_neo4j_cypher_wrapper", workspace_root),
        "neo4j-memory": _wrapper_command("mcp_neo4j_memory_wrapper", workspace_root),
        "needle": _wrapper_command("mcp_needle_wrapper", workspace_root),
        "chembl": _wrapper_command("mcp_chembl_wrapper", workspace_root),
        "pubchem": _wrapper_command("mcp_pubchem_wrapper", workspace_root),
        "pubmed": _wrapper_command("mcp_pubmed_wrapper", workspace_root),
        "mermaid": _wrapper_command("mcp_mermaid_wrapper", workspace_root),
        "biomoltechDocs": _http_server("https://biomoltech.mintlify.app/mcp"),
        "mintlify": _http_server("https://mcp.mintlify.com"),
        "deepwiki": _http_server("https://mcp.deepwiki.com/mcp"),
        "openaiDeveloperDocs": _http_server("https://developers.openai.com/mcp"),
    }

    # Preserve the committed config shape where the GitHub wrapper receives npm cache.
    servers["github"]["env"] = {"NPM_CONFIG_CACHE": npm_cache_dir}
    servers["memory"]["env"]["MEMORY_FILE_PATH"] = str(memory_file_path)
    return servers


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    path.write_text(rendered, encoding="utf-8")


def _write_workspace_codex_settings(output_root: Path, workspace_root: Path) -> Path:
    settings_path = output_root / ".codex" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        existing = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise ValueError(
                f"Codex workspace settings must be a JSON object: {settings_path}"
            )
    else:
        existing = {}

    existing["mcpServers"] = deepcopy(_canonical_servers(workspace_root))
    _write_json(settings_path, existing)
    return settings_path


def _write_devin_config(output_root: Path, workspace_root: Path) -> Path:
    settings_path = output_root / ".devin" / "config.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        existing = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise ValueError(
                f"Devin workspace config must be a JSON object: {settings_path}"
            )
    else:
        existing = {}

    existing["mcpServers"] = deepcopy(_canonical_servers(workspace_root))
    _write_json(settings_path, existing)
    return settings_path


def _write_configs(
    output_root: Path, workspace_root: Path, *, qodo_only: bool = False
) -> tuple[Path | None, Path | None, Path | None, Path, Path | None, Path | None]:
    servers = _canonical_servers(workspace_root)
    codex_payload = {"mcpServers": deepcopy(servers)}
    vscode_payload = {"servers": deepcopy(servers)}
    qodo_payload = {"mcpServers": deepcopy(servers)}

    mcp_path = output_root / ".mcp.json"
    vscode_path = output_root / ".vscode" / "mcp.json"
    cursor_path = output_root / ".cursor" / "mcp.json"
    qodo_path = output_root / ".qodo" / "mcp.json"
    codex_settings_path: Path | None = None
    devin_config_path: Path | None = None
    if not qodo_only:
        codex_settings_path = _write_workspace_codex_settings(output_root, workspace_root)
        devin_config_path = _write_devin_config(output_root, workspace_root)
        _write_json(mcp_path, codex_payload)
        _write_json(vscode_path, vscode_payload)
        _write_json(cursor_path, codex_payload)
    _write_json(qodo_path, qodo_payload)
    return (
        mcp_path,
        vscode_path,
        cursor_path,
        qodo_path,
        codex_settings_path,
        devin_config_path,
    )


def _gemini_server_config(server: dict[str, Any]) -> dict[str, Any]:
    rendered = deepcopy(server)
    if rendered.get("type") == "http" and "url" in rendered:
        rendered["httpUrl"] = rendered.pop("url")
        rendered.pop("type", None)
    return rendered


def _write_gemini_settings(output_root: Path, workspace_root: Path) -> Path:
    settings_path = output_root / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        existing = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise ValueError(f"Gemini settings must be a JSON object: {settings_path}")
    else:
        existing = {}

    existing_servers = existing.get("mcpServers", {})
    if existing_servers and not isinstance(existing_servers, dict):
        raise ValueError(f"Gemini mcpServers must be a JSON object: {settings_path}")

    merged_servers = dict(existing_servers)
    for name, server in _canonical_servers(workspace_root).items():
        merged_servers[name] = _gemini_server_config(server)

    existing["mcpServers"] = merged_servers
    _write_json(settings_path, existing)
    return settings_path


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return _toml_string(value)


def _toml_array(values: Sequence[Any]) -> str:
    rendered = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(
                f"Only string MCP args are supported in TOML output: {value!r}"
            )
        rendered.append(_toml_string(value))
    return "[" + ", ".join(rendered) + "]"


def _render_codex_mcp_toml(servers: dict[str, dict[str, Any]]) -> str:
    lines = [
        MANAGED_BLOCK_BEGIN,
        "# Generated by scripts/ai/codex/setup_mcp.py. Do not edit this block manually.",
    ]
    for name, server in servers.items():
        key = _toml_key(name)
        lines.append("")
        lines.append(f"[mcp_servers.{key}]")
        if "url" in server:
            lines.append(f"url = {_toml_string(str(server['url']))}")
        else:
            lines.append(f"command = {_toml_string(str(server['command']))}")
            lines.append(f"args = {_toml_array(server.get('args', []))}")

        env = server.get("env")
        if env:
            lines.append("")
            lines.append(f"[mcp_servers.{key}.env]")
            for env_key in sorted(env):
                lines.append(
                    f"{_toml_key(env_key)} = {_toml_string(str(env[env_key]))}"
                )

    lines.append("")
    lines.append(MANAGED_BLOCK_END)
    lines.append("")
    return "\n".join(lines)


def _strip_managed_mcp_blocks(content: str, managed_server_names: set[str]) -> str:
    section_re = re.compile(r"^\[mcp_servers\.([A-Za-z0-9_-]+)(?:\.env)?\]\s*$")
    kept: list[str] = []
    skip = False
    skip_marker_block = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == MANAGED_BLOCK_BEGIN:
            skip_marker_block = True
            skip = False
            continue
        if skip_marker_block:
            if stripped == MANAGED_BLOCK_END:
                skip_marker_block = False
            continue

        section_match = section_re.match(stripped)
        if stripped.startswith("["):
            skip = bool(
                section_match and section_match.group(1) in managed_server_names
            )

        if not skip:
            kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)


def _write_codex_config(workspace_root: Path) -> Path:
    servers = _canonical_servers(workspace_root)
    config_dir = Path.home() / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    preserved = _strip_managed_mcp_blocks(existing, set(servers))
    managed_block = _render_codex_mcp_toml(servers)

    if preserved:
        rendered = preserved.rstrip() + "\n\n" + managed_block
    else:
        rendered = managed_block

    config_path.write_text(rendered, encoding="utf-8")
    return config_path


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
        encoding="utf-8",
        errors="replace",
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
        help=(
            "Directory where .mcp.json, .vscode/mcp.json, .cursor/mcp.json, "
            ".qodo/mcp.json, .codex/settings.json, and .devin/config.json "
            "should be written."
        ),
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
    parser.add_argument(
        "--skip-codex-config",
        action="store_true",
        help="Do not update ~/.codex/config.toml with the generated MCP servers.",
    )
    parser.add_argument(
        "--skip-gemini-settings",
        action="store_true",
        help="Do not update .gemini/settings.json with the generated MCP servers.",
    )
    parser.add_argument(
        "--qodo-only",
        action="store_true",
        help="Write only .qodo/mcp.json and skip Codex/Gemini side effects.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_root = args.root.absolute()
    workspace_root = args.workspace_root.absolute()
    if args.qodo_only:
        args.skip_codex = True
        args.skip_codex_config = True
        args.skip_gemini_settings = True

    (
        mcp_path,
        vscode_path,
        cursor_path,
        qodo_path,
        codex_settings_path,
        devin_config_path,
    ) = _write_configs(output_root, workspace_root, qodo_only=args.qodo_only)
    if mcp_path is not None and not args.qodo_only:
        print(f"Wrote {mcp_path}")
    if vscode_path is not None and not args.qodo_only:
        print(f"Wrote {vscode_path}")
    if cursor_path is not None and not args.qodo_only:
        print(f"Wrote {cursor_path}")
    print(f"Wrote {qodo_path}")
    if codex_settings_path is not None and not args.qodo_only:
        print(f"Wrote {codex_settings_path}")
    if devin_config_path is not None and not args.qodo_only:
        print(f"Wrote {devin_config_path}")
    if not args.skip_codex_config:
        codex_config_path = _write_codex_config(workspace_root)
        print(f"Wrote {codex_config_path}")
    if not args.skip_gemini_settings:
        gemini_settings_path = _write_gemini_settings(output_root, workspace_root)
        print(f"Wrote {gemini_settings_path}")

    if not args.skip_codex:
        _run_codex_validation(workspace_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
