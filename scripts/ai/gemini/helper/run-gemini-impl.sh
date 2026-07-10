#!/usr/bin/env bash
# Helper: Launch Gemini CLI.
# Called by: run-gemini.sh/run-gemini.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Resolve REPO_ROOT with WSL path conversion
if [[ -n "${REPO_ROOT:-}" ]]; then
    # If REPO_ROOT is set, convert Windows path to WSL if needed
    if [[ "$REPO_ROOT" =~ ^[A-Za-z]: ]]; then
        # Convert E:\path to /mnt/e/path
        REPO_ROOT="$(echo "$REPO_ROOT" | sed 's/^\([A-Za-z]\):/\/mnt\/\L\1/' | sed 's/\\/\//g')"
    fi
else
    # Auto-detect repo root and convert to WSL path
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))"
    if [[ "$REPO_ROOT" =~ ^[A-Za-z]: ]]; then
        REPO_ROOT="$(echo "$REPO_ROOT" | sed 's/^\([A-Za-z]\):/\/mnt\/\L\1/' | sed 's/\\/\//g')"
    fi
fi

ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-gemini-cli.sh"
ENSURE_MCP_SCRIPT="${SCRIPT_DIR}/ensure-mcp.sh"

ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

SHARED_WSL_PROXY_ENV="${REPO_ROOT}/scripts/engineering/dev/bash/.wsl_proxy_env.sh"
if [[ -f "${SHARED_WSL_PROXY_ENV}" ]]; then
    source "${SHARED_WSL_PROXY_ENV}" 2>/dev/null || true
fi

# Windows IDE workspace paths contain drive-letter colons (for example E:\...),
# which Gemini CLI under Linux treats as path separators and may resolve as ./E.
unset GEMINI_CLI_IDE_WORKSPACE_PATH

if [[ -z "${GEMINI_API_KEY:-}" ]] || [[ "${GEMINI_API_KEY}" == "your-api-key-here" ]]; then
    echo "[ERROR] GEMINI_API_KEY not set or invalid in ${ENV_FILE}" >&2
    echo "[INFO] Please edit .env.gemini and add your API key from: https://aistudio.google.com/app/apikeys" >&2
    exit 1
fi

if [[ ! -x "${ENSURE_SCRIPT}" ]]; then
    echo "[ERROR] Gemini bootstrap helper not found: ${ENSURE_SCRIPT}" >&2
    exit 1
fi

GEMINI_BIN=""
GEMINI_PREFIX=""
if timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin >/dev/null 2>&1; then
    GEMINI_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || echo "")"
    GEMINI_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --no-install --print-prefix 2>/dev/null || echo "")"
fi

if [[ -z "${GEMINI_BIN}" ]]; then
    echo "[INFO] Gemini CLI not found, attempting installation..." >&2
    if timeout 120 "${ENSURE_SCRIPT}" --ensure >/dev/null 2>&1; then
        GEMINI_BIN="$(timeout 10 "${ENSURE_SCRIPT}" --print-bin 2>/dev/null || echo "")"
        GEMINI_PREFIX="$(timeout 10 "${ENSURE_SCRIPT}" --print-prefix 2>/dev/null || echo "")"
    fi
fi

GEMINI_HOME="$(cd "${GEMINI_PREFIX}/.." && pwd)/home"
echo "[INFO] Using Gemini CLI from managed prefix: ${GEMINI_BIN}"

if [[ -z "${GEMINI_BIN}" ]] || [[ ! -x "${GEMINI_BIN}" ]]; then
    echo "[ERROR] Gemini CLI binary not found" >&2
    echo "[INFO] Try running: bash ${ENSURE_SCRIPT} --ensure" >&2
    exit 1
fi

export GEMINI_API_KEY
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
export GEMINI_CLI_HOME="${GEMINI_CLI_HOME:-${GEMINI_HOME}}"
export NPM_CONFIG_PREFIX="${GEMINI_PREFIX}"
export npm_config_prefix="${GEMINI_PREFIX}"
export PATH="${GEMINI_PREFIX}/bin:/usr/local/bin:${PATH}"

mkdir -p "${GEMINI_CLI_HOME}"

if [[ "${GEMINI_SKIP_MCP_SETUP:-0}" != "1" ]]; then
    echo "[INFO] Synchronizing Gemini MCP config (timeout: 60s)"
    if [[ ! -x "${ENSURE_MCP_SCRIPT}" ]]; then
        echo "[ERROR] Gemini MCP setup helper not found: ${ENSURE_MCP_SCRIPT}" >&2
        exit 1
    fi
    if ! timeout 60 "${ENSURE_MCP_SCRIPT}" \
        --ensure \
        --gemini-bin "${GEMINI_BIN}" \
        --gemini-prefix "${GEMINI_PREFIX}" >/dev/null 2>&1; then
        echo "[WARN] MCP setup timed out or failed, continuing anyway" >&2
    else
        echo "[INFO] MCP configuration synchronized"
    fi
fi

cd "${REPO_ROOT}"

GEMINI_ARGS=("$@")
HAS_INCLUDE_DIRECTORIES=0
for arg in "${GEMINI_ARGS[@]}"; do
    if [[ "${arg}" == "--include-directories" ]]; then
        HAS_INCLUDE_DIRECTORIES=1
        break
    fi
done

if [[ "${HAS_INCLUDE_DIRECTORIES}" == "0" ]]; then
    GEMINI_ARGS=("--include-directories=${REPO_ROOT}" "${GEMINI_ARGS[@]}")
fi

exec "${GEMINI_BIN}" "${GEMINI_ARGS[@]}"
