#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"

NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/tmp/playwright-browsers}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
BIOETL_TOOLS_DIR="${BIOETL_TOOLS_DIR:-/tmp/bioetl-tools}"
PLAYWRIGHT_RUNTIME_ROOT="${PLAYWRIGHT_RUNTIME_ROOT:-${BIOETL_TOOLS_DIR}/playwright-runtime}"
PLAYWRIGHT_NODE_MODULES_DIR="${PLAYWRIGHT_NODE_MODULES_DIR:-${PLAYWRIGHT_RUNTIME_ROOT}/node_modules}"
PREFER_ISOLATED_RUNTIME="${BIOETL_PLAYWRIGHT_PREFER_ISOLATED_RUNTIME:-auto}"
LOCAL_SYSTEM_LIB_ROOT="${LOCAL_SYSTEM_LIB_ROOT:-${REPO_ROOT}/.cache/grafana-screenshot-runtime/root}"
LOCAL_SYSTEM_DEB_DIR="${LOCAL_SYSTEM_DEB_DIR:-${REPO_ROOT}/.cache/grafana-screenshot-runtime/debs}"
LOCAL_SYSTEM_LIB_DIR="${LOCAL_SYSTEM_LIB_DIR:-${LOCAL_SYSTEM_LIB_ROOT}/usr/lib/x86_64-linux-gnu}"

ATTEMPT_SYSTEM_INSTALL=0
RUN_SMOKE=0
SKIP_SYSTEM_CHECK=0
PLAYWRIGHT_INSTALL_ROOT=""

APT_PACKAGES=(
  libnspr4
  libnss3
  libdrm2
  libgbm1
  libxcomposite1
  libxdamage1
  libxfixes3
  libxkbcommon0
  libxrandr2
)

APT_PACKAGE_ALTERNATIVES=(
  "libatk-bridge2.0-0|libatk-bridge2.0-0t64"
  "libatk1.0-0|libatk1.0-0t64"
  "libcups2|libcups2t64"
  "libasound2|libasound2t64"
)

REQUIRED_LIBS=(
  libnspr4.so
  libnss3.so
  libnssutil3.so
  libsmime3.so
  libasound.so.2
  libatk-bridge-2.0.so.0
  libatk-1.0.so.0
  libcups.so.2
  libdrm.so.2
  libgbm.so.1
  libXcomposite.so.1
  libXdamage.so.1
  libXfixes.so.3
  libxkbcommon.so.0
  libXrandr.so.2
)

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh [options]

Options:
  --attempt-system-install  Try to install missing Chromium shared libraries
                            with apt-get when sudo/root is available.
  --skip-system-check       Skip shared-library verification.
  --smoke                   Run a non-GUI screenshot smoke command after setup.
  --help                    Show this help.

Environment:
  NPM_CONFIG_CACHE          npm cache directory. Default: /tmp/npm-cache
  PLAYWRIGHT_BROWSERS_PATH  Browser download directory. Default: /tmp/playwright-browsers
  UV_CACHE_DIR              uv cache directory for smoke command. Default: /tmp/uv-cache
  BIOETL_TOOLS_DIR          Tool cache root. Default: /tmp/bioetl-tools
  BIOETL_PLAYWRIGHT_PREFER_ISOLATED_RUNTIME
                            true/false/auto. Auto uses the isolated /tmp tool
                            runtime for WSL /mnt checkouts.
  LOCAL_SYSTEM_LIB_ROOT     User-space extracted Chromium libs root.
                            Default: .cache/grafana-screenshot-runtime/root
  LOCAL_SYSTEM_DEB_DIR      User-space downloaded .deb cache.
                            Default: .cache/grafana-screenshot-runtime/debs
  GRAFANA_BASE_URL          Optional smoke target. Default from rerender-grafana.
  GRAFANA_USERNAME          Optional smoke auth. Default from rerender-grafana.
  GRAFANA_PASSWORD          Optional smoke auth. Default from rerender-grafana.
EOF
}

parse_args() {
  while (($# > 0)); do
    case "$1" in
      --attempt-system-install)
        ATTEMPT_SYSTEM_INSTALL=1
        ;;
      --skip-system-check)
        SKIP_SYSTEM_CHECK=1
        ;;
      --smoke)
        RUN_SMOKE=1
        ;;
      --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 2
        ;;
    esac
    shift
  done
}

log() {
  printf '%s\n' "$*"
}

have_command() {
  command -v "$1" >/dev/null 2>&1
}

ensure_dirs() {
  mkdir -p \
    "${NPM_CONFIG_CACHE}" \
    "${PLAYWRIGHT_BROWSERS_PATH}" \
    "${UV_CACHE_DIR}" \
    "${BIOETL_TOOLS_DIR}" \
    "${LOCAL_SYSTEM_DEB_DIR}" \
    "${LOCAL_SYSTEM_LIB_ROOT}"
}

local_lib_available() {
  local lib="$1"
  [[ -d "${LOCAL_SYSTEM_LIB_ROOT}" ]] || return 1
  find "${LOCAL_SYSTEM_LIB_ROOT}" \( -type f -o -type l \) \
    -name "${lib}" -print -quit 2>/dev/null \
    | grep -Fq "${lib}"
}

collect_missing_libs() {
  local missing=()
  local lib ldconfig_output
  if ! have_command ldconfig; then
    printf '%s\n' "${missing[@]}"
    return 0
  fi
  # Do not combine `grep -q` with `ldconfig -p` under `set -o pipefail`.
  # `grep -q` exits on the first match and can make ldconfig receive SIGPIPE,
  # which incorrectly classifies an installed library as missing.
  ldconfig_output="$(ldconfig -p 2>/dev/null || true)"
  for lib in "${REQUIRED_LIBS[@]}"; do
    if ! grep -F "${lib}" >/dev/null <<<"${ldconfig_output}" \
      && ! local_lib_available "${lib}"; then
      missing+=("${lib}")
    fi
  done
  printf '%s\n' "${missing[@]}"
}

print_install_hint() {
  local missing_libs="${1:-}"
  log "Missing shared libraries prevent Playwright Chromium from launching."
  if [[ -n "${missing_libs}" ]]; then
    log "Missing libraries detected by ldconfig:"
    while IFS= read -r lib; do
      [[ -n "${lib}" ]] && log "  - ${lib}"
    done <<<"${missing_libs}"
    log ""
  fi
  log "Install the standard headless Chromium runtime packages with:"
  log ""
  log "  sudo apt-get update -qq"
  log "  sudo apt-get install -y ${APT_PACKAGES[*]} libatk-bridge2.0-0 libatk1.0-0 libcups2 libasound2"
  log ""
  log "On Ubuntu 24.04, use the corresponding *t64 package when a legacy"
  log "libatk/libcups/libasound package has no candidate."
  log "Without sudo, this setup script can download and extract the missing"
  log "runtime libraries into ${LOCAL_SYSTEM_LIB_ROOT}."
  log ""
}

resolve_apt_package() {
  local candidate
  for candidate in "$@"; do
    if apt-cache policy "${candidate}" 2>/dev/null \
      | awk '$1 == "Candidate:" && $2 != "(none)" { found = 1 } END { exit !found }'; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

resolved_apt_packages() {
  local packages=("${APT_PACKAGES[@]}")
  local alternatives choice
  for alternatives in "${APT_PACKAGE_ALTERNATIVES[@]}"; do
    IFS='|' read -r -a choices <<<"${alternatives}"
    choice="$(resolve_apt_package "${choices[@]}" || true)"
    if [[ -n "${choice}" ]]; then
      packages+=("${choice}")
    else
      packages+=("${choices[0]}")
    fi
  done
  printf '%s\n' "${packages[@]}"
}

try_install_system_libs() {
  if ! have_command apt-get; then
    log "apt-get is not available on this host."
    return 1
  fi
  if [[ "${EUID}" -eq 0 ]]; then
    apt-get update -qq
    mapfile -t packages < <(resolved_apt_packages)
    apt-get install -y "${packages[@]}"
    return 0
  fi
  if have_command sudo && sudo -n true >/dev/null 2>&1; then
    sudo apt-get update -qq
    mapfile -t packages < <(resolved_apt_packages)
    sudo apt-get install -y "${packages[@]}"
    return 0
  fi
  log "Root/sudo is required to install system libraries automatically."
  return 1
}

try_install_local_libs() {
  if ! have_command apt-get || ! have_command dpkg-deb || ! have_command apt-cache; then
    log "apt-get, apt-cache, and dpkg-deb are required for user-space library extraction."
    return 1
  fi

  mapfile -t packages < <(resolved_apt_packages)
  log "Downloading Chromium runtime libraries into ${LOCAL_SYSTEM_DEB_DIR}..."
  (
    cd "${LOCAL_SYSTEM_DEB_DIR}"
    apt-get download "${packages[@]}"
  )

  log "Extracting Chromium runtime libraries into ${LOCAL_SYSTEM_LIB_ROOT}..."
  local deb
  shopt -s nullglob
  for deb in "${LOCAL_SYSTEM_DEB_DIR}"/*.deb; do
    dpkg-deb -x "${deb}" "${LOCAL_SYSTEM_LIB_ROOT}"
  done
  shopt -u nullglob
}

export_local_lib_path() {
  if [[ -d "${LOCAL_SYSTEM_LIB_DIR}" ]]; then
    export BIOETL_PLAYWRIGHT_LIBRARY_PATH="${LOCAL_SYSTEM_LIB_DIR}"
    export LD_LIBRARY_PATH="${LOCAL_SYSTEM_LIB_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  fi
}

playwright_version_spec() {
  local python_bin
  python_bin="$(command -v python3 || command -v python || true)"
  if [[ -z "${python_bin}" ]]; then
    printf '%s' 'latest'
    return 0
  fi
  "${python_bin}" - "${REPO_ROOT}/package.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

package = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
deps = package.get("devDependencies", {}) or {}
value = deps.get("playwright")
if not value:
    value = (package.get("dependencies", {}) or {}).get("playwright", "latest")
print(value)
PY
}

run_npm_install() {
  local target_dir="$1"
  shift
  (
    cd "${target_dir}"
    NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE}" \
    NPM_CONFIG_INCLUDE=dev \
    NPM_CONFIG_PRODUCTION=false \
    npm_config_production=false \
    NODE_ENV=development \
      "$@"
  )
}

install_playwright_tool_runtime() {
  local version_spec
  version_spec="$(playwright_version_spec)"
  log "Falling back to isolated Playwright tool cache at ${PLAYWRIGHT_RUNTIME_ROOT}..."
  mkdir -p "${PLAYWRIGHT_RUNTIME_ROOT}"
  if [[ ! -f "${PLAYWRIGHT_RUNTIME_ROOT}/package.json" ]]; then
    printf '{\n  "name": "bioetl-playwright-runtime",\n  "private": true\n}\n' \
      > "${PLAYWRIGHT_RUNTIME_ROOT}/package.json"
  fi
  run_npm_install "${PLAYWRIGHT_RUNTIME_ROOT}" \
    npm install --include=dev --no-bin-links "playwright@${version_spec}"
  PLAYWRIGHT_INSTALL_ROOT="${PLAYWRIGHT_RUNTIME_ROOT}"
}

prefer_isolated_runtime() {
  case "${PREFER_ISOLATED_RUNTIME,,}" in
    1|true|yes)
      return 0
      ;;
    0|false|no)
      return 1
      ;;
    auto)
      [[ "${REPO_ROOT}" == /mnt/* ]]
      return
      ;;
    *)
      log "Invalid BIOETL_PLAYWRIGHT_PREFER_ISOLATED_RUNTIME=${PREFER_ISOLATED_RUNTIME}; expected true, false, or auto."
      exit 2
      ;;
  esac
}

install_node_dependencies() {
  if prefer_isolated_runtime; then
    log "Using isolated Playwright runtime for mounted checkout ${REPO_ROOT}."
    install_playwright_tool_runtime
    return 0
  fi
  log "Installing repo-local Node dependencies..."
  local npm_command=(npm install --include=dev --no-bin-links)
  if [[ -f "${REPO_ROOT}/package-lock.json" ]]; then
    npm_command=(npm ci --include=dev --no-bin-links)
  fi
  if run_npm_install "${REPO_ROOT}" "${npm_command[@]}"; then
    PLAYWRIGHT_INSTALL_ROOT="${REPO_ROOT}"
    return 0
  fi
  install_playwright_tool_runtime
}

install_playwright_browser() {
  log "Installing Playwright Chromium runtime into ${PLAYWRIGHT_BROWSERS_PATH}..."
  local cli_path="${PLAYWRIGHT_INSTALL_ROOT}/node_modules/playwright/cli.js"
  if [[ ! -f "${cli_path}" ]]; then
    log "Playwright CLI is missing after dependency install."
    log "Ensure repo-local devDependencies were installed before browser bootstrap."
    return 1
  fi
  (
    cd "${PLAYWRIGHT_INSTALL_ROOT}"
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
    BIOETL_PLAYWRIGHT_NODE_MODULES="${PLAYWRIGHT_INSTALL_ROOT}/node_modules" \
    NODE_PATH="${PLAYWRIGHT_INSTALL_ROOT}/node_modules${NODE_PATH:+:${NODE_PATH}}" \
      node "${cli_path}" install chromium
  )
}

run_browser_launch_smoke() {
  log "Running headless Chromium launch smoke..."
  (
    cd "${PLAYWRIGHT_INSTALL_ROOT}"
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
    BIOETL_PLAYWRIGHT_NODE_MODULES="${PLAYWRIGHT_INSTALL_ROOT}/node_modules" \
    NODE_PATH="${PLAYWRIGHT_INSTALL_ROOT}/node_modules${NODE_PATH:+:${NODE_PATH}}" \
      node -e 'const { chromium } = require("playwright"); (async () => { const browser = await chromium.launch({ headless: true }); await browser.close(); })().catch((error) => { console.error(String(error && error.message ? error.message : error)); process.exit(1); });'
  )
}

run_repo_smoke() {
  log "Running screenshot smoke against rerender-grafana..."
  (
    cd "${REPO_ROOT}"
    UV_CACHE_DIR="${UV_CACHE_DIR}" \
    UV_NO_BUILD=1 \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
    BIOETL_PLAYWRIGHT_NODE_MODULES="${PLAYWRIGHT_INSTALL_ROOT}/node_modules" \
    NODE_PATH="${PLAYWRIGHT_INSTALL_ROOT}/node_modules${NODE_PATH:+:${NODE_PATH}}" \
      uv run --frozen --no-build python -m scripts.ops rerender-grafana \
        --uids bioetl-control-plane-v1 \
        --timeout-seconds 90 \
        --fallback playwright
  )
}

main() {
  parse_args "$@"
  ensure_dirs

  local missing_libs_text=""
  if [[ "${SKIP_SYSTEM_CHECK}" -eq 0 ]]; then
    missing_libs_text="$(collect_missing_libs || true)"
    if [[ -n "${missing_libs_text}" ]]; then
      if [[ "${ATTEMPT_SYSTEM_INSTALL}" -eq 1 ]]; then
        log "Attempting to install missing system libraries..."
        try_install_system_libs || {
          print_install_hint "${missing_libs_text}"
          exit 1
        }
        missing_libs_text="$(collect_missing_libs || true)"
        if [[ -n "${missing_libs_text}" ]]; then
          print_install_hint "${missing_libs_text}"
          exit 1
        fi
      else
        log "Attempting user-space Chromium library extraction..."
        try_install_local_libs || {
          print_install_hint "${missing_libs_text}"
          exit 1
        }
        export_local_lib_path
        missing_libs_text="$(collect_missing_libs || true)"
        if [[ -n "${missing_libs_text}" ]]; then
          print_install_hint "${missing_libs_text}"
          exit 1
        fi
      fi
    fi
  fi

  export_local_lib_path
  install_node_dependencies
  install_playwright_browser
  run_browser_launch_smoke

  if [[ "${RUN_SMOKE}" -eq 1 ]]; then
    run_repo_smoke
  fi

  log ""
  log "Grafana screenshot runtime is ready."
  log "Playwright modules root: ${PLAYWRIGHT_INSTALL_ROOT}/node_modules"
  log "Playwright browser root: ${PLAYWRIGHT_BROWSERS_PATH}"
  log "Playwright local library path: ${LOCAL_SYSTEM_LIB_DIR}"
  log "Example command:"
  log "  UV_CACHE_DIR=${UV_CACHE_DIR} PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} BIOETL_PLAYWRIGHT_NODE_MODULES=${PLAYWRIGHT_INSTALL_ROOT}/node_modules BIOETL_PLAYWRIGHT_LIBRARY_PATH=${LOCAL_SYSTEM_LIB_DIR} uv run python -m scripts.ops rerender-grafana --uids bioetl-control-plane-v1 --fallback playwright"
}

main "$@"
