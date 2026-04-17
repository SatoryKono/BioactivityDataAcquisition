const fs = require("node:fs");
const path = require("node:path");

const { chromium, request } = require("playwright");

const BASE_URL = process.env.GRAFANA_BASE_URL || "http://localhost:3000";
const OUTPUT_DIR = path.resolve("output", "playwright");
const VIEWPORT = { width: 1600, height: 2200 };

const DASHBOARDS = [
  { uid: "bioetl-overview-v2", title: "1-overview", file: "bioetl-overview-v2.png" },
  { uid: "bioetl-dq-v2", title: "4-data-quality", file: "bioetl-dq-v2.png" },
  {
    uid: "bioetl-provider-health-v2",
    title: "3-provider-health",
    file: "bioetl-provider-health-v2.png",
  },
  { uid: "bioetl-runtime", title: "2-runtime", file: "bioetl-runtime.png" },
];

async function ensureOutputDir() {
  await fs.promises.mkdir(OUTPUT_DIR, { recursive: true });
}

async function createAuthenticatedContext(browser) {
  const api = await request.newContext({ baseURL: BASE_URL });
  const response = await api.post("/login", {
    data: { user: "admin", password: "admin" },
  });
  if (!response.ok()) {
    throw new Error(`Grafana login failed: ${response.status()} ${response.statusText()}`);
  }
  const storageState = await api.storageState();
  await api.dispose();
  return browser.newContext({
    storageState,
    viewport: VIEWPORT,
  });
}

async function renderDashboard(page, dashboard) {
  const target = `${BASE_URL}/d/${dashboard.uid}/${dashboard.title}?orgId=1`;
  await page.goto(target, {
    timeout: 90_000,
    waitUntil: "domcontentloaded",
  });
  await page.waitForLoadState("networkidle", { timeout: 90_000 }).catch(() => {});
  await page.waitForTimeout(10_000);

  const panels = page.locator("[data-testid=\"data-testid Panel header\"]");
  if ((await panels.count()) === 0) {
    console.warn(`warning: no panel headers detected for ${dashboard.uid}`);
  }

  const filePath = path.join(OUTPUT_DIR, dashboard.file);
  await page.screenshot({
    path: filePath,
    fullPage: true,
  });
  console.log(`rendered ${dashboard.uid} -> ${dashboard.file}`);
}

async function main() {
  await ensureOutputDir();
  const browser = await chromium.launch({ headless: true });
  const context = await createAuthenticatedContext(browser);
  const page = await context.newPage();
  try {
    for (const dashboard of DASHBOARDS) {
      await renderDashboard(page, dashboard);
    }
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
