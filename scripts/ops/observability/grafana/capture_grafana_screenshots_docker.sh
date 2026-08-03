#!/usr/bin/env bash
# Capture shipped Grafana dashboards with a Playwright container.
# Prefer this when host Chromium launch is flaky (Windows GDrive / WSL /mnt).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT_DIR="${1:-${ROOT}/reports/observability/grafana/screenshots}"
# Prefer a pre-tagged local image; fall back to official Playwright jammy.
IMAGE="${PLAYWRIGHT_DOCKER_IMAGE:-mcp/playwright:local}"
GRAFANA_BASE_URL="${GRAFANA_BASE_URL:-http://host.docker.internal:3000}"
GRAFANA_USERNAME="${GRAFANA_USERNAME:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-}"
THEME="${GRAFANA_SCREENSHOT_THEME:-dark}"
CAPTURE_JS="${ROOT}/scripts/ops/observability/grafana/_capture_all_dashboards.js"

if [[ -z "${GRAFANA_PASSWORD}" && -z "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  echo "Set GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN (no default password)." >&2
  exit 9
fi

if [[ ! -f "${CAPTURE_JS}" ]]; then
  echo "Missing capture script: ${CAPTURE_JS}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

# Single container run: install playwright once under /tmp, then capture all UIDs.
# Use --entrypoint bash because mcp/playwright images may wrap node as MCP server.
docker run --rm \
  --ipc=host \
  --shm-size=2g \
  --add-host=host.docker.internal:host-gateway \
  --entrypoint bash \
  -e GRAFANA_BASE_URL="${GRAFANA_BASE_URL}" \
  -e GRAFANA_USERNAME="${GRAFANA_USERNAME}" \
  -e GRAFANA_PASSWORD="${GRAFANA_PASSWORD}" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" \
  -e GRAFANA_SCREENSHOT_THEME="${THEME}" \
  -e OUT_DIR=/out \
  -e SETTLE_MS="${SETTLE_MS:-12000}" \
  -e NAV_TIMEOUT_MS="${NAV_TIMEOUT_MS:-180000}" \
  -e PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH_IN_CONTAINER:-/ms-playwright}" \
  -e PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
  -e NODE_PATH=/tmp/node_modules \
  -v "${OUT_DIR}:/out" \
  -v "${CAPTURE_JS}:/work/capture.js:ro" \
  "${IMAGE}" \
  -lc 'set -euo pipefail
cd /tmp
npm init -y >/dev/null 2>&1
npm i playwright@1.49.1 --no-fund --no-audit
# Prefer image browsers when present; otherwise let Playwright use defaults.
if [[ ! -d "${PLAYWRIGHT_BROWSERS_PATH:-/ms-playwright}" ]]; then
  unset PLAYWRIGHT_BROWSERS_PATH PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
  npx playwright install chromium
fi
node /work/capture.js
'

echo "DONE screenshots in ${OUT_DIR}"
