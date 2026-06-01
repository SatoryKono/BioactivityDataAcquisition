const fs = require("node:fs");
const path = require("node:path");

const { chromium, request } = require("playwright");

function parseArgs(argv) {
  const config = {
    baseUrl: process.env.GRAFANA_BASE_URL || "http://localhost:3000",
    username: process.env.GRAFANA_USERNAME || "admin",
    password: process.env.GRAFANA_PASSWORD || "changeme",
    serviceAccountToken: process.env.GRAFANA_SERVICE_ACCOUNT_TOKEN || "",
    outputDir: path.resolve(
      process.env.GRAFANA_SCREENSHOT_OUTPUT_DIR ||
        path.join("reports", "observability", "grafana", "screenshots"),
    ),
    viewport: { width: 1600, height: 2200 },
    timeoutMs: Number.parseInt(
      process.env.GRAFANA_SCREENSHOT_TIMEOUT_MS || "90000",
      10,
    ),
    captureTimeoutMs: Number.parseInt(
      process.env.GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS || "0",
      10,
    ),
    settleMs: Number.parseInt(
      process.env.GRAFANA_SCREENSHOT_SETTLE_MS || "5000",
      10,
    ),
    selectedUids: new Set(
      (process.env.GRAFANA_SCREENSHOT_UIDS || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
    scopeQuery: process.env.GRAFANA_SCREENSHOT_SCOPE_QUERY || "",
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
    } else if (arg === "--capture-timeout-ms" && next) {
      config.captureTimeoutMs = Number.parseInt(next, 10);
      index += 1;
    } else if (arg === "--uids" && next) {
      config.selectedUids = new Set(
        next.split(",").map((item) => item.trim()).filter(Boolean),
      );
      index += 1;
    } else if (arg === "--scope-query" && next) {
      config.scopeQuery = next;
      index += 1;
    }
  }
  if (!Number.isFinite(config.captureTimeoutMs) || config.captureTimeoutMs <= 0) {
    config.captureTimeoutMs = Math.max(config.timeoutMs, 180000);
  }
  return config;
}

const CONFIG = parseArgs(process.argv.slice(2));

async function ensureOutputDir() {
  await fs.promises.mkdir(CONFIG.outputDir, { recursive: true });
}

function repoRoot() {
  return path.resolve(__dirname, "..", "..", "..", "..");
}

function dashboardDir() {
  return path.join(repoRoot(), "grafana", "dashboards");
}

function grafanaSlugify(title) {
  return String(title || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

async function createAuthenticatedApiContext() {
  const api = await request.newContext({ baseURL: CONFIG.baseUrl });
  const response = await api.post("/login", {
    data: { user: CONFIG.username, password: CONFIG.password },
  });
  if (!response.ok()) {
    await api.dispose();
    throw new Error(`Grafana login failed: ${response.status()} ${response.statusText()}`);
  }
  return api;
}

async function createBrowserContext(browser) {
  if (CONFIG.serviceAccountToken) {
    return {
      context: await browser.newContext({
        viewport: CONFIG.viewport,
        extraHTTPHeaders: {
          Authorization: `Bearer ${CONFIG.serviceAccountToken}`,
        },
      }),
      api: null,
    };
  }
  let api = null;
  try {
    api = await createAuthenticatedApiContext();
  } catch (error) {
    console.warn(
      `warning: Grafana login failed for Playwright fallback; continuing anonymously (${String(error && error.message ? error.message : error)})`,
    );
    return {
      context: await browser.newContext({ viewport: CONFIG.viewport }),
      api: null,
    };
  }
  const storageState = await api.storageState();
  return {
    context: await browser.newContext({
      storageState,
      viewport: CONFIG.viewport,
    }),
    api,
  };
}

function listDashboardsFromRepo() {
  const dir = dashboardDir();
  const files = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => path.join(dir, entry.name))
    .sort((left, right) => left.localeCompare(right));

  const dashboards = [];
  for (const filePath of files) {
    const payload = JSON.parse(fs.readFileSync(filePath, "utf8"));
    const uid = typeof payload.uid === "string" ? payload.uid : "";
    const title = typeof payload.title === "string" ? payload.title : uid;
    if (!uid) {
      continue;
    }
    if (CONFIG.selectedUids.size > 0 && !CONFIG.selectedUids.has(uid)) {
      continue;
    }
    const slug = grafanaSlugify(title) || uid;
    const panels = Array.isArray(payload.panels) ? payload.panels : [];
    dashboards.push({
      uid,
      title,
      url: `/d/${uid}/${slug}`,
      file: `${uid}.png`,
      collapsedRowTitles: panels
        .filter((panel) => panel && panel.type === "row" && panel.collapsed === true)
        .map((panel) => (typeof panel.title === "string" ? panel.title.trim() : ""))
        .filter(Boolean),
    });
  }
  if (dashboards.length === 0) {
    throw new Error("No local dashboard JSON files matched the current render selection");
  }
  return dashboards.sort((left, right) => left.uid.localeCompare(right.uid));
}

async function tryExpandCollapsedRow(page, title, index, total, uid) {
  const escapedTitle = JSON.stringify(title);
  const candidates = [
    page.locator(`button:has-text(${escapedTitle})`).first(),
    page.locator(`[role="button"]:has-text(${escapedTitle})`).first(),
    page.getByText(title, { exact: true }).first(),
  ];

  for (const candidate of candidates) {
    if ((await candidate.count()) === 0) {
      continue;
    }
    const visible = await candidate.isVisible().catch(() => false);
    if (!visible) {
      continue;
    }
    try {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 5000 });
      console.log(`[${index}/${total}] expanded row '${title}' in ${uid}`);
      return true;
    } catch {
      continue;
    }
  }

  console.warn(`[${index}/${total}] could not expand collapsed row '${title}' in ${uid}`);
  return false;
}

async function expandCollapsedRows(page, dashboard, index, total) {
  const titles = Array.isArray(dashboard.collapsedRowTitles)
    ? dashboard.collapsedRowTitles
    : [];
  if (titles.length === 0) {
    return;
  }

  console.log(
    `[${index}/${total}] expanding ${titles.length} collapsed row(s) for ${dashboard.uid} ...`,
  );
  let expanded = 0;
  for (const title of titles) {
    if (await tryExpandCollapsedRow(page, title, index, total, dashboard.uid)) {
      expanded += 1;
    }
  }
  console.log(
    `[${index}/${total}] expanded ${expanded}/${titles.length} collapsed row(s) for ${dashboard.uid}`,
  );
  if (expanded === 0) {
    return;
  }
  await page.waitForLoadState("networkidle", { timeout: CONFIG.timeoutMs }).catch(() => {
    console.warn(
      `[${index}/${total}] networkidle timeout after row expansion for ${dashboard.uid}; continuing`,
    );
  });
  console.log(
    `[${index}/${total}] settling expanded rows for ${dashboard.uid} for ${CONFIG.settleMs}ms ...`,
  );
  await page.waitForTimeout(CONFIG.settleMs);
}

async function countRenderedPanels(page) {
  const selectors = [
    '[data-testid^="data-testid Panel header"]',
    '[data-testid*="Panel header"]',
    '[data-testid="data-testid Panel header"]',
    '[data-testid="Panel header"]',
    '[data-testid$="Panel header"]',
    '[aria-label="Panel header"]',
    '[data-viz-panel-key^="panel-"]',
    '[data-panelid]',
    '.panel-title',
  ];
  for (const selector of selectors) {
    const count = await page.locator(selector).count().catch(() => 0);
    if (count > 0) {
      return { selector, count };
    }
  }
  return { selector: "", count: 0 };
}

function dashboardRenderUrl(dashboard) {
  const params = new URLSearchParams({ orgId: "1" });
  if (CONFIG.scopeQuery) {
    for (const [key, value] of new URLSearchParams(CONFIG.scopeQuery)) {
      params.set(key, value);
    }
  }
  return `${CONFIG.baseUrl}${dashboard.url}?${params.toString()}`;
}

async function renderDashboard(page, dashboard, index, total) {
  const target = dashboardRenderUrl(dashboard);
  console.log(`[${index}/${total}] loading ${dashboard.uid} ...`);
  console.log(`[${index}/${total}] goto ${dashboard.uid} -> ${target}`);
  await page.goto(target, {
    timeout: CONFIG.timeoutMs,
    waitUntil: "commit",
  });
  console.log(`[${index}/${total}] navigation committed ${dashboard.uid}`);
  await page
    .waitForLoadState("domcontentloaded", { timeout: CONFIG.timeoutMs })
    .then(() => {
      console.log(`[${index}/${total}] domcontentloaded ${dashboard.uid}`);
    })
    .catch(() => {
      console.warn(
        `[${index}/${total}] domcontentloaded timeout for ${dashboard.uid}; continuing with settled page wait`,
      );
    });
  console.log(`[${index}/${total}] waiting for networkidle ${dashboard.uid} ...`);
  await page.waitForLoadState("networkidle", { timeout: CONFIG.timeoutMs }).catch(() => {
    console.warn(
      `[${index}/${total}] networkidle timeout for ${dashboard.uid}; continuing with settled page wait`,
    );
  });
  console.log(
    `[${index}/${total}] settling ${dashboard.uid} for ${CONFIG.settleMs}ms ...`,
  );
  await page.waitForTimeout(CONFIG.settleMs);
  await expandCollapsedRows(page, dashboard, index, total);

  const renderedPanelEvidence = await countRenderedPanels(page);
  dashboard.renderedPanelCount = renderedPanelEvidence.count;
  dashboard.renderedPanelSelector = renderedPanelEvidence.selector;
  if (renderedPanelEvidence.count === 0) {
    console.warn(`warning: no panel headers detected for ${dashboard.uid}`);
  } else {
    console.log(
      `[${index}/${total}] detected ${renderedPanelEvidence.count} rendered panel marker(s) for ${dashboard.uid} using ${renderedPanelEvidence.selector}`,
    );
  }

  const filePath = path.join(CONFIG.outputDir, dashboard.file);
  console.log(
    `[${index}/${total}] capturing screenshot ${dashboard.uid} with timeout ${CONFIG.captureTimeoutMs}ms ...`,
  );
  await page.screenshot({
    path: filePath,
    fullPage: true,
    timeout: CONFIG.captureTimeoutMs,
    animations: "disabled",
    caret: "hide",
  });
  console.log(`rendered ${dashboard.uid} -> ${dashboard.file}`);
}

async function writeManifest(dashboards) {
  const payload = {
    generated_at: new Date().toISOString(),
    engine: "playwright",
    base_url: CONFIG.baseUrl,
    scope_query: CONFIG.scopeQuery,
    timeout_ms: CONFIG.timeoutMs,
    capture_timeout_ms: CONFIG.captureTimeoutMs,
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
  const dashboards = listDashboardsFromRepo();
  const browser = await chromium.launch({ headless: true });
  const contextBundle = await createBrowserContext(browser);
  const context = contextBundle.context || contextBundle;
  const page = await context.newPage();
  try {
    for (const [index, dashboard] of dashboards.entries()) {
      await renderDashboard(page, dashboard, index + 1, dashboards.length);
    }
    await writeManifest(dashboards);
  } finally {
    if (contextBundle.api) {
      await contextBundle.api.dispose();
    }
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
