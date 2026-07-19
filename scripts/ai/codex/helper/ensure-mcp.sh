#!/usr/bin/env bash
# Helper: keep Codex MCP config synchronized before launching Codex.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"
SETUP_MCP="${ROOT_DIR}/setup_mcp.py"

MODE="ensure"
CODEX_BIN="${CODEX_BIN:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)
            MODE="check"
            shift
            ;;
        --ensure)
            MODE="ensure"
            shift
            ;;
        --codex-bin)
            CODEX_BIN="${2:-}"
            shift 2
            ;;
        *)
            echo "[mcp] ERROR: Unsupported argument: $1" >&2
            exit 2
            ;;
    esac
done

fail() {
    echo "[mcp] ERROR: $*" >&2
    exit 1
    return 1
}

warn() {
    echo "[mcp] WARN: $*" >&2
    return 0
}

check_workspace_mcp_config() {
    local path="$1"
    [[ -f "${path}" ]] || fail "Missing MCP config: ${path}"
    python3 - "${path}" <<'PY' || fail "Workspace MCP config is not portable/repo-relative: ${path}"
import json
import os
import re
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
payload = json.loads(config_path.read_text(encoding="utf-8"))
servers = payload.get("mcpServers") or payload.get("servers")
if not isinstance(servers, dict):
    raise SystemExit("missing MCP server mapping")

errors: list[str] = []

filesystem_args = servers.get("filesystem", {}).get("args", [])
if not filesystem_args or filesystem_args[-1] != ".":
    errors.append("filesystem scope must be repo-relative '.'")

fetch_args = servers.get("fetch", {}).get("args", [])
expected_fetch_args = [
    "--python",
    "3.13",
    "--from",
    "mcp-server-fetch==2025.4.7",
    "mcp-server-fetch",
]
if fetch_args != expected_fetch_args:
    errors.append("fetch must use pinned CPython 3.13 and mcp-server-fetch 2025.4.7")

memory_env = servers.get("memory", {}).get("env", {})
if memory_env.get("MEMORY_FILE_PATH") != "docs/00-project/ai/memory/mcp-memory.json":
    errors.append("memory file path must be repo-relative docs/00-project/ai/memory/mcp-memory.json")

suffix = ".ps1" if os.name == "nt" else ".sh"
wrapper_stems = {
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
removed_server_names = {
    "sonarqube",
    "chembl",
    "pubchem",
    "pubmed",
    "sequential-thinking",
    "openaiDeveloperDocs",
    "needle",
    "docker-docs",
    "dockerhub",
    "pdf",
    "paper-search",
}
retired_present = sorted(removed_server_names.intersection(servers))
if retired_present:
    joined_retired = ", ".join(retired_present)
    errors.append(f"retired MCP servers must not be registered: {joined_retired}")

for server_name, stem in wrapper_stems.items():
    args = servers.get(server_name, {}).get("args", [])
    expected = f"scripts/ai/mcp/{stem}{suffix}"
    if not args or args[0] != expected:
        errors.append(f"{server_name} wrapper must be {expected!r}")

portable_path_values = [
    str(filesystem_args[-1]) if filesystem_args else "",
    str(memory_env.get("MEMORY_FILE_PATH", "")),
]
for server in servers.values():
    if isinstance(server, dict):
        env = server.get("env", {})
        if isinstance(env, dict):
            for key in ("NPM_CONFIG_CACHE", "UV_CACHE_DIR", "UV_TOOL_DIR"):
                if key in env:
                    portable_path_values.append(str(env[key]))
        args = server.get("args", [])
        if isinstance(args, list):
            portable_path_values.extend(
                str(arg) for arg in args if isinstance(arg, str) and arg.startswith(("scripts/", ".cache/", "."))
            )

for value in portable_path_values:
    if Path(value).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
        errors.append(f"path is not repo-relative: {value}")

if errors:
    raise SystemExit("\n".join(errors))
PY
    return 0
}

check_codex_config() {
    local config_path="${HOME}/.codex/config.toml"
    [[ -f "${config_path}" ]] || fail "Missing Codex config: ${config_path}"
    grep -Eq '^\[mcp_servers\.filesystem\]' "${config_path}" || fail "Codex config has no filesystem MCP server"
    grep -Eq '^\[mcp_servers\.memory\]' "${config_path}" || fail "Codex config has no memory MCP server"
    grep -Fq "${REPO_ROOT}" "${config_path}" || fail "Codex config does not reference current repo: ${config_path}"
    return 0
}

validate_codex_mcp_list() {
    if [[ "${CODEX_VALIDATE_MCP_LIST:-0}" != "1" ]]; then
        return 0
    fi

    if [[ -z "${CODEX_BIN}" || ! -x "${CODEX_BIN}" ]]; then
        warn "Skipping 'codex mcp list' validation because CODEX_BIN is unavailable"
        return 0
    fi

    local timeout_seconds="${CODEX_MCP_CHECK_TIMEOUT:-15}"
    if ! timeout "${timeout_seconds}" "${CODEX_BIN}" mcp list --json >/dev/null; then
        if [[ "${CODEX_REQUIRE_MCP_LIST:-0}" == "1" ]]; then
            fail "'codex mcp list --json' failed or timed out after ${timeout_seconds}s"
        fi
        warn "'codex mcp list --json' failed or timed out; config files were still synchronized"
    fi
    return 0
}

if [[ ! -f "${SETUP_MCP}" ]]; then
    fail "MCP setup script not found: ${SETUP_MCP}"
fi

case "${MODE}" in
    ensure)
        # Add 15-second timeout (stricter) to prevent hanging on Python script
        # Skip validation (codex mcp list) which can hang on slow systems
        timeout 15 python3 "${SETUP_MCP}" \
            --root "${REPO_ROOT}" \
            --workspace-root "${REPO_ROOT}" \
            --skip-codex-validation \
            --skip-gemini-settings >/dev/null 2>&1 || \
        warn "MCP setup timed out or failed; config may be incomplete"
        ;;
    check)
        ;;
    *)
        fail "Unsupported MCP mode: ${MODE}"
        ;;
esac

check_workspace_mcp_config "${REPO_ROOT}/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/scripts/ai/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.vscode/mcp.json"
if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
    check_workspace_mcp_config "${REPO_ROOT}/.cursor/mcp.json"
fi
check_codex_config
validate_codex_mcp_list

echo "[mcp] MCP config is ready"
