#!/usr/bin/env bash
# Capture shipped Grafana dashboards with the official Playwright container.
# Use when host Chromium launch is flaky (Windows GDrive/WSL /mnt paths).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT_DIR="${1:-${ROOT}/reports/observability/grafana/screenshots}"
IMAGE="${PLAYWRIGHT_DOCKER_IMAGE:-mcr.microsoft.com/playwright:v1.49.1-jammy}"
GRAFANA_BASE_URL="${GRAFANA_BASE_URL:-http://host.docker.internal:3000}"
GRAFANA_USERNAME="${GRAFANA_USERNAME:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-}"
THEME="${GRAFANA_SCREENSHOT_THEME:-dark}"

if [[ -z "${GRAFANA_PASSWORD}" && -z "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  echo "Set GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN (no default password)." >&2
  exit 9
fi

mkdir -p "${OUT_DIR}"
UIDS=(
  bioetl-control-plane-v1
  bioetl-overview-v2
  bioetl-runtime
  bioetl-provider-health-v2
  bioetl-dq-v2
  bioetl-workflow-overview
  bioetl-alerts-slo
  bioetl-silver-reject-explorer
)

CAPTURE_JS="$(mktemp)"
trap 'rm -f "${CAPTURE_JS}"' EXIT
cat >"${CAPTURE_JS}" <<'JS'
const { chromium } = require('playwright');
(async () => {
  const base = process.env.GRAFANA_BASE_URL;
  const user = process.env.GRAFANA_USERNAME || 'admin';
  const pass = process.env.GRAFANA_PASSWORD || '';
  const out = process.env.OUT_PNG;
  const uid = process.env.DASH_UID;
  const theme = process.env.THEME || 'dark';
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.fill('input[name="user"]', user);
  await page.fill('input[name="password"]', pass);
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle', timeout: 90000 }).catch(() => null),
    page.click('button[type="submit"]'),
  ]);
  await page.goto(
    `${base}/d/${uid}?orgId=1&from=now-12h&to=now&theme=${theme}&kiosk`,
    { waitUntil: 'networkidle', timeout: 180000 },
  );
  await page.waitForTimeout(Number(process.env.SETTLE_MS || 12000));
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  process.stdout.write(`wrote ${out}\n`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS

for uid in "${UIDS[@]}"; do
  out_name="${uid}-${THEME}.png"
  echo "capturing ${uid} -> ${out_name}"
  docker run --rm \
    --add-host=host.docker.internal:host-gateway \
    -e GRAFANA_BASE_URL="${GRAFANA_BASE_URL}" \
    -e GRAFANA_USERNAME="${GRAFANA_USERNAME}" \
    -e GRAFANA_PASSWORD="${GRAFANA_PASSWORD}" \
    -e DASH_UID="${uid}" \
    -e THEME="${THEME}" \
    -e OUT_PNG="/out/${out_name}" \
    -e SETTLE_MS="${SETTLE_MS:-12000}" \
    -v "${OUT_DIR}:/out" \
    -v "${CAPTURE_JS}:/work/capture.js:ro" \
    "${IMAGE}" \
    bash -lc 'cd /work && npm init -y >/dev/null 2>&1 && npm i playwright@1.49.1 >/dev/null 2>&1 && node capture.js'
done

echo "DONE screenshots in ${OUT_DIR}"
