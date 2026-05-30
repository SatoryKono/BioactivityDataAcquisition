#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"

NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/tmp/playwright-browsers}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

ATTEMPT_SYSTEM_INSTALL=0
RUN_SMOKE=0
SKIP_SYSTEM_CHECK=0

APT_PACKAGES=(
  libnspr4
  libnss3
  libasound2
  libatk-bridge2.0-0
  libatk1.0-0
  libcups2
  libdrm2
  libgbm1
  libxcomposite1
  libxdamage1
  libxfixes3
  libxkbcommon0
  libxrandr2
)

REQUIRED_LIBS=(
  libnspr4.so
  libnss3.so
  libnssutil3.so
  libasound.so.2
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
  mkdir -p "${NPM_CONFIG_CACHE}" "${PLAYWRIGHT_BROWSERS_PATH}" "${UV_CACHE_DIR}"
}

collect_missing_libs() {
  local missing=()
  local lib
  if ! have_command ldconfig; then
    printf '%s\n' "${missing[@]}"
    return 0
  fi
  for lib in "${REQUIRED_LIBS[@]}"; do
    if ! ldconfig -p 2>/dev/null | grep -Fq "${lib}"; then
      missing+=("${lib}")
    fi
  done
  printf '%s\n' "${missing[@]}"
}

print_install_hint() {
  log "Missing shared libraries prevent Playwright Chromium from launching."
  log "Install the standard headless Chromium runtime packages with:"
  log ""
  log "  sudo apt-get update -qq"
  log "  sudo apt-get install -y ${APT_PACKAGES[*]}"
  log ""
}

try_install_system_libs() {
  if ! have_command apt-get; then
    log "apt-get is not available on this host."
    return 1
  fi
  if [[ "${EUID}" -eq 0 ]]; then
    apt-get update -qq
    apt-get install -y "${APT_PACKAGES[@]}"
    return 0
  fi
  if have_command sudo && sudo -n true >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y "${APT_PACKAGES[@]}"
    return 0
  fi
  log "Root/sudo is required to install system libraries automatically."
  return 1
}

install_node_dependencies() {
  log "Installing repo-local Node dependencies..."
  local npm_command=(npm install --include=dev --no-bin-links)
  if [[ -f "${REPO_ROOT}/package-lock.json" ]]; then
    npm_command=(npm ci --include=dev --no-bin-links)
  fi
  (
    cd "${REPO_ROOT}"
    NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE}" \
    NPM_CONFIG_INCLUDE=dev \
    NPM_CONFIG_PRODUCTION=false \
    npm_config_production=false \
    NODE_ENV=development \
      "${npm_command[@]}"
  )
}

install_playwright_browser() {
  log "Installing Playwright Chromium runtime into ${PLAYWRIGHT_BROWSERS_PATH}..."
  if [[ ! -f "${REPO_ROOT}/node_modules/playwright/cli.js" ]]; then
    log "Playwright CLI is missing after dependency install."
    log "Ensure repo-local devDependencies were installed before browser bootstrap."
    return 1
  fi
  (
    cd "${REPO_ROOT}"
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
      node node_modules/playwright/cli.js install chromium
  )
}

run_browser_launch_smoke() {
  log "Running headless Chromium launch smoke..."
  (
    cd "${REPO_ROOT}"
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
      node -e 'const { chromium } = require("playwright"); (async () => { const browser = await chromium.launch({ headless: true }); await browser.close(); })().catch((error) => { console.error(String(error && error.message ? error.message : error)); process.exit(1); });'
  )
}

run_repo_smoke() {
  log "Running screenshot smoke against rerender-grafana..."
  (
    cd "${REPO_ROOT}"
    UV_CACHE_DIR="${UV_CACHE_DIR}" \
    PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
      uv run python -m scripts.ops rerender-grafana \
        --uids bioetl-control-plane-v1 \
        --timeout-seconds 30 \
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
          print_install_hint
          exit 1
        }
        missing_libs_text="$(collect_missing_libs || true)"
        if [[ -n "${missing_libs_text}" ]]; then
          print_install_hint
          exit 1
        fi
      else
        print_install_hint
        exit 1
      fi
    fi
  fi

  install_node_dependencies
  install_playwright_browser
  run_browser_launch_smoke

  if [[ "${RUN_SMOKE}" -eq 1 ]]; then
    run_repo_smoke
  fi

  log ""
  log "Grafana screenshot runtime is ready."
  log "Example command:"
  log "  UV_CACHE_DIR=${UV_CACHE_DIR} PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} uv run python -m scripts.ops rerender-grafana --uids bioetl-control-plane-v1"
}

main "$@"
