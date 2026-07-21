#!/usr/bin/env bash
# Compatibility facade for the canonical Codex auto-execution launcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
ENSURE_SCRIPT="${REPO_ROOT}/scripts/ai/codex/helper/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${REPO_ROOT}/scripts/ai/codex/helper/ensure-mcp.sh"
REPO_ENV_LOADER="${REPO_ROOT}/scripts/ai/mcp/support/load_repo_env.sh"

# Only REF reaches the Codex parent process (remote HTTP MCP header source).
# Other MCP wrapper secrets are not exported into this process environment.
if [[ -f "${REPO_ENV_LOADER}" ]]; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
        printf -v "${key}" '%s' "${value}"
        export "${key}"
    done < <(
        (
            # shellcheck source=../../ai/mcp/support/load_repo_env.sh
            source "${REPO_ENV_LOADER}"
            load_repo_env_if_present
            for key in "REF_TOOL_API_KEY"; do
                if [[ -n "${!key:-}" ]]; then
                    printf '%s\0%s\0' "${key}" "${!key}"
                fi
            done
        )
    )
fi

if [[ ! -f "${ENSURE_SCRIPT}" ]]; then
    echo "[codex-exec] ERROR: bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
    exit 1
fi

CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"

if [[ ! -x "${CODEX_BIN}" ]]; then
    "${ENSURE_SCRIPT}" --ensure >/dev/null
    CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
fi

export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${PATH}"

if [[ "${CODEX_SKIP_MCP_SETUP:-0}" != "1" ]]; then
    if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
        echo "[codex-exec] ERROR: MCP setup helper not found: ${ENSURE_MCP_SCRIPT}" >&2
        exit 1
    fi
    if ! timeout 60 "${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${CODEX_BIN}" >/dev/null 2>&1; then
        echo "[codex-exec] WARN: MCP setup timed out or failed, continuing anyway" >&2
    fi
fi

exec "${CODEX_BIN}" exec --full-auto -C "${REPO_ROOT}" "$@"
