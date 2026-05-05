#!/usr/bin/env bash
# Helper: keep Gemini CLI MCP config synchronized before launching Gemini.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"
SETUP_MCP="${REPO_ROOT}/scripts/ai/codex/setup_mcp.py"
ENSURE_GEMINI="${SCRIPT_DIR}/ensure-gemini-cli.sh"

MODE="ensure"
GEMINI_BIN="${GEMINI_BIN:-}"
GEMINI_PREFIX="${GEMINI_PREFIX:-}"

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
        --gemini-bin)
            GEMINI_BIN="${2:-}"
            shift 2
            ;;
        --gemini-prefix)
            GEMINI_PREFIX="${2:-}"
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

resolve_gemini_runtime() {
    if [[ -x "${ENSURE_GEMINI}" ]]; then
        if [[ -z "${GEMINI_BIN}" ]]; then
            GEMINI_BIN="$("${ENSURE_GEMINI}" --no-install --print-bin 2>/dev/null || true)"
        fi
        if [[ -z "${GEMINI_PREFIX}" ]]; then
            GEMINI_PREFIX="$("${ENSURE_GEMINI}" --no-install --print-prefix 2>/dev/null || true)"
        fi
    fi
    return 0
}

check_workspace_settings() {
    local path="${REPO_ROOT}/.gemini/settings.json"
    [[ -f "${path}" ]] || fail "Missing Gemini workspace settings: ${path}"
    python3 - "$path" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
repo_root = sys.argv[2]
payload = json.loads(path.read_text(encoding="utf-8"))
servers = payload.get("mcpServers")
if not isinstance(servers, dict):
    raise SystemExit("mcpServers is missing or is not an object")
for name in ("memory", "filesystem"):
    if name not in servers:
        raise SystemExit(f"required MCP server is missing: {name}")
rendered = json.dumps(servers, sort_keys=True)
if repo_root not in rendered:
    raise SystemExit("mcpServers does not reference current repository root")
PY
    return 0
}

validate_gemini_mcp_list() {
    if [[ "${GEMINI_VALIDATE_MCP_LIST:-0}" != "1" ]]; then
        return 0
    fi

    if [[ -z "${GEMINI_BIN}" || ! -x "${GEMINI_BIN}" ]]; then
        warn "Skipping 'gemini mcp list' validation because GEMINI_BIN is unavailable"
        return 0
    fi

    local timeout_seconds="${GEMINI_MCP_CHECK_TIMEOUT:-15}"
    local gemini_home="${GEMINI_CLI_HOME:-}"
    if [[ -z "${gemini_home}" && -n "${GEMINI_PREFIX}" ]]; then
        gemini_home="$(cd "${GEMINI_PREFIX}/.." && pwd)/home"
    fi

    local gemini_path="${PATH}"
    if [[ -n "${GEMINI_PREFIX}" ]]; then
        gemini_path="${GEMINI_PREFIX}/bin:${PATH}"
    fi

    if ! GEMINI_CLI_HOME="${gemini_home}" PATH="${gemini_path}" timeout "${timeout_seconds}" "${GEMINI_BIN}" mcp list >/dev/null; then
        if [[ "${GEMINI_REQUIRE_MCP_LIST:-0}" == "1" ]]; then
            fail "'gemini mcp list' failed or timed out after ${timeout_seconds}s"
        fi
        warn "'gemini mcp list' failed or timed out; workspace settings were still synchronized"
    fi
    return 0
}

sync_required_server_enablement() {
    if [[ "${GEMINI_RESPECT_MCP_DISABLES:-0}" == "1" ]]; then
        return 0
    fi

    local gemini_home="${GEMINI_CLI_HOME:-}"
    if [[ -z "${gemini_home}" && -n "${GEMINI_PREFIX}" ]]; then
        gemini_home="$(cd "${GEMINI_PREFIX}/.." && pwd)/home"
    fi
    if [[ -z "${gemini_home}" ]]; then
        return 0
    fi

    local enablement_path="${gemini_home}/.gemini/mcp-server-enablement.json"
    mkdir -p "$(dirname "${enablement_path}")"
    python3 - "${enablement_path}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.exists():
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        payload = {}
else:
    payload = {}

for name in ("memory", "filesystem", "sequential-thinking", "openaiDeveloperDocs"):
    entry = payload.get(name)
    if not isinstance(entry, dict):
        entry = {}
    entry["enabled"] = True
    payload[name] = entry

path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY
    return 0
}

if [[ ! -f "${SETUP_MCP}" ]]; then
    fail "Canonical MCP setup script not found: ${SETUP_MCP}"
fi

resolve_gemini_runtime

case "${MODE}" in
    ensure)
        timeout 30 python3 "${SETUP_MCP}" \
            --root "${REPO_ROOT}" \
            --workspace-root "${REPO_ROOT}" \
            --skip-codex \
            --skip-codex-config >/dev/null 2>&1 || \
        warn "MCP setup timed out; config may be incomplete"
        ;;
    check)
        ;;
    *)
        fail "Unsupported MCP mode: ${MODE}"
        ;;
esac

check_workspace_settings
if [[ "${MODE}" == "ensure" ]]; then
    sync_required_server_enablement
fi
validate_gemini_mcp_list

echo "[mcp] Gemini MCP config is ready"
