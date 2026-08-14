const fs = require("node:fs");
const crypto = require("node:crypto");
const path = require("node:path");

// Lazy-load Playwright so pure helpers (e.g. classifyPanelTerminalEvidence) can be
// required from unit tests without paying Chromium package resolve cost. On this
// host, eager `require("playwright")` can hang for >60s (GDrive/NODE_PATH paths).
let _playwright = null;
const MIN_PANEL_BODY_FONT_PX = 16;
const MIN_PANEL_TITLE_FONT_PX = (14 * 4) / 3;

function playwright() {
  if (_playwright === null) {
    _playwright = require("playwright");
  }
  return _playwright;
}

function defaultScreenshotConfig() {
  return {
    baseUrl: process.env.GRAFANA_BASE_URL || "http://localhost:3000",
    username: process.env.GRAFANA_USERNAME || "admin",
    password: process.env.GRAFANA_PASSWORD || "",
    serviceAccountToken: process.env.GRAFANA_SERVICE_ACCOUNT_TOKEN || "",
    outputDir: path.resolve(
      process.env.GRAFANA_SCREENSHOT_OUTPUT_DIR ||
        path.join("reports", "observability", "grafana", "screenshots"),
    ),
    viewport: {
      width: Number.parseInt(process.env.GRAFANA_SCREENSHOT_WIDTH || "1600", 10),
      height: Number.parseInt(process.env.GRAFANA_SCREENSHOT_HEIGHT || "2200", 10),
    },
    theme: (process.env.GRAFANA_SCREENSHOT_THEME || "dark").trim().toLowerCase(),
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
    expandCollapsedRows: !/^(0|false|no)$/i.test(
      process.env.GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS || "true",
    ),
    captureSurface: (
      process.env.GRAFANA_SCREENSHOT_CAPTURE_SURFACE || "full"
    ).trim().toLowerCase(),
    kioskMode: (
      process.env.GRAFANA_SCREENSHOT_KIOSK_MODE || "off"
    ).trim().toLowerCase(),
    browserZoom: Number.parseInt(
      process.env.GRAFANA_SCREENSHOT_BROWSER_ZOOM || "100",
      10,
    ),
    navigationOnly: /^(1|true|yes)$/i.test(
      process.env.GRAFANA_SCREENSHOT_NAVIGATION_ONLY || "false",
    ),
  };
}

function applyScreenshotArg(config, arg, next) {
  const valueArgs = {
    "--base-url": (value) => {
      config.baseUrl = value;
    },
    "--username": (value) => {
      config.username = value;
    },
    "--password": (value) => {
      config.password = value;
    },
    "--output-dir": (value) => {
      config.outputDir = path.resolve(value);
    },
    "--width": (value) => {
      config.viewport.width = Number.parseInt(value, 10);
    },
    "--height": (value) => {
      config.viewport.height = Number.parseInt(value, 10);
    },
    "--theme": (value) => {
      config.theme = value.trim().toLowerCase();
    },
    "--timeout-ms": (value) => {
      config.timeoutMs = Number.parseInt(value, 10);
    },
    "--capture-timeout-ms": (value) => {
      config.captureTimeoutMs = Number.parseInt(value, 10);
    },
    "--uids": (value) => {
      config.selectedUids = new Set(
        value.split(",").map((item) => item.trim()).filter(Boolean),
      );
    },
    "--scope-query": (value) => {
      config.scopeQuery = value;
    },
    "--capture-surface": (value) => {
      config.captureSurface = value.trim().toLowerCase();
    },
    "--kiosk-mode": (value) => {
      config.kioskMode = value.trim().toLowerCase();
    },
    "--browser-zoom": (value) => {
      config.browserZoom = Number.parseInt(value, 10);
    },
  };
  if (Object.hasOwn(valueArgs, arg) && next) {
    valueArgs[arg](next);
    return 1;
  }
  if (arg === "--expand-collapsed-rows") {
    config.expandCollapsedRows = true;
    return 0;
  }
  if (arg === "--no-expand-collapsed-rows") {
    config.expandCollapsedRows = false;
    return 0;
  }
  if (arg === "--navigation-only") {
    config.navigationOnly = true;
    return 0;
  }
  return 0;
}

function validateScreenshotConfig(config) {
  if (!Number.isFinite(config.captureTimeoutMs) || config.captureTimeoutMs <= 0) {
    config.captureTimeoutMs = Math.max(config.timeoutMs, 180000);
  }
  if (!Number.isInteger(config.viewport.width) || config.viewport.width <= 0) {
    throw new Error("Playwright screenshot width must be a positive integer");
  }
  if (!Number.isInteger(config.viewport.height) || config.viewport.height <= 0) {
    throw new Error("Playwright screenshot height must be a positive integer");
  }
  if (!new Set(["dark", "light"]).has(config.theme)) {
    throw new Error("Playwright screenshot theme must be 'dark' or 'light'");
  }
  if (!new Set(["viewport", "full"]).has(config.captureSurface)) {
    throw new Error("Playwright capture surface must be 'viewport' or 'full'");
  }
  if (!new Set(["off", "full", "tv"]).has(config.kioskMode)) {
    throw new Error("Playwright kiosk mode must be 'off', 'full', or 'tv'");
  }
  if (
    !Number.isInteger(config.browserZoom) ||
    config.browserZoom < 50 ||
    config.browserZoom > 200
  ) {
    throw new Error("Playwright browser zoom must be an integer from 50 to 200");
  }
  return config;
}

function parseArgs(argv) {
  const config = defaultScreenshotConfig();
  for (let index = 0; index < argv.length; index += 1) {
    index += applyScreenshotArg(config, argv[index], argv[index + 1]);
  }
  return validateScreenshotConfig(config);
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
const TERMINAL_POLL_INTERVAL_MS = 500;
const TERMINAL_CLASSIFICATIONS = new Set([
  "healthy",
  "explicit-error",
  "valid-empty",
  "telemetry-absent",
  "not-applicable",
  "incomplete",
  "loading",
  "blank",
  "contradictory",
]);

function classifyStaticPanelEvidence(bodyText, hasVisualEvidence) {
  return bodyText || hasVisualEvidence
    ? {
        classification: "healthy",
        reason: "static operator copy reached a rendered state",
      }
    : {
        classification: "blank",
        reason: "text panel body has no visible content",
      };
}

function classifyLeadingEmptyState(bodyText, hasErrorIcon) {
  const leadingValidEmpty = /^(?:VALID EMPTY|EMPTY RESULT)\b/i.test(bodyText);
  const leadingNoMatch =
    /^(?:NO MATCHING(?: SCOPE| DATA| ROWS?)?|NOT APPLICABLE|N\/A)\b/i.test(bodyText);
  if (!leadingValidEmpty && !leadingNoMatch) {
    return null;
  }
  if (hasErrorIcon) {
    return {
      classification: "contradictory",
      reason: "panel combines an error marker with a non-error empty state",
    };
  }
  return leadingValidEmpty
    ? {
        classification: "valid-empty",
        reason: "panel explicitly identifies a successful empty result",
      }
    : {
        classification: "not-applicable",
        reason: "panel explicitly identifies an unmatched or inapplicable scope",
      };
}

function classifyQueryPanelTerminalEvidence(
  bodyText,
  hasErrorIcon,
  hasVisualEvidence,
) {
  if (/^(?:ERROR|QUERY ERROR|DATASOURCE ERROR|REQUEST ERROR)\b/i.test(bodyText)) {
    return {
      classification: "explicit-error",
      reason: "panel exposes an explicit terminal query or datasource error",
    };
  }
  const emptyState = classifyLeadingEmptyState(bodyText, hasErrorIcon);
  if (emptyState) {
    return emptyState;
  }
  if (hasErrorIcon) {
    return {
      classification: "explicit-error",
      reason: "panel exposes a visible terminal error marker",
    };
  }
  if (/^(?:LOADING|PENDING QUERY|WAITING FOR DATA)\b/i.test(bodyText)) {
    return {
      classification: "loading",
      reason: "panel copy still identifies a loading state",
    };
  }
  if (/^(?:TELEMETRY ABSENT|TELEMETRY MISSING)\b/i.test(bodyText)) {
    return {
      classification: "telemetry-absent",
      reason: "panel explicitly identifies missing telemetry",
    };
  }
  if (
    /^(?:UNKNOWN|INCOMPLETE|NOT RESOLVED|UNRESOLVED)\b/i.test(bodyText) ||
    /^(?:NO DATA|NO\b|NOT FOUND\b)/i.test(bodyText)
  ) {
    return {
      classification: "incomplete",
      reason: "panel explicitly identifies incomplete or unresolved evidence",
    };
  }
  if (!bodyText && !hasVisualEvidence) {
    return {
      classification: "blank",
      reason: "panel body has no visible text or visual evidence",
    };
  }
  return {
    classification: "healthy",
    reason: "panel body reached a visible terminal rendered state",
  };
}

function classifyPanelTerminalEvidence(evidence) {
  const bodyText = String(evidence.bodyText || "").replace(/\s+/g, " ").trim();
  const supportsQueryTerminalState = evidence.type !== "text";
  const hasLoadingMarker = evidence.hasLoadingMarker === true;
  const hasErrorIcon = evidence.hasErrorIcon === true;
  const hasVisualEvidence = evidence.hasVisualEvidence === true;

  // Grafana can retain an internal loading marker after a viewport resize even
  // when the panel-local terminal value/table is already visible. Treat the
  // marker as blocking only while the panel has no rendered terminal evidence;
  // explicit LOADING/PENDING copy remains blocking below.
  if (hasLoadingMarker && !bodyText && !hasVisualEvidence) {
    return {
      classification: "loading",
      reason: "panel exposes a loading marker without rendered terminal evidence",
    };
  }
  if (!supportsQueryTerminalState) {
    return classifyStaticPanelEvidence(bodyText, hasVisualEvidence);
  }
  return classifyQueryPanelTerminalEvidence(
    bodyText,
    hasErrorIcon,
    hasVisualEvidence,
  );
}

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
  // Character-class + fixed quantifiers avoid super-linear backtracking (S8786).
  return String(title || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-/, "")
    .replace(/-$/, "");
}


function isMateriallyBlankPng(buffer) {
  // Fail-closed blank-screen detector for #6686.
  // Samples RGB bytes after PNG decode when possible; falls back to tiny-file heuristic.
  try {
    if (!Buffer.isBuffer(buffer) || buffer.length < 1000) {
      return true;
    }
    // IHDR width/height already validated elsewhere; use raw byte entropy proxy:
    // near-uniform screenshots compress extremely well / have low unique byte diversity.
    const sampleStep = Math.max(1, Math.floor(buffer.length / 4000));
    const counts = new Map();
    let samples = 0;
    for (let i = 0; i < buffer.length; i += sampleStep) {
      const b = buffer[i];
      counts.set(b, (counts.get(b) || 0) + 1);
      samples += 1;
    }
    if (samples < 100) {
      return true;
    }
    let top = 0;
    for (const v of counts.values()) {
      if (v > top) top = v;
    }
    const dominance = top / samples;
    // Dominant single byte across sample => blank/flat canvas.
    return dominance >= 0.92 && counts.size <= 24;
  } catch (err) {
    // Decode/sample failures are treated as non-blank so the outer PNG gate
    // (signature/size) remains the hard fail path rather than false blank.
    console.warn(
      `isMateriallyBlankPng: blank-detector failed (${err?.message ?? err}); treating as non-blank`,
    );
    return false;
  }
}

function pngEvidence(buffer) {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(signature)) {
    throw new Error("captured screenshot is not a valid PNG with an IHDR header");
  }
  return {
    bytes: buffer.length,
    sha256: crypto.createHash("sha256").update(buffer).digest("hex"),
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

function requiredNonRowPanels(panels, includeCollapsedRows) {
  const required = [];
  for (const panel of panels) {
    if (!panel || typeof panel !== "object") {
      continue;
    }
    if (panel.type === "row") {
      if (includeCollapsedRows && Array.isArray(panel.panels)) {
        required.push(...requiredNonRowPanels(panel.panels, true));
      }
      continue;
    }
    if (!Number.isInteger(panel.id)) {
      continue;
    }
    const pluginOptions =
      panel.options && typeof panel.options === "object" ? panel.options : {};
    const displayTitle =
      typeof pluginOptions.bioetlDisplayTitle === "string"
        ? pluginOptions.bioetlDisplayTitle.trim()
        : "";
    required.push({
      id: panel.id,
      title:
        displayTitle ||
        (typeof panel.title === "string" ? panel.title.trim() : ""),
      type: typeof panel.type === "string" ? panel.type : "unknown",
    });
  }
  return required;
}

async function createAuthenticatedApiContext() {
  const api = await playwright().request.newContext({ baseURL: CONFIG.baseUrl });
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
        deviceScaleFactor: 1,
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
      `warning: Grafana login failed for Playwright fallback; continuing anonymously (${String(error?.message ?? error)})`,
    );
    return {
      context: await browser.newContext({
        viewport: CONFIG.viewport,
        deviceScaleFactor: 1,
      }),
      api: null,
    };
  }
  const storageState = await api.storageState();
  return {
    context: await browser.newContext({
      storageState,
      viewport: CONFIG.viewport,
      deviceScaleFactor: 1,
    }),
    api,
  };
}

function dashboardEntryFromPayload(payload) {
  const uid = typeof payload.uid === "string" ? payload.uid : "";
  const title = typeof payload.title === "string" ? payload.title : uid;
  if (!uid) {
    return null;
  }
  if (CONFIG.selectedUids.size > 0 && !CONFIG.selectedUids.has(uid)) {
    return null;
  }
  const slug = grafanaSlugify(title) || uid;
  const panels = Array.isArray(payload.panels) ? payload.panels : [];
  const allRequiredPanels = requiredNonRowPanels(
    panels,
    CONFIG.expandCollapsedRows,
  );
  const requiredPanels = CONFIG.navigationOnly
    ? allRequiredPanels.filter((panel) => panel.id === 1000)
    : allRequiredPanels;
  if (CONFIG.navigationOnly && requiredPanels.length !== 1) {
    throw new Error(`${uid} must expose exactly one navigation panel id=1000`);
  }
  if (
    uid === "bioetl-silver-reject-explorer" &&
    !requiredPanels.some((panel) => panel.id === 13)
  ) {
    throw new Error(
      "Silver Reject Explorer must expose required Backend Health panel 13",
    );
  }
  const collapsedRowTitles = CONFIG.expandCollapsedRows
    ? panels
        .filter((panel) => panel?.type === "row" && panel.collapsed === true)
        .map((panel) => (typeof panel.title === "string" ? panel.title.trim() : ""))
        .filter(Boolean)
    : [];
  return {
    uid,
    title,
    url: `/d/${uid}/${slug}`,
    file: `${uid}.png`,
    requiredPanels,
    requiredTerminalPanelIds:
      uid === "bioetl-silver-reject-explorer" ? [13] : [],
    collapsedRowTitles,
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
    const entry = dashboardEntryFromPayload(payload);
    if (entry) {
      dashboards.push(entry);
    }
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
  if (expanded !== titles.length) {
    throw new Error(
      `Collapsed-row expansion failed for ${dashboard.uid}: expanded ${expanded}/${titles.length}`,
    );
  }
  // Auto-refreshing Grafana dashboards may never become globally network-idle.
  // Row expansion only needs a short bounded grace period; panel-local terminal
  // polling below is the authoritative readiness gate.
  const networkIdleTimeoutMs = Math.max(3000, Math.min(CONFIG.timeoutMs, 15000));
  await page.waitForLoadState("networkidle", { timeout: networkIdleTimeoutMs }).catch(() => {
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

async function detectActualTheme(page) {
  return page.evaluate(() => {
    const themeFromTokens = (tokens) => {
      if (/(^|[\s_-])dark($|[\s_-])/.test(tokens)) {
        return "dark";
      }
      if (/(^|[\s_-])light($|[\s_-])/.test(tokens)) {
        return "light";
      }
      return "";
    };
    const themeFromScheme = (scheme) => {
      if (scheme.includes("dark") && !scheme.includes("light")) {
        return "dark";
      }
      if (scheme.includes("light") && !scheme.includes("dark")) {
        return "light";
      }
      return "";
    };
    const themeFromBackground = (element) => {
      if (!element) {
        return "";
      }
      const rgbaPattern = /rgba?\(\s*(\d+)\D+(\d+)\D+(\d+)(?:\D+([\d.]+))?/;
      const match = rgbaPattern.exec(getComputedStyle(element).backgroundColor);
      if (!match || (match[4] !== undefined && Number.parseFloat(match[4]) === 0)) {
        return "";
      }
      const red = Number.parseInt(match[1], 10);
      const green = Number.parseInt(match[2], 10);
      const blue = Number.parseInt(match[3], 10);
      const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue;
      return luminance < 128 ? "dark" : "light";
    };

    const root = document.documentElement;
    const body = document.body;
    const tokens = [
      root ? root.className : "",
      body ? body.className : "",
      root?.dataset?.theme || "",
      body?.dataset?.theme || "",
    ]
      .join(" ")
      .toLowerCase();
    const fromTokens = themeFromTokens(tokens);
    if (fromTokens) {
      return fromTokens;
    }
    const scheme = root ? getComputedStyle(root).colorScheme.toLowerCase() : "";
    const fromScheme = themeFromScheme(scheme);
    if (fromScheme) {
      return fromScheme;
    }
    return themeFromBackground(body) || themeFromBackground(root) || "unknown";
  });
}

async function collectPanelTerminalStates(page, dashboard) {
  const states = await page.evaluate(({ requiredPanels }) => {
    const normalize = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const headerIdentityText = (header) =>
      normalize(
        [
          header.innerText || header.textContent || "",
          header.dataset?.testid || "",
          header.getAttribute("aria-label") || "",
          header.getAttribute("title") || "",
        ].join(" "),
      );
    const locateBySelectors = (selectors) => {
      for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element) {
          return { element, selector };
        }
      }
      return null;
    };
    const locateByTitle = (panelTitle) => {
      if (!panelTitle) {
        return null;
      }
      const headerSelectors = [
        '[data-testid^="data-testid Panel header"]',
        '[data-testid*="Panel header"]',
        '[aria-label="Panel header"]',
        '[aria-label*="Panel header"]',
        ".panel-title",
      ];
      for (const headerSelector of headerSelectors) {
        for (const header of document.querySelectorAll(headerSelector)) {
          if (!headerIdentityText(header).includes(panelTitle)) {
            continue;
          }
          const container = header.closest(
            '[data-panelid],[data-viz-panel-key],[data-griditem-key],.react-grid-item',
          );
          if (container) {
            return { element: container, selector: headerSelector + " -> closest" };
          }
        }
      }
      return null;
    };
    const panelContainer = (panelId, panelTitle) =>
      locateBySelectors([
        `[data-panelid="${panelId}"]`,
        `[data-viz-panel-key="panel-${panelId}"]`,
        `[data-griditem-key="grid-item-${panelId}"]`,
        `[data-griditem-key="panel-${panelId}"]`,
        `[data-griditem-key="${panelId}"]`,
        `[data-testid="panel-${panelId}"]`,
      ]) ||
      locateByTitle(panelTitle) || { element: null, selector: "" };
    const panelSurface = (element) =>
      element.matches('[data-testid^="data-testid Panel header"]')
        ? element
        : element.querySelector('[data-testid^="data-testid Panel header"]') ||
          element;
    const panelContent = (element) => {
      const selectors = [
        '[data-testid="data-testid panel content"]',
        '[data-testid="panel content"]',
        '[data-testid$="panel content"]',
        ".panel-content",
      ];
      for (const selector of selectors) {
        const content = element.querySelector(selector);
        if (content) {
          return { element: content, selector };
        }
      }
      return { element: null, selector: "" };
    };
    const headerContentSelector = [
      '[data-testid="header-container"]',
      '[data-testid="title-items-container"]',
      ".panel-title-container",
      ".panel-header",
      ".panel-title",
    ].join(",");
    const loadingSelector = [
      '[aria-label*="loading" i]',
      '[data-testid*="loading" i]',
      '[aria-busy="true"]',
      ".panel-loading",
      '[class*="panel-loading-bar"]',
    ].join(",");
    const errorSelector = [
      '[aria-label="error" i]',
      '[aria-label^="error:" i]',
      '[data-testid*="panel-alert" i]',
      '[data-testid*="query-error" i]',
      '[data-testid*="datasource-error" i]',
      ".panel-alert-error",
      '[class*="panel-alert"]',
    ].join(",");
    const visualSelector = [
      "canvas",
      "svg",
      "img",
      "table",
      '[role="table"]',
      '[role="grid"]',
    ].join(",");
    const isElementVisible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0"
      );
    };
    const hasVisibleMarker = (root, selector, excludeHeaderContent = false) =>
      Array.from(root.querySelectorAll(selector)).some((element) => {
        if (excludeHeaderContent && element.closest(headerContentSelector)) {
          return false;
        }
        return isElementVisible(element);
      });
    const availablePanelHeaders = Array.from(
      document.querySelectorAll(
        '[data-testid*="Panel header"],[aria-label*="Panel header"]',
      ),
    )
      .slice(0, 5)
      .map((header) => headerIdentityText(header));

    return requiredPanels.map((panel) => {
      const located = panelContainer(panel.id, panel.title);
      if (!located.element) {
        return {
          ...panel,
          selector: "",
          bodyText: "",
          hasLoadingMarker: true,
          hasErrorIcon: false,
          hasVisualEvidence: false,
          missingReason:
            "panel container is not rendered yet; visible headers=" +
            JSON.stringify(availablePanelHeaders),
        };
      }

      const surface = panelSurface(located.element);
      const content = panelContent(surface);
      const bodyText = content.element
        ? normalize(content.element.innerText || content.element.textContent || "")
        : "";

      return {
        ...panel,
        selector: located.selector,
        contentSelector: content.selector,
        bodyText: bodyText.slice(0, 500),
        hasLoadingMarker: hasVisibleMarker(surface, loadingSelector, true),
        hasErrorIcon: hasVisibleMarker(surface, errorSelector, true),
        hasVisualEvidence: content.element
          ? hasVisibleMarker(content.element, visualSelector)
          : false,
      };
    });
  }, { requiredPanels: dashboard.requiredPanels });

  const classifiedStates = states.map((state) => {
    const classification = classifyPanelTerminalEvidence(state);
    return {
      ...state,
      ...classification,
      reason: state.missingReason || classification.reason,
    };
  });
  for (const state of classifiedStates) {
    if (!TERMINAL_CLASSIFICATIONS.has(state.classification)) {
      throw new Error(
        `Unknown panel terminal classification '${state.classification}' for ${dashboard.uid} panel ${state.id}`,
      );
    }
  }
  return classifiedStates;
}

function terminalStateSummary(dashboard, panelStates, status) {
  const counts = {};
  for (const state of panelStates) {
    counts[state.classification] = (counts[state.classification] || 0) + 1;
  }
  return {
    status,
    checkedPanelCount: panelStates.length,
    requiredPanelCount: dashboard.requiredPanels.length,
    requiredTerminalPanelIds: dashboard.requiredTerminalPanelIds,
    classificationCounts: counts,
    panelStates,
  };
}

const ACCEPTED_TERMINAL_CLASSIFICATIONS = new Set([
  "healthy",
  "explicit-error",
  "valid-empty",
  "telemetry-absent",
  "not-applicable",
  "incomplete",
]);

function requiredTerminalStatesAccepted(dashboard, panelStates) {
  return dashboard.requiredTerminalPanelIds.every((panelId) => {
    const state = panelStates.find((item) => item.id === panelId);
    return Boolean(state && ACCEPTED_TERMINAL_CLASSIFICATIONS.has(state.classification));
  });
}

async function validateDashboardTerminalStates(page, dashboard, index, total) {
  // HTTP-backed forensic panels can legitimately settle after Prometheus panels,
  // especially while an observability campaign is writing evidence. Keep the
  // wait bounded by the caller timeout, but do not fail a full-surface audit at
  // the old 15 second cap while those panels are still transitioning.
  const timeoutMs = Math.max(3000, Math.min(CONFIG.timeoutMs, 60000));
  const deadline = Date.now() + timeoutMs;
  let panelStates = [];

  while (Date.now() <= deadline) {
    panelStates = await collectPanelTerminalStates(page, dashboard);
    if (panelStates.some((state) => state.classification === "contradictory")) {
      return terminalStateSummary(dashboard, panelStates, "error");
    }
    const pending = panelStates.filter((state) =>
      new Set(["blank", "loading"]).has(state.classification),
    );
    if (pending.length === 0) {
      if (!requiredTerminalStatesAccepted(dashboard, panelStates)) {
        return terminalStateSummary(dashboard, panelStates, "error");
      }
      console.log(
        `[${index}/${total}] terminal-state validation passed for ${dashboard.uid} (${panelStates.length} required non-row panel(s))`,
      );
      return terminalStateSummary(dashboard, panelStates, "ok");
    }
    await page.waitForTimeout(TERMINAL_POLL_INTERVAL_MS);
  }

  return terminalStateSummary(dashboard, panelStates, "error");
}

function describeTerminalStateFailure(dashboard) {
  const validation = dashboard.terminalStateValidation || {};
  const states = Array.isArray(validation.panelStates)
    ? validation.panelStates
    : [];
  const failures = states
    .filter((state) =>
      new Set(["blank", "loading", "contradictory"]).has(state.classification),
    )
    .map((state) => {
      const evidence = [state.reason, state.bodyText]
        .filter(Boolean)
        .join("; ")
        .slice(0, 240);
      const titleSuffix = state.title ? " (" + state.title + ")" : "";
      const evidenceSuffix = evidence ? " [" + evidence + "]" : "";
      return (
        "panel " +
        state.id +
        titleSuffix +
        ": " +
        state.classification +
        evidenceSuffix
      );
    });
  return failures.length > 0
    ? failures.join("; ")
    : "required terminal panel evidence is missing or invalid";
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
      const resolveContainer = (marker, containerSelectors) =>
        containerSelectors
          .map((selector) => marker.closest(selector))
          .find(Boolean) || marker;

      const visibleBottom = (elements, project) => {
        let bottom = 0;
        for (const element of elements) {
          const rect = element.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) {
            continue;
          }
          bottom = Math.max(bottom, project(element, rect));
        }
        return bottom;
      };

      const candidateElements = new Set();
      for (const selector of panelSelectors) {
        for (const marker of document.querySelectorAll(selector)) {
          candidateElements.add(resolveContainer(marker, panelContainerSelectors));
        }
      }

      const panelBottom = visibleBottom(
        candidateElements,
        (_element, rect) => rect.bottom + window.scrollY,
      );

      const scrollElements = [];
      for (const selector of scrollSelectors) {
        scrollElements.push(...document.querySelectorAll(selector));
      }
      const scrollBottom = Math.max(
        document.body?.scrollHeight || 0,
        document.documentElement?.scrollHeight || 0,
        visibleBottom(
          scrollElements,
          (element, rect) => rect.top + element.scrollHeight,
        ),
      );

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
  if (CONFIG.captureSurface !== "full") {
    return false;
  }
  const metrics = await dashboardCaptureMetrics(page);
  const measuredBottom =
    metrics.panelBottom > 0 ? metrics.panelBottom : metrics.scrollBottom;
  const desiredHeight = Math.min(
    MAX_CAPTURE_VIEWPORT_HEIGHT,
    Math.max(900, Math.ceil(measuredBottom || CONFIG.viewport.height) + 32),
  );
  dashboard.captureHeight = desiredHeight;
  const currentViewport = page.viewportSize() || CONFIG.viewport;
  let viewportChanged = false;
  if (desiredHeight > currentViewport.height + 4) {
    console.log(
      `[${index}/${total}] setting capture viewport for ${dashboard.uid} to ${CONFIG.viewport.width}x${desiredHeight} based on ${metrics.markerCount} panel marker(s) ...`,
    );
    await page.setViewportSize({
      width: CONFIG.viewport.width,
      height: desiredHeight,
    });
    viewportChanged = true;
    await page.waitForTimeout(Math.max(250, Math.min(1000, CONFIG.settleMs)));
  }
  await setDashboardScrollPosition(page, 0);
  await page.waitForTimeout(Math.max(250, Math.min(1000, Math.floor(CONFIG.settleMs / 3))));
  return viewportChanged;
}

async function settleDashboardAfterViewportChange(page, dashboard, index, total) {
  console.log(
    `[${index}/${total}] settling ${dashboard.uid} after capture viewport change for ${CONFIG.settleMs}ms ...`,
  );
  await page.waitForTimeout(CONFIG.settleMs);
  await waitForDashboardContent(page, dashboard, index, total);
  await materializeLazyPanels(page, dashboard, index, total);
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
  // Freeze dashboard auto-refresh during audit capture. Otherwise a 30s refresh
  // can restart a subset of 50+ expanded-row queries while terminal-state
  // validation is polling, producing non-deterministic "loading" evidence.
  const params = new URLSearchParams({
    orgId: "1",
    theme: CONFIG.theme,
    refresh: "off",
  });
  if (CONFIG.scopeQuery) {
    for (const [key, value] of new URLSearchParams(CONFIG.scopeQuery)) {
      params.set(key, value);
    }
  }
  if (CONFIG.kioskMode === "full") {
    params.set("kiosk", "1");
  } else if (CONFIG.kioskMode === "tv") {
    params.set("kiosk", "tv");
  }
  return `${CONFIG.baseUrl}${dashboard.url}?${params.toString()}`;
}

async function applyBrowserZoom(page) {
  await page.evaluate((zoomPercent) => {
    document.documentElement.style.zoom = `${zoomPercent}%`;
  }, CONFIG.browserZoom);
}

async function detectBrowserAndKioskState(page) {
  return page.evaluate(({ requestedZoom, requestedKiosk }) => {
    const visible = (element) => {
      if (!element) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.display !== "none" &&
        style.visibility !== "hidden"
      );
    };
    const url = new URL(window.location.href);
    const kioskParam = url.searchParams.get("kiosk");
    const chromeSelectors = [
      '[data-testid="sidemenu"]',
      '[data-testid="navbarmenu"]',
      '[aria-label="Main menu"]',
    ];
    const visibleChrome = chromeSelectors.some((selector) =>
      visible(document.querySelector(selector)),
    );
    let actualKiosk = "off";
    if (kioskParam === "tv") actualKiosk = "tv";
    if (kioskParam === "1" || kioskParam === "true" || kioskParam === "") {
      actualKiosk = url.searchParams.has("kiosk") ? "full" : "off";
    }
    return {
      requestedZoom,
      cssZoom: getComputedStyle(document.documentElement).zoom || "1",
      visualViewportScale: window.visualViewport?.scale || 1,
      devicePixelRatio: window.devicePixelRatio,
      requestedKiosk,
      actualKiosk,
      kioskParam,
      visibleGrafanaChrome: visibleChrome,
    };
  }, { requestedZoom: CONFIG.browserZoom, requestedKiosk: CONFIG.kioskMode });
}

async function collectLayoutGeometry(page, dashboard) {
  return page.evaluate(({ requiredPanels, viewport }) => {
    const round = (value) => Math.round(value * 10) / 10;
    const panelGeometry = {};
    for (const panel of requiredPanels) {
      const element =
        document.querySelector(`[data-panelid="${panel.id}"]`) ||
        document.querySelector(`[data-viz-panel-key="panel-${panel.id}"]`) ||
        document.querySelector(`[data-griditem-key="grid-item-${panel.id}"]`);
      if (!element) continue;
      const rect = element.getBoundingClientRect();
      panelGeometry[String(panel.id)] = {
        x: round(rect.x),
        y: round(rect.y + window.scrollY),
        width: round(rect.width),
        height: round(rect.height),
      };
    }
    const documentWidth = Math.max(
      document.documentElement.scrollWidth,
      document.body?.scrollWidth || 0,
    );
    return {
      viewport,
      documentWidth,
      horizontalOverflow: documentWidth > viewport.width + 2,
      panelGeometry,
    };
  }, { requiredPanels: dashboard.requiredPanels, viewport: CONFIG.viewport });
}

async function collectNavigationValidation(page) {
  return page.evaluate(() => {
    const panel =
      document.querySelector('[data-panelid="1000"]') ||
      document.querySelector('[data-viz-panel-key="panel-1000"]') ||
      document.querySelector('[data-griditem-key="grid-item-1000"]');
    const nav = panel?.querySelector(".bioetl-nav") || null;
    const title =
      panel?.querySelector("[data-bioetl-panel-title]") ||
      panel?.querySelector(".bioetl-panel-title") ||
      panel?.querySelector('[role="heading"]') ||
      null;
    const links = nav
      ? Array.from(
          nav.querySelectorAll(".bioetl-nav-link, .bioetl-nav-current"),
        )
      : [];
    const panelRect = panel?.getBoundingClientRect() || null;
    const navRect = nav?.getBoundingClientRect() || null;
    const titleRect = title?.getBoundingClientRect() || null;
    const linkRects = links.map((link) => link.getBoundingClientRect());
    const tolerance = 1;
    const rectInside = (inner, outer) =>
      Boolean(
        inner &&
          outer &&
          inner.left >= outer.left - tolerance &&
          inner.right <= outer.right + tolerance &&
          inner.top >= outer.top - tolerance &&
          inner.bottom <= outer.bottom + tolerance,
      );
    const linksInsidePanel = linkRects.every((rect) =>
      rectInside(rect, panelRect),
    );
    const contentInsidePanel =
      rectInside(navRect, panelRect) && rectInside(titleRect, panelRect);
    const focusTarget = nav?.querySelector('a.bioetl-nav-link[href*="/d/"]') || null;
    focusTarget?.focus();
    const focusStyle = focusTarget ? getComputedStyle(focusTarget) : null;
    const focusOutlineWidthPx = Number.parseFloat(
      focusStyle?.outlineWidth || "0",
    );
    const focusBoxShadow = (focusStyle?.boxShadow || "").trim().toLowerCase();
    const focusIndicatorVisible = Boolean(
      focusTarget &&
        document.activeElement === focusTarget &&
        ((focusStyle?.outlineStyle || "").toLowerCase() !== "none" &&
          Number.isFinite(focusOutlineWidthPx) &&
          focusOutlineWidthPx > 0 ||
          focusBoxShadow &&
            focusBoxShadow !== "none" &&
            focusBoxShadow !== "rgba(0, 0, 0, 0) 0px 0px 0px 0px"),
    );
    const evidence = {
      panelFound: Boolean(panel),
      navigationFound: Boolean(nav),
      titleFound: Boolean(title),
      linkCount: links.length,
      contentInsidePanel,
      linksInsidePanel,
      focusTargetFound: Boolean(focusTarget),
      focusInsideNavigation: Boolean(focusTarget?.closest(".bioetl-nav")),
      focusIndicatorVisible,
      focusOutlineStyle: focusStyle?.outlineStyle || null,
      focusOutlineWidthPx: Number.isFinite(focusOutlineWidthPx)
        ? focusOutlineWidthPx
        : null,
      focusBoxShadow: focusStyle?.boxShadow || null,
      panelHeightPx: panelRect?.height ?? null,
      navigationHeightPx: navRect?.height ?? null,
    };
    return {
      status:
        evidence.panelFound &&
        evidence.navigationFound &&
        evidence.titleFound &&
        evidence.linkCount === 7 &&
        evidence.contentInsidePanel &&
        evidence.linksInsidePanel &&
        evidence.focusTargetFound &&
        evidence.focusInsideNavigation &&
        evidence.focusIndicatorVisible
          ? "ok"
          : "error",
      ...evidence,
    };
  });
}

async function collectTypographyValidation(page, dashboard) {
  return page.evaluate(({ requiredPanels, minBodyPx, minTitlePx }) => {
    const round = (value) => Math.round(value * 100) / 100;
    const visible = (element) => {
      if (!(element instanceof Element)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.display !== "none" &&
        style.visibility !== "hidden"
      );
    };
    const panelElement = (panel) =>
      document.querySelector(`[data-panelid="${panel.id}"]`) ||
      document.querySelector(`[data-viz-panel-key="panel-${panel.id}"]`) ||
      document.querySelector(`[data-griditem-key="grid-item-${panel.id}"]`);
    const panelTitleElement = (container) =>
      container.querySelector("[data-bioetl-panel-title]") ||
      container.querySelector(".bioetl-panel-title") ||
      container.querySelector('[role="heading"]') ||
      container.querySelector('[data-testid="title-items-container"]') ||
      container.querySelector('[data-testid^="data-testid Panel header"]') ||
      container.querySelector(".panel-title") ||
      container.querySelector("header");
    const panelBodyRoot = (container) =>
      container.querySelector(".bioetl-nav") ||
      container.querySelector('[data-testid="data-testid panel content"]') ||
      container.querySelector('[data-testid="panel content"]') ||
      container.querySelector('[data-testid$="panel content"]') ||
      container.querySelector(".panel-content") ||
      container;
    const ownText = (element) =>
      Array.from(element.childNodes)
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent?.trim() || "")
        .join(" ")
        .trim();

    const panels = [];
    const violations = [];
    for (const panel of requiredPanels) {
      const container = panelElement(panel);
      if (!container) {
        violations.push({
          id: panel.id,
          title: panel.title,
          kind: "panel_missing",
        });
        continue;
      }

      const titleElement = panelTitleElement(container);
      const titleFontPx = titleElement
        ? Number.parseFloat(getComputedStyle(titleElement).fontSize)
        : null;
      if (!Number.isFinite(titleFontPx) || titleFontPx + 0.01 < minTitlePx) {
        violations.push({
          id: panel.id,
          title: panel.title,
          kind: "panel_title_font",
          observedPx: Number.isFinite(titleFontPx) ? round(titleFontPx) : null,
          minimumPx: round(minTitlePx),
        });
      }

      const bodyRoot = panelBodyRoot(container);
      const navigationRoot = container.querySelector(".bioetl-nav");
      const bodyFonts = [bodyRoot, ...Array.from(bodyRoot.querySelectorAll("*"))]
        .filter((element) => {
          if (!visible(element) || !ownText(element)) return false;
          if (
            titleElement &&
            (element === titleElement || titleElement.contains(element))
          ) {
            return false;
          }
          return !element.closest("script, style, noscript");
        })
        .map((element) => Number.parseFloat(getComputedStyle(element).fontSize))
        .filter(Number.isFinite);
      const minimumBodyFontPx =
        bodyFonts.length > 0 ? Math.min(...bodyFonts) : null;
      const populatedNavigation = Boolean(
        container.querySelector('.bioetl-nav a[href*="/d/"]'),
      );
      if (populatedNavigation && bodyFonts.length === 0) {
        violations.push({
          id: panel.id,
          title: panel.title,
          kind: "panel_body_font_missing",
          minimumPx: round(minBodyPx),
        });
      }
      if (
        Number.isFinite(minimumBodyFontPx) &&
        minimumBodyFontPx + 0.01 < minBodyPx
      ) {
        violations.push({
          id: panel.id,
          title: panel.title,
          kind: "panel_body_font",
          observedPx: round(minimumBodyFontPx),
          minimumPx: round(minBodyPx),
        });
      }
      panels.push({
        id: panel.id,
        title: panel.title,
        measuredTitleText: titleElement?.textContent?.trim().slice(0, 80) || "",
        measuredTitleTag: titleElement?.tagName || null,
        measuredTitleClass: titleElement?.className || null,
        navigationClassFound: Boolean(navigationRoot),
        navigationFirstChildTag: navigationRoot?.firstElementChild?.tagName || null,
        navigationFirstChildFontPx: navigationRoot?.firstElementChild
          ? round(
              Number.parseFloat(
                getComputedStyle(navigationRoot.firstElementChild).fontSize,
              ),
            )
          : null,
        titleFontPx: Number.isFinite(titleFontPx) ? round(titleFontPx) : null,
        minimumBodyFontPx: Number.isFinite(minimumBodyFontPx)
          ? round(minimumBodyFontPx)
          : null,
        bodyTextSampleCount: bodyFonts.length,
      });
    }
    return {
      status: violations.length === 0 ? "ok" : "error",
      bodyMinimumPx: minBodyPx,
      panelTitleMinimumPx: minTitlePx,
      checkedPanelCount: panels.length,
      panels,
      violations,
    };
  }, {
    requiredPanels: dashboard.requiredPanels,
    minBodyPx: MIN_PANEL_BODY_FONT_PX,
    minTitlePx: MIN_PANEL_TITLE_FONT_PX,
  });
}

async function renderDashboard(page, dashboard, index, total) {
  const target = dashboardRenderUrl(dashboard);
  console.log(`[${index}/${total}] loading ${dashboard.uid} ...`);
  // Start full-surface audits with enough vertical space for expanded rows.
  // Shrinking/resizing only after queries settle makes Grafana re-run every
  // panel and can strand Infinity/HTTP panels in a loading state.
  const auditViewport =
    CONFIG.captureSurface === "full" && CONFIG.expandCollapsedRows
    ? { width: CONFIG.viewport.width, height: MAX_CAPTURE_VIEWPORT_HEIGHT }
    : CONFIG.viewport;
  await page.setViewportSize(auditViewport);
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
  await applyBrowserZoom(page);
  await expandCollapsedRows(page, dashboard, index, total);
  await waitForDashboardContent(page, dashboard, index, total);
  await materializeLazyPanels(page, dashboard, index, total);

  const renderedPanelEvidence = await countRenderedPanels(page);
  dashboard.renderedPanelCount = renderedPanelEvidence.count;
  dashboard.renderedPanelSelector = renderedPanelEvidence.selector;
  if (renderedPanelEvidence.count === 0) {
    throw new Error(
      `Render gate failed for ${dashboard.uid}: renderedPanelCount=0 (blank/zero panels are fail-closed)`,
    );
  }
  console.log(
    `[${index}/${total}] detected ${renderedPanelEvidence.count} rendered panel marker(s) for ${dashboard.uid} using ${renderedPanelEvidence.selector}`,
  );
  const viewportChanged = await prepareDashboardForCapture(
    page,
    dashboard,
    index,
    total,
  );
  if (viewportChanged) {
    await settleDashboardAfterViewportChange(page, dashboard, index, total);
  }
  dashboard.requestedViewport = { ...CONFIG.viewport };
  dashboard.actualViewport = page.viewportSize() || { ...CONFIG.viewport };
  dashboard.requestedTheme = CONFIG.theme;
  dashboard.actualTheme = await detectActualTheme(page);
  if (dashboard.actualTheme !== CONFIG.theme) {
    throw new Error(
      `Theme verification failed for ${dashboard.uid}: requested=${CONFIG.theme} actual=${dashboard.actualTheme}`,
    );
  }
  dashboard.browserState = await detectBrowserAndKioskState(page);
  if (dashboard.browserState.actualKiosk !== CONFIG.kioskMode) {
    throw new Error(
      `Kiosk verification failed for ${dashboard.uid}: requested=${CONFIG.kioskMode} actual=${dashboard.browserState.actualKiosk}`,
    );
  }
  dashboard.layoutGeometry = await collectLayoutGeometry(page, dashboard);
  dashboard.typographyValidation = await collectTypographyValidation(page, dashboard);
  if (dashboard.typographyValidation.status !== "ok") {
    throw new Error(
      `Typography validation failed for ${dashboard.uid}: ${dashboard.typographyValidation.violations.length} violation(s)`,
    );
  }
  dashboard.navigationValidation = await collectNavigationValidation(page);
  if (CONFIG.navigationOnly && dashboard.navigationValidation.status !== "ok") {
    throw new Error(
      `Navigation validation failed for ${dashboard.uid}: ${JSON.stringify(dashboard.navigationValidation)}`,
    );
  }
  if (CONFIG.navigationOnly) {
    dashboard.terminalStateValidation = {
      status: "ok",
      mode: "navigation-only",
      checkedPanelCount: 0,
      panels: [],
    };
  } else {
    dashboard.terminalStateValidation = await validateDashboardTerminalStates(
      page,
      dashboard,
      index,
      total,
    );
  }
  if (dashboard.terminalStateValidation.status !== "ok") {
    throw new Error(
      `Terminal-state validation failed for ${dashboard.uid}: ${describeTerminalStateFailure(dashboard)}`,
    );
  }

  const filePath = path.join(CONFIG.outputDir, dashboard.file);
  console.log(
    `[${index}/${total}] capturing screenshot ${dashboard.uid} with timeout ${CONFIG.captureTimeoutMs}ms ...`,
  );
  const screenshotOptions = {
    path: filePath,
    timeout: CONFIG.captureTimeoutMs,
    animations: "disabled",
    caret: "hide",
  };
  if (CONFIG.captureSurface === "viewport") {
    screenshotOptions.clip = {
      x: 0,
      y: 0,
      width: CONFIG.viewport.width,
      height: CONFIG.viewport.height,
    };
  } else if (CONFIG.expandCollapsedRows && Number.isFinite(dashboard.captureHeight)) {
    screenshotOptions.clip = {
      x: 0,
      y: 0,
      width: CONFIG.viewport.width,
      height: dashboard.captureHeight,
    };
  } else {
    screenshotOptions.fullPage = true;
  }
  await page.screenshot(screenshotOptions);
  const screenshotBuffer = await fs.promises.readFile(filePath);
  dashboard.screenshotEvidence = {
    file: dashboard.file,
    ...pngEvidence(screenshotBuffer),
    capturedAt: new Date().toISOString(),
  };
  if (isMateriallyBlankPng(screenshotBuffer)) {
    throw new Error(
      `Render gate failed for ${dashboard.uid}: screenshot is materially blank (near-uniform pixels)`,
    );
  }
  if (dashboard.screenshotEvidence.width !== CONFIG.viewport.width) {
    throw new Error(
      `Screenshot width verification failed for ${dashboard.uid}: requested=${CONFIG.viewport.width} actual=${dashboard.screenshotEvidence.width}`,
    );
  }
  dashboard.renderStatus = "rendered";
  console.log(`rendered ${dashboard.uid} -> ${dashboard.file}`);
}

async function writeManifest(dashboards) {
  const terminalStatuses = dashboards.map(
    (dashboard) => dashboard.terminalStateValidation?.status || "missing",
  );
  const payload = {
    generated_at: new Date().toISOString(),
    engine: "playwright",
    base_url: CONFIG.baseUrl,
    scope_query: CONFIG.scopeQuery,
    timeout_ms: CONFIG.timeoutMs,
    capture_timeout_ms: CONFIG.captureTimeoutMs,
    expand_collapsed_rows: CONFIG.expandCollapsedRows,
    navigation_only: CONFIG.navigationOnly,
    requested: {
      viewport: CONFIG.viewport,
      theme: CONFIG.theme,
      capture_surface: CONFIG.captureSurface,
      kiosk_mode: CONFIG.kioskMode,
      browser_zoom: CONFIG.browserZoom,
    },
    actual: {
      viewports: Object.fromEntries(
        dashboards.map((dashboard) => [dashboard.uid, dashboard.actualViewport || null]),
      ),
      themes: Object.fromEntries(
        dashboards.map((dashboard) => [dashboard.uid, dashboard.actualTheme || "unknown"]),
      ),
    },
    terminal_state_validation: {
      status:
        terminalStatuses.length > 0 && terminalStatuses.every((status) => status === "ok")
          ? "ok"
          : "error",
      dashboards: Object.fromEntries(
        dashboards.map((dashboard) => [
          dashboard.uid,
          dashboard.terminalStateValidation?.status || "missing",
        ]),
      ),
    },
    backend_applicability: {
      quarantine_explorer: {
        state: "NOT_APPLICABLE",
        reason: "Quarantine Explorer HTTP/UI surface is retired from shipping.",
      },
    },
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
  let renderFailure = null;
  for (const [index, dashboard] of dashboards.entries()) {
    const launchOptions = {
      headless: true,
      args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    };
    const executablePath =
      process.env.PLAYWRIGHT_EXECUTABLE_PATH ||
      process.env.CHROME_EXE ||
      process.env.CHROMIUM_PATH ||
      "";
    if (executablePath) {
      launchOptions.executablePath = executablePath;
    }
    const browser = await playwright().chromium.launch(launchOptions);
    let contextBundle = null;
    let context = null;
    try {
      contextBundle = await createBrowserContext(browser);
      context = contextBundle.context || contextBundle;
      const page = await context.newPage();
      try {
        await renderDashboard(page, dashboard, index + 1, dashboards.length);
      } catch (error) {
        dashboard.renderStatus = "error";
        dashboard.error = String(error?.message ?? error);
        renderFailure = error;
      } finally {
        await page.close();
      }
    } finally {
      if (contextBundle?.api) {
        await contextBundle.api.dispose();
      }
      if (context) {
        await context.close();
      }
      await browser.close();
    }
    if (renderFailure) {
      break;
    }
  }
  await writeManifest(dashboards);
  if (renderFailure) {
    throw renderFailure;
  }
}

if (require.main === module) {
  main().catch((error) => {
    const message = String(error?.message ?? error);
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
}

module.exports = {
  classifyPanelTerminalEvidence,
  pngEvidence,
};
