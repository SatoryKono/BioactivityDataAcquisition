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
      process.env.GRAFANA_SCREENSHOT_SETTLE_MS || "12000",
      10,
    ),
    selectedUids: new Set(
      (process.env.GRAFANA_SCREENSHOT_UIDS || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
    scopeQuery: process.env.GRAFANA_SCREENSHOT_SCOPE_QUERY || "",
    expandCollapsedRows: /^(1|true|yes)$/i.test(
      process.env.GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS || "",
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
    } else if (arg === "--expand-collapsed-rows") {
      config.expandCollapsedRows = true;
    }
  }
  if (!Number.isFinite(config.captureTimeoutMs) || config.captureTimeoutMs <= 0) {
    config.captureTimeoutMs = Math.max(config.timeoutMs, 180000);
  }
  return config;
}

const CONFIG = parseArgs(process.argv.slice(2));
const PANEL_READY_SELECTORS = [
  '[data-testid^="data-testid Panel header"]',
  '[data-testid*="Panel header"]',
  '[data-testid="data-testid Panel header"]',
  '[data-testid="Panel header"]',
  '[data-testid$="Panel header"]',
  '[aria-label="Panel header"]',
  '[data-viz-panel-key^="panel-"]',
  '[data-panelid]',
  ".panel-title",
];
const DASHBOARD_PANEL_CONTAINER_SELECTORS = [
  "[data-panelid]",
  "[data-viz-panel-key]",
  "[data-griditem-key]",
  ".react-grid-item",
];
const SCROLL_CONTAINER_SELECTORS = [
  '[data-testid="data-testid Dashboard content"]',
  '[data-testid="dashboard-container"]',
  ".dashboard-container",
  ".scrollbar-view",
  ".main-view",
  "main",
];
const MAX_CAPTURE_VIEWPORT_HEIGHT = 12000;

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
      collapsedRowTitles: CONFIG.expandCollapsedRows
        ? panels
            .filter((panel) => panel && panel.type === "row" && panel.collapsed === true)
            .map((panel) => (typeof panel.title === "string" ? panel.title.trim() : ""))
            .filter(Boolean)
        : [],
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
  for (const selector of PANEL_READY_SELECTORS) {
    const count = await page.locator(selector).count().catch(() => 0);
    if (count > 0) {
      return { selector, count };
    }
  }
  return { selector: "", count: 0 };
}

async function waitForDashboardContent(page, dashboard, index, total) {
  console.log(`[${index}/${total}] waiting for dashboard content ${dashboard.uid} ...`);
  const selectors = PANEL_READY_SELECTORS;
  await page
    .waitForFunction(
      (readySelectors) => {
        const panelCount = readySelectors.reduce(
          (total, selector) => total + document.querySelectorAll(selector).length,
          0,
        );
        if (panelCount > 0) {
          return true;
        }
        const text = document.body ? document.body.innerText || "" : "";
        return text.includes("Review Dashboard Navigation") || text.includes("Navigation");
      },
      selectors,
      { timeout: CONFIG.timeoutMs },
    )
    .catch(() => {
      console.warn(
        `[${index}/${total}] dashboard content readiness timeout for ${dashboard.uid}; continuing with screenshot capture`,
      );
    });
}

async function setDashboardScrollPosition(page, position) {
  await page.evaluate(
    ({ scrollPosition, scrollSelectors }) => {
      const scrollables = new Set();
      for (const selector of scrollSelectors) {
        for (const element of document.querySelectorAll(selector)) {
          scrollables.add(element);
        }
      }
      for (const element of document.querySelectorAll("*")) {
        if (element.scrollHeight > element.clientHeight + 2) {
          scrollables.add(element);
        }
      }

      const documentScroller =
        document.scrollingElement || document.documentElement || document.body;
      if (documentScroller) {
        documentScroller.scrollTop = scrollPosition;
      }
      window.scrollTo(0, scrollPosition);
      if (document.body) {
        document.body.scrollTop = scrollPosition;
      }
      if (document.documentElement) {
        document.documentElement.scrollTop = scrollPosition;
      }
      for (const element of scrollables) {
        element.scrollTop = Math.min(scrollPosition, element.scrollHeight);
      }
    },
    { scrollPosition: position, scrollSelectors: SCROLL_CONTAINER_SELECTORS },
  );
}

async function dashboardCaptureMetrics(page) {
  return page.evaluate(
    ({ panelSelectors, panelContainerSelectors, scrollSelectors }) => {
      const candidateElements = new Set();

      for (const selector of panelSelectors) {
        for (const marker of document.querySelectorAll(selector)) {
          let container = null;
          for (const containerSelector of panelContainerSelectors) {
            container = marker.closest(containerSelector);
            if (container) {
              break;
            }
          }
          candidateElements.add(container || marker);
        }
      }

      let panelBottom = 0;
      for (const element of candidateElements) {
        const rect = element.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          panelBottom = Math.max(panelBottom, rect.bottom + window.scrollY);
        }
      }

      let scrollBottom = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0,
      );
      for (const selector of scrollSelectors) {
        for (const element of document.querySelectorAll(selector)) {
          const rect = element.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            scrollBottom = Math.max(scrollBottom, rect.top + element.scrollHeight);
          }
        }
      }

      return {
        panelBottom,
        scrollBottom,
        markerCount: candidateElements.size,
      };
    },
    {
      panelSelectors: PANEL_READY_SELECTORS,
      panelContainerSelectors: DASHBOARD_PANEL_CONTAINER_SELECTORS,
      scrollSelectors: SCROLL_CONTAINER_SELECTORS,
    },
  );
}

async function prepareDashboardForCapture(page, dashboard, index, total) {
  const metrics = await dashboardCaptureMetrics(page);
  const measuredBottom =
    metrics.panelBottom > 0 ? metrics.panelBottom : metrics.scrollBottom;
  const desiredHeight = Math.min(
    MAX_CAPTURE_VIEWPORT_HEIGHT,
    Math.max(900, Math.ceil(measuredBottom || CONFIG.viewport.height) + 32),
  );
  const currentViewport = page.viewportSize() || CONFIG.viewport;
  if (Math.abs(desiredHeight - currentViewport.height) > 4) {
    console.log(
      `[${index}/${total}] setting capture viewport for ${dashboard.uid} to ${CONFIG.viewport.width}x${desiredHeight} based on ${metrics.markerCount} panel marker(s) ...`,
    );
    await page.setViewportSize({
      width: CONFIG.viewport.width,
      height: desiredHeight,
    });
    await page.waitForTimeout(Math.max(250, Math.min(1000, CONFIG.settleMs)));
  }
  await setDashboardScrollPosition(page, 0);
  await page.waitForTimeout(Math.max(250, Math.min(1000, Math.floor(CONFIG.settleMs / 3))));
}

async function materializeLazyPanels(page, dashboard, index, total) {
  const scrollDelayMs = Math.max(250, Math.min(1000, Math.floor(CONFIG.settleMs / 3)));
  const step = Math.max(500, Math.floor(CONFIG.viewport.height * 0.75));
  let previousScrollHeight = 0;
  console.log(`[${index}/${total}] materializing lazy panels for ${dashboard.uid} ...`);

  for (let pass = 1; pass <= 2; pass += 1) {
    const metrics = await dashboardCaptureMetrics(page);
    const scrollHeight = Math.max(
      metrics.scrollBottom,
      metrics.panelBottom,
      CONFIG.viewport.height,
    );
    if (scrollHeight <= CONFIG.viewport.height && pass > 1) {
      break;
    }
    for (let y = 0; y <= scrollHeight; y += step) {
      await setDashboardScrollPosition(page, y);
      await page.waitForTimeout(scrollDelayMs);
    }
    await setDashboardScrollPosition(page, scrollHeight);
    await page.waitForTimeout(scrollDelayMs);

    const nextMetrics = await dashboardCaptureMetrics(page);
    const nextScrollHeight = Math.max(nextMetrics.scrollBottom, nextMetrics.panelBottom);
    if (nextScrollHeight === previousScrollHeight || nextScrollHeight === scrollHeight) {
      break;
    }
    previousScrollHeight = nextScrollHeight;
  }

  await setDashboardScrollPosition(page, 0);
  await page.waitForTimeout(scrollDelayMs);
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
  await page.setViewportSize(CONFIG.viewport);
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
  await waitForDashboardContent(page, dashboard, index, total);
  await materializeLazyPanels(page, dashboard, index, total);

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
  await prepareDashboardForCapture(page, dashboard, index, total);

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
    expand_collapsed_rows: CONFIG.expandCollapsedRows,
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
  for (const [index, dashboard] of dashboards.entries()) {
    const browser = await chromium.launch({ headless: true });
    let contextBundle = null;
    let context = null;
    try {
      contextBundle = await createBrowserContext(browser);
      context = contextBundle.context || contextBundle;
      const page = await context.newPage();
      try {
        await renderDashboard(page, dashboard, index + 1, dashboards.length);
      } finally {
        await page.close();
      }
    } finally {
      if (contextBundle && contextBundle.api) {
        await contextBundle.api.dispose();
      }
      if (context) {
        await context.close();
      }
      await browser.close();
    }
  }
  await writeManifest(dashboards);
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
