#!/usr/bin/env bash
# Helper: keep Codex MCP config synchronized before launching Codex.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Package root always follows this helper's checkout (contains `scripts/` package).
# REPO_ROOT may be overridden in tests to a temp workspace projection.
PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo "${PACKAGE_ROOT}")}"
SETUP_MCP="${ROOT_DIR}/setup_mcp.py"
# setup_mcp imports `scripts.*`; ensure package root is importable even when
# REPO_ROOT points at an ephemeral projection workspace.
export PYTHONPATH="${PACKAGE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

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
        --refresh)
            MODE="refresh"
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
import shutil
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
payload = json.loads(config_path.read_text(encoding="utf-8"))
servers = payload.get("mcpServers") or payload.get("servers")
if not isinstance(servers, dict):
    raise SystemExit("missing MCP server mapping")

errors: list[str] = []

memory_env = servers.get("memory", {}).get("env", {})
if memory_env.get("MEMORY_FILE_PATH") != "docs/00-project/ai/memory/mcp-memory.json":
    errors.append("memory file path must be repo-relative docs/00-project/ai/memory/mcp-memory.json")

expected_wrapper_suffixes = (".sh", ".ps1")
wrapper_stems = {
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
def is_command_available(command: str) -> bool:
    if re.match(r"^[A-Za-z]:[\\/]", command):
        return True
    if "/" in command or "\\" in command:
        return Path(command).exists()
    return shutil.which(command) is not None

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

# Shared multi-client plane URLs (must match setup_mcp.MCP_SHARED_SERVER_ENDPOINTS).
shared_urls = {
    "brave-search": "http://127.0.0.1:8811/mcp",
    "adr-analysis": "http://127.0.0.1:8813/mcp",
    "deja": "http://127.0.0.1:8814/mcp",
    "context7": "http://127.0.0.1:8815/mcp",
    "ast-grep": "http://127.0.0.1:8816/mcp",
    "prometheus": "http://127.0.0.1:8822/mcp",
    "grafana": "http://127.0.0.1:8823/mcp",
}

for server_name, stem in wrapper_stems.items():
    # Profiled local projections may omit high-privilege servers.
    if server_name not in servers:
        continue
    entry = servers[server_name]
    if not isinstance(entry, dict):
        errors.append(f"{server_name} entry must be an object")
        continue
    # Local shared-plane HTTP projections are valid (multi-client).
    url = str(entry.get("url") or "").strip()
    entry_type = str(entry.get("type") or "").strip().lower()
    if url or entry_type == "http":
        expected_url = shared_urls.get(server_name)
        if not expected_url:
            errors.append(f"{server_name} has unapproved shared URL: {url!r}")
            continue
        if url != expected_url:
            errors.append(
                f"{server_name} shared URL must be {expected_url!r}, got {url!r}"
            )
            continue
        continue
    args = entry.get("args", [])
    command = str(entry.get("command", "")).strip()
    expected = tuple(f"scripts/ai/mcp/{stem}{suffix}" for suffix in expected_wrapper_suffixes)
    if not args or args[0] not in expected:
        allowed = " or ".join(repr(path) for path in expected)
        errors.append(f"{server_name} wrapper must be one of: {allowed}")
    if command and not is_command_available(command):
        errors.append(f"{server_name} wrapper command is not on PATH: {command!r}")

portable_path_values = [
    str(memory_env.get("MEMORY_FILE_PATH", "")),
]
for server in servers.values():
    if isinstance(server, dict):
        env = server.get("env", {})
        if isinstance(env, dict):
            for key in (
                "NPM_CONFIG_CACHE",
                "UV_CACHE_DIR",
                "UV_TOOL_DIR",
                "PROJECT_PATH",
                "ADR_PATH",
                "MUTMUT_PROJECT_PATH",
            ):
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
    python3 - "${SETUP_MCP}" "${config_path}" "${REPO_ROOT}" <<'PY' || \
        fail "Codex managed MCP block is missing or stale: ${config_path}"
import importlib.util
import sys
from pathlib import Path

setup_path = Path(sys.argv[1])
config_path = Path(sys.argv[2])
workspace_root = Path(sys.argv[3])

spec = importlib.util.spec_from_file_location("bioetl_setup_mcp", setup_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot load MCP setup module: {setup_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

begin = module.MANAGED_BLOCK_BEGIN
end = module.MANAGED_BLOCK_END
content = config_path.read_text(encoding="utf-8")
if content.count(begin) != 1 or content.count(end) != 1:
    raise SystemExit("managed MCP markers must occur exactly once")

start = content.index(begin)
finish = content.index(end, start) + len(end)
actual = content[start:finish].strip()
# Multi-client daily: shared profile + localhost HTTP plane (see setup_mcp defaults).
profile = getattr(module, "DEFAULT_LOCAL_PROFILE", "shared")
transport_mode = getattr(module, "DEFAULT_LOCAL_TRANSPORT_MODE", "shared")
expected = module._render_codex_mcp_toml(
    module._codex_runtime_servers(
        workspace_root,
        profile=profile,
        transport_mode=transport_mode,
    )
).strip()
if actual != expected:
    raise SystemExit("managed MCP block differs from canonical setup output")
PY
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

current_config_is_ready() {
    # Run structural checks in-process (subshell) instead of re-execing this
    # script. Nested `timeout 15 bash --check` + later `timeout 15 python setup`
    # easily exhausts a 30s pytest budget on slow/WSL filesystems, and
    # re-exec doubles Python/import cold-start cost for no benefit.
    # Live Codex CLI validation stays opt-in via validate_codex_mcp_list.
    (
        check_workspace_mcp_config "${REPO_ROOT}/.mcp.json"
        check_workspace_mcp_config "${REPO_ROOT}/scripts/ai/.mcp.json"
        check_workspace_mcp_config "${REPO_ROOT}/.vscode/mcp.json"
        if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
            check_workspace_mcp_config "${REPO_ROOT}/.cursor/mcp.json"
        fi
        check_workspace_mcp_config "${REPO_ROOT}/.qodo/mcp.json"
        check_workspace_mcp_config "${REPO_ROOT}/.zed/mcp.json"
        check_workspace_mcp_config "${REPO_ROOT}/.devin/config.json"
        check_codex_config
    ) >/dev/null 2>&1
}

if [[ ! -f "${SETUP_MCP}" ]]; then
    fail "MCP setup script not found: ${SETUP_MCP}"
fi

SHOULD_GENERATE=0

case "${MODE}" in
    ensure)
        if current_config_is_ready; then
            validate_codex_mcp_list
            echo "[mcp] MCP config is ready (unchanged)"
            exit 0
        fi
        SHOULD_GENERATE=1
        ;;
    refresh)
        SHOULD_GENERATE=1
        ;;
    check)
        ;;
    *)
        fail "Unsupported MCP mode: ${MODE}"
        ;;
esac

if [[ "${SHOULD_GENERATE}" -eq 1 ]]; then
    # Bound regeneration and skip the potentially slow live CLI check here;
    # the structural checks below still fail closed on incomplete output.
    # 30s: WSL mounts of Windows drives pay high Python cold-start cost.
    local_setup_timeout="${CODEX_MCP_SETUP_TIMEOUT:-30}"
    # Default multi-client plane: shared profile + shared HTTP transport.
    # Override with CODEX_MCP_PROFILE / CODEX_MCP_TRANSPORT_MODE if needed.
    local_profile="${CODEX_MCP_PROFILE:-shared}"
    local_transport="${CODEX_MCP_TRANSPORT_MODE:-shared}"
    timeout "${local_setup_timeout}" python3 "${SETUP_MCP}" \
        --root "${REPO_ROOT}" \
        --workspace-root "${REPO_ROOT}" \
        --profile "${local_profile}" \
        --transport-mode "${local_transport}" \
        --skip-codex-validation \
        --skip-gemini-settings >/dev/null 2>&1 || \
        warn "MCP setup timed out or failed; config may be incomplete"
fi

check_workspace_mcp_config "${REPO_ROOT}/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/scripts/ai/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.vscode/mcp.json"
if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
    check_workspace_mcp_config "${REPO_ROOT}/.cursor/mcp.json"
fi
check_workspace_mcp_config "${REPO_ROOT}/.qodo/mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.zed/mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.devin/config.json"
check_codex_config
validate_codex_mcp_list

if [[ "${SHOULD_GENERATE}" -eq 1 ]]; then
    echo "[mcp] MCP config is ready (refreshed)"
else
    echo "[mcp] MCP config is ready"
fi
