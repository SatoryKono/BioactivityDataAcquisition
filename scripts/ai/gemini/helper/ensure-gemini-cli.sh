#!/usr/bin/env bash
# Ensure a writable Gemini CLI installation for project launchers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../../.." && pwd))}"
GEMINI_TOOLING_DIR="${REPO_ROOT}/scripts/ai/gemini/npm-tooling"
GEMINI_TOOLING_MANIFEST="${GEMINI_TOOLING_DIR}/package.json"
GEMINI_TOOLING_LOCK="${GEMINI_TOOLING_DIR}/package-lock.json"

GEMINI_TOOL_HOME_DEFAULT="${REPO_ROOT}/.cache/tools/gemini-cli"
# Windows-mounted paths under /mnt/* often reject npm rename (EACCES) and are
# extremely slow for global installs. Prefer a Linux-native home cache when the
# repo lives on a WSL mount and no explicit prefix was provided by the caller.
if [[ -z "${GEMINI_NPM_PREFIX:-}" ]]; then
    if [[ "${REPO_ROOT}" == /mnt/* || "${REPO_ROOT}" == /mnt ]]; then
        GEMINI_NPM_PREFIX="${HOME}/.cache/bioetl-gemini/npm-global"
    else
        GEMINI_NPM_PREFIX="${GEMINI_TOOL_HOME_DEFAULT}/npm-global"
    fi
fi
if [[ -z "${GEMINI_NPM_CACHE:-}" ]]; then
    if [[ "${REPO_ROOT}" == /mnt/* || "${REPO_ROOT}" == /mnt ]]; then
        GEMINI_NPM_CACHE="${HOME}/.cache/bioetl-gemini/npm-cache"
    else
        GEMINI_NPM_CACHE="${GEMINI_TOOL_HOME_DEFAULT}/npm-cache"
    fi
fi
if [[ -z "${GEMINI_CLI_HOME:-}" ]]; then
    if [[ "${REPO_ROOT}" == /mnt/* || "${REPO_ROOT}" == /mnt ]]; then
        GEMINI_CLI_HOME="${HOME}/.cache/bioetl-gemini/home"
    else
        GEMINI_CLI_HOME="${GEMINI_TOOL_HOME_DEFAULT}/home"
    fi
fi
GEMINI_BIN="${GEMINI_NPM_PREFIX}/bin/gemini"
GEMINI_NODE_BIN="${GEMINI_NPM_PREFIX}/bin/node"
GEMINI_CACHE_STAMP="${GEMINI_NPM_PREFIX}/.toolchain-cache-id"

case "$(uname -s):$(uname -m)" in
    Linux:x86_64)
        GEMINI_NODE_PACKAGE="node-linux-x64"
        ;;
    Linux:aarch64 | Linux:arm64)
        GEMINI_NODE_PACKAGE="node-linux-arm64"
        ;;
    *)
        echo "[ensure-gemini] ERROR: Unsupported managed Node platform: $(uname -s):$(uname -m)" >&2
        exit 1
        ;;
esac
GEMINI_NODE_SOURCE="${GEMINI_NPM_PREFIX}/node_modules/${GEMINI_NODE_PACKAGE}/bin/node"

MODE_ENSURE="ensure"
MODE_UPDATE="update"
MODE="${MODE_ENSURE}"
PRINT_BIN=0
PRINT_PREFIX=0
ALLOW_INSTALL=1
HEALTHCHECK_TIMEOUT="${GEMINI_HEALTHCHECK_TIMEOUT:-15}"

for arg in "$@"; do
    case "$arg" in
        --ensure)
            MODE="${MODE_ENSURE}"
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

if [[ ! -f "${GEMINI_TOOLING_MANIFEST}" || ! -f "${GEMINI_TOOLING_LOCK}" ]]; then
    echo "[ensure-gemini] ERROR: Pinned tooling manifest or lockfile is missing: ${GEMINI_TOOLING_DIR}" >&2
    exit 1
fi

lock_sha256() {
    local lockfile_path="$1"

    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${lockfile_path}" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "${lockfile_path}" | awk '{print $1}'
    else
        node -e 'const fs=require("fs");const crypto=require("crypto");process.stdout.write(crypto.createHash("sha256").update(fs.readFileSync(process.argv[1])).digest("hex"))' "${lockfile_path}"
    fi
}

EXPECTED_LOCK_SHA="$(lock_sha256 "${GEMINI_TOOLING_LOCK}")"
EXPECTED_CACHE_ID="${EXPECTED_LOCK_SHA}:${GEMINI_NODE_PACKAGE}"

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
CURRENT_CACHE_ID=""
if [[ -f "${GEMINI_CACHE_STAMP}" ]]; then
    CURRENT_CACHE_ID="$(tr -d '[:space:]' < "${GEMINI_CACHE_STAMP}")"
fi
if [[ "${MODE}" == "${MODE_UPDATE}" || ! -x "${GEMINI_BIN}" || ! -x "${GEMINI_NODE_BIN}" || ! -x "${GEMINI_NODE_SOURCE}" || "${CURRENT_CACHE_ID}" != "${EXPECTED_CACHE_ID}" ]]; then
    need_install=1
fi

if [[ "${need_install}" -eq 1 && "${ALLOW_INSTALL}" -eq 0 ]]; then
    echo "[ensure-gemini] ERROR: Managed Gemini CLI is missing or stale for package-lock.json; run with --ensure" >&2
    exit 1
fi

if [[ "${need_install}" -eq 1 && "${ALLOW_INSTALL}" -eq 1 ]]; then
    if [[ "${MODE}" == "${MODE_UPDATE}" ]]; then
        echo "[ensure-gemini] Updating Gemini CLI in ${GEMINI_NPM_PREFIX}..." >&2
    else
        echo "[ensure-gemini] Installing Gemini CLI in ${GEMINI_NPM_PREFIX}..." >&2
    fi

    # Scorecard PinnedDependencies (alerts 1410/1411): install only the committed
    # integrity-pinned dependency graph. Never fall back to an unlocked install.
    cp "${GEMINI_TOOLING_MANIFEST}" "${GEMINI_NPM_PREFIX}/package.json"
    cp "${GEMINI_TOOLING_LOCK}" "${GEMINI_NPM_PREFIX}/package-lock.json"
    npm ci --prefix "${GEMINI_NPM_PREFIX}" --omit=dev --ignore-scripts --no-fund --no-audit >&2

    mkdir -p "${GEMINI_NPM_PREFIX}/bin"
    if [[ ! -x "${GEMINI_NPM_PREFIX}/node_modules/.bin/gemini" || ! -x "${GEMINI_NODE_SOURCE}" ]]; then
        echo "[ensure-gemini] ERROR: Locked dependency installation did not produce the expected binaries" >&2
        exit 1
    fi
    ln -sfn ../node_modules/.bin/gemini "${GEMINI_BIN}"
    ln -sfn "../node_modules/${GEMINI_NODE_PACKAGE}/bin/node" "${GEMINI_NODE_BIN}"
    printf '%s\n' "${EXPECTED_CACHE_ID}" > "${GEMINI_CACHE_STAMP}.tmp"
    mv -f "${GEMINI_CACHE_STAMP}.tmp" "${GEMINI_CACHE_STAMP}"
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
if [[ "${ALLOW_INSTALL}" -eq 1 || "${PRINT_BIN}" -eq 0 && "${PRINT_PREFIX}" -eq 0 || "${MODE}" == "${MODE_UPDATE}" ]] \
    && ! GEMINI_CLI_HOME="${GEMINI_CLI_HOME}" PATH="${GEMINI_NPM_PREFIX}/bin:${PATH}" \
        timeout "${HEALTHCHECK_TIMEOUT}" "${GEMINI_BIN}" --version >/dev/null 2>&1; then
    echo "[ensure-gemini] ERROR: Gemini CLI failed to start within ${HEALTHCHECK_TIMEOUT}s from managed prefix: ${GEMINI_BIN}" >&2
    exit 1
fi

if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
    printf '%s\n' "${GEMINI_NPM_PREFIX}"
fi

if [[ "${PRINT_BIN}" -eq 1 ]]; then
    printf '%s\n' "${GEMINI_BIN}"
fi
