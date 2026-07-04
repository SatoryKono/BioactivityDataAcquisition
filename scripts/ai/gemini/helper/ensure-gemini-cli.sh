#!/usr/bin/env bash
# Ensure a writable Gemini CLI installation for project launchers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"

GEMINI_TOOL_HOME_DEFAULT="${REPO_ROOT}/.cache/tools/gemini-cli"
GEMINI_NPM_PREFIX="${GEMINI_NPM_PREFIX:-${GEMINI_TOOL_HOME_DEFAULT}/npm-global}"
GEMINI_NPM_CACHE="${GEMINI_NPM_CACHE:-${GEMINI_TOOL_HOME_DEFAULT}/npm-cache}"
GEMINI_CLI_HOME="${GEMINI_CLI_HOME:-${GEMINI_TOOL_HOME_DEFAULT}/home}"
GEMINI_BIN="${GEMINI_NPM_PREFIX}/bin/gemini"
GEMINI_NODE_BIN="${GEMINI_NPM_PREFIX}/bin/node"

MODE="ensure"
PRINT_BIN=0
PRINT_PREFIX=0
ALLOW_INSTALL=1
HEALTHCHECK_TIMEOUT="${GEMINI_HEALTHCHECK_TIMEOUT:-15}"

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
            echo "[ensure-gemini] ERROR: Unsupported argument: $arg" >&2
            exit 2
            ;;
    esac
done

if ! command -v node >/dev/null 2>&1; then
    echo "[ensure-gemini] ERROR: Node.js is required but was not found in PATH" >&2
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "[ensure-gemini] ERROR: npm is required but was not found in PATH" >&2
    exit 1
fi

if [[ "${ALLOW_INSTALL}" -eq 1 ]]; then
    mkdir -p "${GEMINI_NPM_PREFIX}"
    mkdir -p "${GEMINI_NPM_CACHE}"
    mkdir -p "${GEMINI_CLI_HOME}"
fi

export NPM_CONFIG_PREFIX="${GEMINI_NPM_PREFIX}"
export npm_config_prefix="${GEMINI_NPM_PREFIX}"
export NPM_CONFIG_CACHE="${GEMINI_NPM_CACHE}"
export npm_config_cache="${GEMINI_NPM_CACHE}"
export PATH="${GEMINI_NPM_PREFIX}/bin:${PATH}"

need_install=0
if [[ "${MODE}" == "update" || ! -x "${GEMINI_BIN}" || ! -x "${GEMINI_NODE_BIN}" ]]; then
    need_install=1
fi

if [[ "${need_install}" -eq 1 && "${ALLOW_INSTALL}" -eq 1 ]]; then
    if [[ "${MODE}" == "update" ]]; then
        echo "[ensure-gemini] Updating Gemini CLI in ${GEMINI_NPM_PREFIX}..." >&2
    else
        echo "[ensure-gemini] Installing Gemini CLI in ${GEMINI_NPM_PREFIX}..." >&2
    fi

    npm install --global --prefix "${GEMINI_NPM_PREFIX}" --silent node@22 @google/gemini-cli@latest \
        2>/dev/null || npm install --global --prefix "${GEMINI_NPM_PREFIX}" node@22 @google/gemini-cli@latest >&2
fi

if [[ ! -x "${GEMINI_BIN}" ]]; then
    echo "[ensure-gemini] ERROR: Gemini CLI binary not found after installation: ${GEMINI_BIN}" >&2
    exit 1
fi

if [[ ! -x "${GEMINI_NODE_BIN}" ]]; then
    echo "[ensure-gemini] ERROR: Managed Node.js binary not found after installation: ${GEMINI_NODE_BIN}" >&2
    exit 1
fi

# Discovery callers only need the managed path and should not block on CLI startup.
if [[ "${ALLOW_INSTALL}" -eq 1 || "${PRINT_BIN}" -eq 0 && "${PRINT_PREFIX}" -eq 0 || "${MODE}" == "update" ]]; then
    if ! GEMINI_CLI_HOME="${GEMINI_CLI_HOME}" PATH="${GEMINI_NPM_PREFIX}/bin:${PATH}" \
        timeout "${HEALTHCHECK_TIMEOUT}" "${GEMINI_BIN}" --version >/dev/null 2>&1; then
        echo "[ensure-gemini] ERROR: Gemini CLI failed to start within ${HEALTHCHECK_TIMEOUT}s from managed prefix: ${GEMINI_BIN}" >&2
        exit 1
    fi
fi

if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
    printf '%s\n' "${GEMINI_NPM_PREFIX}"
fi

if [[ "${PRINT_BIN}" -eq 1 ]]; then
    printf '%s\n' "${GEMINI_BIN}"
fi
