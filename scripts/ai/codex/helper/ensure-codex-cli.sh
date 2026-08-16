#!/usr/bin/env bash
# INTERNAL: Ensure a writable Codex CLI installation for project launchers.
# Called by: Multiple parent scripts
# DO NOT invoke directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"

CODEX_TOOL_HOME_DEFAULT="${REPO_ROOT}/.cache/tools/codex-cli"
# Windows-mounted paths under /mnt/* often reject npm rename (EACCES). Prefer a
# Linux-native home cache when the repo lives on a WSL mount and no explicit
# prefix was provided by the caller.
if [[ -z "${CODEX_NPM_PREFIX:-}" ]]; then
    if [[ "${REPO_ROOT}" == /mnt/* || "${REPO_ROOT}" == /mnt ]]; then
        CODEX_NPM_PREFIX="${HOME}/.cache/bioetl-codex/npm-global"
    else
        CODEX_NPM_PREFIX="${CODEX_TOOL_HOME_DEFAULT}/npm-global"
    fi
fi
if [[ -z "${CODEX_NPM_CACHE:-}" ]]; then
    if [[ "${REPO_ROOT}" == /mnt/* || "${REPO_ROOT}" == /mnt ]]; then
        CODEX_NPM_CACHE="${HOME}/.cache/bioetl-codex/npm-cache"
    else
        CODEX_NPM_CACHE="${CODEX_TOOL_HOME_DEFAULT}/npm-cache"
    fi
fi
CODEX_BIN="${CODEX_NPM_PREFIX}/bin/codex"
USER_CODEX_PREFIX_DEFAULT="${HOME}/.npm-global"
USER_CODEX_BIN_DEFAULT="${USER_CODEX_PREFIX_DEFAULT}/bin/codex"
LINUX_CODEX_PREFIX_DEFAULT="${HOME}/.cache/bioetl-codex/npm-global"
LINUX_CODEX_BIN_DEFAULT="${LINUX_CODEX_PREFIX_DEFAULT}/bin/codex"
CODEX_COMMAND_SHIM_DIR="${BIOETL_CODEX_COMMAND_SHIM_DIR:-${HOME}/.local/bin}"
CODEX_COMMAND_SHIM="${CODEX_COMMAND_SHIM_DIR}/codex"
CODEX_COMMAND_SHIM_MARKER="# Managed by BioETL Codex launcher setup"
CANONICAL_LAUNCHER="${REPO_ROOT}/scripts/ai/codex/run-codex.sh"

MODE_UPDATE="update"
MODE="ensure"
PRINT_BIN=0
PRINT_PREFIX=0
ALLOW_INSTALL=1
INSTALL_COMMAND_SHIM=0

install_command_shim() {
    local temporary_shim=""

    if [[ ! -f "${CANONICAL_LAUNCHER}" ]]; then
        echo "[ensure-codex] ERROR: Canonical launcher not found: ${CANONICAL_LAUNCHER}" >&2
        return 1
    fi

    if [[ -e "${CODEX_COMMAND_SHIM}" || -L "${CODEX_COMMAND_SHIM}" ]]; then
        if [[ ! -f "${CODEX_COMMAND_SHIM}" ]] || \
            ! grep -Fq "${CODEX_COMMAND_SHIM_MARKER}" "${CODEX_COMMAND_SHIM}"; then
            echo "[ensure-codex] ERROR: Refusing to overwrite non-BioETL command: ${CODEX_COMMAND_SHIM}" >&2
            return 1
        fi
    fi

    mkdir -p "${CODEX_COMMAND_SHIM_DIR}"
    temporary_shim="$(mktemp "${CODEX_COMMAND_SHIM}.tmp.XXXXXX")"
    {
        printf '%s\n' '#!/usr/bin/env bash'
        printf '%s\n' "${CODEX_COMMAND_SHIM_MARKER}"
        printf '%s\n' 'set -euo pipefail'
        printf 'REPO_ROOT=%q exec bash %q "$@"\n' \
            "${REPO_ROOT}" "${CANONICAL_LAUNCHER}"
    } > "${temporary_shim}"
    chmod 700 "${temporary_shim}"
    mv -f -- "${temporary_shim}" "${CODEX_COMMAND_SHIM}"
    printf '%s\n' "${CODEX_COMMAND_SHIM}"
}

for arg in "$@"; do
    case "$arg" in
        --ensure)
            MODE="ensure"
            ;;
        --update)
            MODE="${MODE_UPDATE}"
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
        --install-command-shim)
            INSTALL_COMMAND_SHIM=1
            ;;
        *)
            echo "[ensure-codex] ERROR: Unsupported argument: $arg" >&2
            exit 2
            ;;
    esac
done

if [[ "${INSTALL_COMMAND_SHIM}" -eq 1 ]]; then
    install_command_shim
    exit $?
fi

resolve_existing_codex() {
    local path_bin=""
    if [[ -x "${CODEX_BIN}" ]]; then
        CODEX_BIN="${CODEX_BIN}"
        CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX}"
        return 0
    fi

    if [[ -x "${LINUX_CODEX_BIN_DEFAULT}" ]]; then
        CODEX_BIN="${LINUX_CODEX_BIN_DEFAULT}"
        CODEX_NPM_PREFIX="${LINUX_CODEX_PREFIX_DEFAULT}"
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

if [[ "${MODE}" != "${MODE_UPDATE}" ]]; then
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
if [[ "${MODE}" == "${MODE_UPDATE}" || ! -x "${CODEX_BIN}" ]]; then
    need_install=1
fi

if [[ "${need_install}" -eq 1 && "${ALLOW_INSTALL}" -eq 1 ]]; then
    if [[ "${MODE}" == "${MODE_UPDATE}" ]]; then
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
