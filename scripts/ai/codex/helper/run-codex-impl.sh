#!/usr/bin/env bash
# INTERNAL: Helper: Launch Codex
# Called by: run-codex.sh, run-codex.ps1
# DO NOT invoke directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(timeout 5 git rev-parse --show-toplevel 2>/dev/null || echo "${SCRIPT_DIR}/../../../..")}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"
ENSURE_MCP_SCRIPT="${SCRIPT_DIR}/ensure-mcp.sh"

# Load optional local API-key env (not required when ChatGPT device auth is present).
ENV_FILE="${ROOT_DIR}/.env.codex"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi

# shellcheck source=codex-auth-lib.sh
source "${SCRIPT_DIR}/codex-auth-lib.sh"

# Ref is a remote HTTP MCP server, so Codex itself must receive the header
# source variable. Load ONLY that key into the Codex parent environment.
# Wrapper-scoped secrets (GitHub, Docker Hub, Neo4j, Grafana, Brave, etc.)
# stay out of this process and are injected by each MCP wrapper via its own env.
REPO_ENV_LOADER="${REPO_ROOT}/scripts/ai/mcp/support/load_repo_env.sh"
if [[ -f "${REPO_ENV_LOADER}" ]]; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
        printf -v "${key}" '%s' "${value}"
        export "${key}"
    done < <(
        (
            # shellcheck source=../../mcp/support/load_repo_env.sh
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

# Accept either OPENAI_API_KEY or persisted ChatGPT tokens from `codex login`.
if ! codex_has_usable_auth; then
    echo "[ERROR] No usable Codex auth found." >&2
    echo "[INFO] Prefer device auth: bash scripts/ai/codex/run-codex.sh device-login" >&2
    echo "[INFO] Or set OPENAI_API_KEY in ${ENV_FILE} (from https://platform.openai.com/api-keys)" >&2
    exit 1
fi
if codex_has_env_api_key; then
    echo "[INFO] Auth: OPENAI_API_KEY"
else
    echo "[INFO] Auth: ChatGPT session ($(codex_auth_file))"
fi

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    echo "[ERROR] Codex bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
    exit 1
fi

# Use timeout on ENSURE_SCRIPT calls
CODEX_BIN=""
CODEX_PREFIX=""
if timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin >/dev/null 2>&1; then
    CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || echo "")"
    CODEX_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-prefix 2>/dev/null || echo "")"
fi

if [[ -z "$CODEX_BIN" ]]; then
    echo "[INFO] Codex binary not found, attempting installation..."
    if timeout 120 "${ENSURE_SCRIPT}" --ensure >/dev/null 2>&1; then
        CODEX_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --print-bin 2>/dev/null || echo "")"
        CODEX_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --print-prefix 2>/dev/null || echo "")"
    fi
fi

echo "[INFO] Using Codex from managed prefix: ${CODEX_BIN}"

# Verify we found it
if [[ -z "$CODEX_BIN" ]] || [[ ! -x "${CODEX_BIN}" ]]; then
    echo "[ERROR] Codex binary not found" >&2
    echo "[INFO] Try running: bash ${ENSURE_SCRIPT} --ensure" >&2
    exit 1
fi

# Setup environment
export NPM_CONFIG_PREFIX="${CODEX_PREFIX}"
export npm_config_prefix="${CODEX_PREFIX}"
export PATH="${CODEX_PREFIX}/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"

# Load shared WSL proxy if available
SHARED_WSL_PROXY_ENV="${REPO_ROOT}/scripts/engineering/dev/bash/.wsl_proxy_env.sh"
if [[ -f "${SHARED_WSL_PROXY_ENV}" ]]; then
    source "${SHARED_WSL_PROXY_ENV}" 2>/dev/null || true
fi

# Verify Codex's persisted native config before launching and repair it only
# when missing or stale. Codex reads ~/.codex/config.toml, not .mcp.json directly.
if [[ "${CODEX_SKIP_MCP_SETUP:-0}" != "1" ]]; then
    if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
        echo "[ERROR] MCP setup helper not found: ${ENSURE_MCP_SCRIPT}" >&2
        exit 1
    fi
    # Bound both the persisted-config verification and any required repair.
    if ! timeout 60 "${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${CODEX_BIN}" >/dev/null 2>&1; then
        echo "[WARN] MCP setup timed out or failed, continuing anyway" >&2
    else
        echo "[INFO] MCP configuration ready"
    fi
fi

# Launch Codex
exec "${CODEX_BIN}" -C "${REPO_ROOT}" "$@"
