#!/usr/bin/env bash
# INTERNAL: Helper: keep Codex MCP config synchronized before launching Codex.
# Called by: run-codex-impl.sh
# DO NOT invoke directly

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

PROFILE_STATE="${REPO_ROOT}/.codex/mcp-profile.json"
if [[ -f "${PROFILE_STATE}" ]]; then
    mapfile -t _mcp_profile_state < <(
        python3 - "${PROFILE_STATE}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(payload.get("profile") or ""))
print(str(payload.get("transport_mode") or ""))
PY
    )
    if [[ -z "${CODEX_MCP_PROFILE:-}" && -n "${_mcp_profile_state[0]:-}" ]]; then
        export CODEX_MCP_PROFILE="${_mcp_profile_state[0]}"
    fi
    if [[ -z "${CODEX_MCP_TRANSPORT_MODE:-}" && -n "${_mcp_profile_state[1]:-}" ]]; then
        export CODEX_MCP_TRANSPORT_MODE="${_mcp_profile_state[1]}"
    fi
fi

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
    local catalog_path="${REPO_ROOT}/scripts/ops/runtime/mcp/shared-servers.json"
    if [[ ! -f "${catalog_path}" ]]; then
        catalog_path="${PACKAGE_ROOT}/scripts/ops/runtime/mcp/shared-servers.json"
    fi
    [[ -f "${path}" ]] || fail "Missing MCP config: ${path}"
    python3 - "${path}" "${catalog_path}" <<'PY' || fail "Workspace MCP config is not portable/repo-relative: ${path}"
import json
import os
import re
import shutil
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
catalog_path = Path(sys.argv[2])
payload = json.loads(config_path.read_text(encoding="utf-8"))
servers = payload.get("mcpServers") or payload.get("servers")
if not isinstance(servers, dict):
    raise SystemExit("missing MCP server mapping")

errors: list[str] = []

memory_entry = servers.get("memory", {})
memory_env = memory_entry.get("env", {})
if not memory_entry.get("url") and memory_env.get("MEMORY_FILE_PATH") != "docs/00-project/ai/memory/mcp-memory.json":
    errors.append("memory file path must be repo-relative docs/00-project/ai/memory/mcp-memory.json")

expected_wrapper_suffixes = (".sh", ".ps1")
wrapper_stems = {
    "memory": "mcp_memory_wrapper",
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

# Shared multi-client plane URLs come from the runtime SSOT.
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
shared_urls = {
    name: f"http://127.0.0.1:{int(entry['port'])}{entry.get('path') or '/mcp'}"
    for name, entry in catalog["servers"].items()
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
# Honor the same profile/transport env overrides used by regeneration below.
# Fall back to setup_mcp daily defaults (stable profile + shared HTTP plane).
import os
profile = (
    os.environ.get("CODEX_MCP_PROFILE")
    or getattr(module, "DEFAULT_LOCAL_PROFILE", "stable")
)
transport_mode = (
    os.environ.get("CODEX_MCP_TRANSPORT_MODE")
    or getattr(module, "DEFAULT_LOCAL_TRANSPORT_MODE", "shared")
)
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

check_local_profile_parity() {
    local check_args=(
        --root "${REPO_ROOT}"
        --workspace-root "${REPO_ROOT}"
        --check-local
    )
    if [[ -n "${CODEX_MCP_PROFILE:-}" ]]; then
        check_args+=(--profile "${CODEX_MCP_PROFILE}")
    fi
    if [[ -n "${CODEX_MCP_TRANSPORT_MODE:-}" ]]; then
        check_args+=(--transport-mode "${CODEX_MCP_TRANSPORT_MODE}")
    fi
    python3 "${SETUP_MCP}" "${check_args[@]}"
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

ensure_shared_plane() {
    if [[ "${CODEX_MCP_ENSURE_SHARED_PLANE:-1}" != "1" ]]; then
        return 0
    fi
    local launcher="${REPO_ROOT}/scripts/ops/runtime/mcp/start-shared.sh"
    local health="${REPO_ROOT}/scripts/ops/runtime/mcp/health-shared.sh"
    local matrix="${REPO_ROOT}/scripts/ai/codex/mcp_profile_contract.py"
    if [[ ! -x "${launcher}" || ! -x "${health}" ]]; then
        warn "Shared MCP launcher/health helper unavailable; config-only ensure"
        return 0
    fi
    local profile="${CODEX_MCP_PROFILE:-stable}"
    if bash "${health}" --profile "${profile}" --no-write >/dev/null 2>&1; then
        return 0
    fi
    if [[ ! -f "${matrix}" ]]; then
        fail "MCP profile contract unavailable: ${matrix}"
    fi
    mapfile -t required_servers < <(
        python3 "${matrix}" --profile "${profile}" --required-local
    )
    if [[ "${#required_servers[@]}" -eq 0 ]]; then
        return 0
    fi
    local timeout_seconds="${CODEX_MCP_SHARED_START_TIMEOUT:-360}"
    timeout "${timeout_seconds}" bash "${launcher}" "${required_servers[@]}" || \
        fail "Shared-plane start phase failed for profile ${profile} within ${timeout_seconds}s; inspect ${REPO_ROOT}/logs/mcp-shared/status.json and per-server *.err.log files"
    bash "${health}" --profile "${profile}" --no-write >/dev/null || \
        fail "Shared-plane health verification phase failed for profile ${profile}; inspect ${REPO_ROOT}/logs/mcp-shared/status.json"
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
        check_workspace_mcp_config "${REPO_ROOT}/.devin/mcp_config.json"
        check_local_profile_parity
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
            ensure_shared_plane
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
    # Defaults must match setup_mcp.DEFAULT_LOCAL_* (stable + shared transport).
    # Override with CODEX_MCP_PROFILE / CODEX_MCP_TRANSPORT_MODE if needed.
    local_profile="${CODEX_MCP_PROFILE:-}"
    local_transport="${CODEX_MCP_TRANSPORT_MODE:-}"
    if [[ -z "${local_profile}" || -z "${local_transport}" ]]; then
        # Resolve from setup_mcp so bash and Python cannot drift.
        mapfile -t _mcp_defaults < <(
            python3 - "${SETUP_MCP}" <<'PY'
import importlib.util
import sys
from pathlib import Path
setup_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("bioetl_setup_mcp", setup_path)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
print(getattr(module, "DEFAULT_LOCAL_PROFILE", "stable"))
print(getattr(module, "DEFAULT_LOCAL_TRANSPORT_MODE", "shared"))
PY
        )
        if [[ -z "${local_profile}" ]]; then
            local_profile="${_mcp_defaults[0]:-stable}"
        fi
        if [[ -z "${local_transport}" ]]; then
            local_transport="${_mcp_defaults[1]:-shared}"
        fi
    fi
    timeout "${local_setup_timeout}" python3 "${SETUP_MCP}" \
        --root "${REPO_ROOT}" \
        --workspace-root "${REPO_ROOT}" \
        --profile "${local_profile}" \
        --transport-mode "${local_transport}" \
        --skip-codex-validation >/dev/null 2>&1 || \
        fail "MCP config materialization phase failed or timed out after ${local_setup_timeout}s"
fi

check_workspace_mcp_config "${REPO_ROOT}/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/scripts/ai/.mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.vscode/mcp.json"
if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
    check_workspace_mcp_config "${REPO_ROOT}/.cursor/mcp.json"
fi
check_workspace_mcp_config "${REPO_ROOT}/.qodo/mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.zed/mcp.json"
check_workspace_mcp_config "${REPO_ROOT}/.devin/mcp_config.json"
check_local_profile_parity
check_codex_config
if [[ "${MODE}" == "ensure" || "${MODE}" == "refresh" ]]; then
    ensure_shared_plane
fi
validate_codex_mcp_list

if [[ "${SHOULD_GENERATE}" -eq 1 ]]; then
    echo "[mcp] MCP config is ready (refreshed)"
else
    echo "[mcp] MCP config is ready"
fi
