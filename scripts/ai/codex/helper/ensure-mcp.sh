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

check_file_contains_repo() {
    local path="$1"
    [[ -f "${path}" ]] || fail "Missing MCP config: ${path}"
    grep -Fq "${REPO_ROOT}" "${path}" || fail "MCP config does not reference current repo: ${path}"
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
            --skip-codex \
            --skip-gemini-settings >/dev/null 2>&1 || \
        warn "MCP setup timed out or failed; config may be incomplete"
        ;;
    check)
        ;;
    *)
        fail "Unsupported MCP mode: ${MODE}"
        ;;
esac

check_file_contains_repo "${REPO_ROOT}/.mcp.json"
check_file_contains_repo "${REPO_ROOT}/.vscode/mcp.json"
if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
    check_file_contains_repo "${REPO_ROOT}/.cursor/mcp.json"
fi
check_codex_config
validate_codex_mcp_list

echo "[mcp] MCP config is ready"
