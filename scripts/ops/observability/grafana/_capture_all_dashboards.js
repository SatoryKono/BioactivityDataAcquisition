/**
 * Capture all shipped BioETL Grafana dashboards via Playwright.
 * Intended for Docker/host runs with PLAYWRIGHT_BROWSERS_PATH set when needed.
 * No default password: set GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN.
 */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const UIDS = (
  process.env.GRAFANA_SCREENSHOT_UIDS ||
  [
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-workflow-overview",
    "bioetl-alerts-slo",
    "bioetl-silver-reject-explorer",
  ].join(",")
)
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);

const base = (process.env.GRAFANA_BASE_URL || "http://host.docker.internal:3000").replace(
  /\/$/,
  "",
);
const user = process.env.GRAFANA_USERNAME || "admin";
const pass = process.env.GRAFANA_PASSWORD || "";
const token = process.env.GRAFANA_SERVICE_ACCOUNT_TOKEN || "";
const theme = (process.env.GRAFANA_SCREENSHOT_THEME || "dark").toLowerCase();
const outDir = process.env.OUT_DIR || process.env.GRAFANA_SCREENSHOT_OUTPUT_DIR || "/out";
const settleMs = Number(process.env.SETTLE_MS || 12000);
const navTimeout = Number(process.env.NAV_TIMEOUT_MS || 180000);

async function main() {
  if (!pass && !token) {
    console.error("Set GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN (no default).");
    process.exit(9);
  }
  fs.mkdirSync(outDir, { recursive: true });

  const executablePath =
    process.env.PLAYWRIGHT_EXECUTABLE_PATH ||
    process.env.CHROME_EXE ||
    process.env.CHROMIUM_PATH ||
    "";
  const launchOptions = {
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  };
  if (executablePath) {
    launchOptions.executablePath = executablePath;
  }
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1200 },
    ignoreHTTPSErrors: true,
  });
  if (token) {
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${token}` });
  }
  const page = await context.newPage();

  if (!token) {
    await page.goto(`${base}/login`, {
      waitUntil: "domcontentloaded",
      timeout: navTimeout,
    });
    await page.fill('input[name="user"]', user);
    await page.fill('input[name="password"]', pass);
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle", timeout: navTimeout }).catch(() => null),
      page.click('button[type="submit"]'),
    ]);
  }

  const results = [];
  for (const uid of UIDS) {
    const outName = `${uid}-${theme}.png`;
    const outPath = path.join(outDir, outName);
    process.stdout.write(`capturing ${uid} -> ${outPath}\n`);
    await page.goto(`${base}/d/${uid}?orgId=1&from=now-12h&to=now&theme=${theme}&kiosk`, {
      waitUntil: "networkidle",
      timeout: navTimeout,
    });
    await page.waitForTimeout(settleMs);
    await page.screenshot({ path: outPath, fullPage: true });
    const size = fs.statSync(outPath).size;
    results.push({ uid, path: outPath, size });
    process.stdout.write(`wrote ${outPath} (${size} bytes)\n`);
  }

  await browser.close();
  const manifest = {
    generated_at: new Date().toISOString(),
    base_url: base,
    theme,
    count: results.length,
    results,
  };
  fs.writeFileSync(
    path.join(outDir, "render-manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8",
  );
  process.stdout.write(`DONE ${results.length} screenshots in ${outDir}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
