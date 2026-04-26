#!/usr/bin/env bash
# Ensure a writable Codex CLI installation for project launchers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"

CODEX_TOOL_HOME_DEFAULT="${REPO_ROOT}/.cache/tools/codex-cli"
CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-${CODEX_TOOL_HOME_DEFAULT}/npm-global}"
CODEX_NPM_CACHE="${CODEX_NPM_CACHE:-${CODEX_TOOL_HOME_DEFAULT}/npm-cache}"
CODEX_BIN="${CODEX_NPM_PREFIX}/bin/codex"
USER_CODEX_PREFIX_DEFAULT="${HOME}/.npm-global"
USER_CODEX_BIN_DEFAULT="${USER_CODEX_PREFIX_DEFAULT}/bin/codex"

MODE="ensure"
PRINT_BIN=0
PRINT_PREFIX=0
ALLOW_INSTALL=1

for arg in "$@"; do
    case "$arg" in
        --ensure)
            MODE="ensure"
            ;;
        --update)
            MODE="update"
            ;;
        --print-bin)
            PRINT_BIN=1
            ;;
        --print-prefix)
            PRINT_PREFIX=1
            ;;
        --no-install)
            ALLOW_INSTALL=0
            ;;
        *)
            echo "[ensure-codex] ERROR: Unsupported argument: $arg" >&2
            exit 2
            ;;
    esac
done

resolve_existing_codex() {
    local path_bin=""
    if [[ -x "${CODEX_BIN}" ]]; then
        CODEX_BIN="${CODEX_BIN}"
        CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX}"
        return 0
    fi

    if [[ -x "${USER_CODEX_BIN_DEFAULT}" ]]; then
        CODEX_BIN="${USER_CODEX_BIN_DEFAULT}"
        CODEX_NPM_PREFIX="${USER_CODEX_PREFIX_DEFAULT}"
        return 0
    fi

    path_bin="$(command -v codex 2>/dev/null || true)"
    if [[ -n "${path_bin}" && -x "${path_bin}" ]]; then
        CODEX_BIN="${path_bin}"
        CODEX_NPM_PREFIX="$(cd "$(dirname "${path_bin}")/.." && pwd)"
        return 0
    fi

    return 1
}

if ! command -v node >/dev/null 2>&1; then
    echo "[ensure-codex] ERROR: Node.js is required but was not found in PATH" >&2
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "[ensure-codex] ERROR: npm is required but was not found in PATH" >&2
    exit 1
fi

if [[ "${MODE}" != "update" ]]; then
    resolve_existing_codex || true
fi

if [[ "${ALLOW_INSTALL}" -eq 1 ]]; then
    mkdir -p "${CODEX_NPM_PREFIX}"
    mkdir -p "${CODEX_NPM_CACHE}"
fi

export NPM_CONFIG_PREFIX="${CODEX_NPM_PREFIX}"
export npm_config_prefix="${CODEX_NPM_PREFIX}"
export NPM_CONFIG_CACHE="${CODEX_NPM_CACHE}"
export npm_config_cache="${CODEX_NPM_CACHE}"
export PATH="${CODEX_NPM_PREFIX}/bin:${PATH}"

need_install=0
if [[ "${MODE}" == "update" || ! -x "${CODEX_BIN}" ]]; then
    need_install=1
fi

if [[ "${need_install}" -eq 1 && "${ALLOW_INSTALL}" -eq 1 ]]; then
    if [[ "${MODE}" == "update" ]]; then
        echo "[ensure-codex] Updating Codex in ${CODEX_NPM_PREFIX}..." >&2
    else
        echo "[ensure-codex] Installing Codex in ${CODEX_NPM_PREFIX}..." >&2
    fi

    # Add 120-second timeout to prevent npm from hanging
    timeout 120 npm install --global --prefix "${CODEX_NPM_PREFIX}" --silent @openai/codex@latest \
        2>/dev/null || timeout 120 npm install --global --prefix "${CODEX_NPM_PREFIX}" @openai/codex@latest >&2 || \
        echo "[ensure-codex] WARNING: npm install timed out or failed" >&2
fi

if [[ ! -x "${CODEX_BIN}" ]]; then
    echo "[ensure-codex] ERROR: Codex binary not found after installation: ${CODEX_BIN}" >&2
    exit 1
fi

if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
    printf '%s\n' "${CODEX_NPM_PREFIX}"
fi

if [[ "${PRINT_BIN}" -eq 1 ]]; then
    printf '%s\n' "${CODEX_BIN}"
fi
