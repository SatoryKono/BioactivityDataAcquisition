const fs = require("node:fs");
const path = require("node:path");

const { chromium, request } = require("playwright");

function parseArgs(argv) {
  const config = {
    baseUrl: process.env.GRAFANA_BASE_URL || "http://localhost:3000",
    username: process.env.GRAFANA_USERNAME || "admin",
    password: process.env.GRAFANA_PASSWORD || "admin",
    outputDir: path.resolve(
      process.env.GRAFANA_SCREENSHOT_OUTPUT_DIR ||
        path.join("reports", "observability", "grafana", "screenshots"),
    ),
    viewport: { width: 1600, height: 2200 },
    timeoutMs: Number.parseInt(
      process.env.GRAFANA_SCREENSHOT_TIMEOUT_MS || "90000",
      10,
    ),
    selectedUids: new Set(
      (process.env.GRAFANA_SCREENSHOT_UIDS || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--base-url" && next) {
      config.baseUrl = next;
      index += 1;
    } else if (arg === "--username" && next) {
      config.username = next;
      index += 1;
    } else if (arg === "--password" && next) {
      config.password = next;
      index += 1;
    } else if (arg === "--output-dir" && next) {
      config.outputDir = path.resolve(next);
      index += 1;
    } else if (arg === "--timeout-ms" && next) {
      config.timeoutMs = Number.parseInt(next, 10);
      index += 1;
    } else if (arg === "--uids" && next) {
      config.selectedUids = new Set(
        next.split(",").map((item) => item.trim()).filter(Boolean),
      );
      index += 1;
    }
  }
  return config;
}

const CONFIG = parseArgs(process.argv.slice(2));

async function ensureOutputDir() {
  await fs.promises.mkdir(CONFIG.outputDir, { recursive: true });
}

async function createAuthenticatedContext(browser) {
  const api = await request.newContext({ baseURL: CONFIG.baseUrl });
  const response = await api.post("/login", {
    data: { user: CONFIG.username, password: CONFIG.password },
  });
  if (!response.ok()) {
    throw new Error(`Grafana login failed: ${response.status()} ${response.statusText()}`);
  }
  const storageState = await api.storageState();
  await api.dispose();
  return browser.newContext({
    storageState,
    viewport: CONFIG.viewport,
  });
}

async function listDashboards() {
  const api = await request.newContext({ baseURL: CONFIG.baseUrl });
  try {
    const response = await api.get("/api/search?type=dash-db", {
      headers: {
        Authorization: `Basic ${Buffer.from(`${CONFIG.username}:${CONFIG.password}`).toString("base64")}`,
      },
    });
    if (!response.ok()) {
      throw new Error(`Grafana search failed: ${response.status()} ${response.statusText()}`);
    }
    const payload = await response.json();
    return payload
      .filter((item) => item && typeof item.uid === "string" && typeof item.url === "string")
      .filter(
        (item) => CONFIG.selectedUids.size === 0 || CONFIG.selectedUids.has(item.uid),
      )
      .map((item) => ({
        uid: item.uid,
        title: typeof item.title === "string" ? item.title : item.uid,
        url: item.url,
        file: `${item.uid}.png`,
      }))
      .sort((left, right) => left.uid.localeCompare(right.uid));
  } finally {
    await api.dispose();
  }
}

async function renderDashboard(page, dashboard) {
  const target = `${CONFIG.baseUrl}${dashboard.url}?orgId=1`;
  await page.goto(target, {
    timeout: CONFIG.timeoutMs,
    waitUntil: "domcontentloaded",
  });
  await page.waitForLoadState("networkidle", { timeout: CONFIG.timeoutMs }).catch(() => {});
  await page.waitForTimeout(10_000);

  const panels = page.locator("[data-testid=\"data-testid Panel header\"]");
  if ((await panels.count()) === 0) {
    console.warn(`warning: no panel headers detected for ${dashboard.uid}`);
  }

  const filePath = path.join(CONFIG.outputDir, dashboard.file);
  await page.screenshot({
    path: filePath,
    fullPage: true,
  });
  console.log(`rendered ${dashboard.uid} -> ${dashboard.file}`);
}

async function writeManifest(dashboards) {
  const payload = {
    generated_at: new Date().toISOString(),
    engine: "playwright",
    base_url: CONFIG.baseUrl,
    timeout_ms: CONFIG.timeoutMs,
    dashboards,
  };
  await fs.promises.writeFile(
    path.join(CONFIG.outputDir, "render-manifest.json"),
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf8",
  );
}

async function main() {
  await ensureOutputDir();
  const dashboards = await listDashboards();
  const browser = await chromium.launch({ headless: true });
  const context = await createAuthenticatedContext(browser);
  const page = await context.newPage();
  try {
    for (const dashboard of dashboards) {
      await renderDashboard(page, dashboard);
    }
    await writeManifest(dashboards);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  const message = String(error && error.message ? error.message : error);
  if (message.includes("error while loading shared libraries")) {
    console.error(
      "Playwright fallback could not launch Chromium because required shared",
      "libraries are missing on the host. Install the standard headless",
      "Chromium runtime packages such as libnspr4, libnss3, and libasound2,",
      "then rerun rerender-grafana.",
    );
  }
  console.error(error);
  process.exit(1);
});
