/**
 * Capture Trust validation panel close-ups via Grafana viewPanel.
 * Uses project-local Playwright under %LOCALAPPDATA%/bioetl-playwright.
 */
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { pathToFileURL } = require("node:url");

const UID = "bioetl-control-plane-v1";
const SLUG = "0-trust";
const PANEL_IDS = [9413, 9414, 9415, 9416, 9417];
const TITLES = {
  9413: "Review Checkpoint Validation",
  9414: "Review Manifest Validation",
  9415: "Review Lineage Validation",
  9416: "Review Retention Compliance",
  9417: "Review Bounded Failure Reasons",
};

function arg(name, fallback = "") {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

async function main() {
  const baseUrl = arg("--base-url", process.env.GRAFANA_BASE_URL || "http://localhost:3000");
  const outputDir = path.resolve(
    arg("--output-dir", "reports/observability/grafana/visual-baseline-20260811/trust-validation-closeups"),
  );
  const width = Number.parseInt(arg("--width", "1920"), 10);
  const height = Number.parseInt(arg("--height", "900"), 10);
  const theme = arg("--theme", "dark");
  const state = arg("--state", process.env.BIOETL_TRUST_FIXTURE_STATE || "default");
  const pipeline = arg("--pipeline", "chembl_activity");
  const runType = arg("--run-type", "incremental");
  const runId = arg("--run-id", "00000000-0000-0000-0000-000000008576");
  const username = process.env.GRAFANA_USERNAME || "admin";
  const password =
    process.env.GF_SECURITY_ADMIN_PASSWORD ||
    process.env.GRAFANA_PASSWORD ||
    process.env.GRAFANA_ADMIN_PASSWORD ||
    "";
  const token = process.env.GRAFANA_SERVICE_ACCOUNT_TOKEN || "";

  const localNm = path.join(process.env.LOCALAPPDATA || "", "bioetl-playwright", "node_modules");
  if (fs.existsSync(path.join(localNm, "playwright", "package.json"))) {
    module.paths.unshift(localNm);
  }
  const { chromium } = require("playwright");

  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });
  if (token) {
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${token}` });
  }
  const page = await context.newPage();
  page.setDefaultTimeout(120000);

  await page.goto(`${baseUrl.replace(/\/$/, "")}/login`, { waitUntil: "domcontentloaded" });
  if (page.url().toLowerCase().includes("login") && password) {
    await page.fill('input[name="user"]', username);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForLoadState("networkidle").catch(() => {});
  }

  const shots = [];
  for (const panelId of PANEL_IDS) {
    const url =
      `${baseUrl.replace(/\/$/, "")}/d/${UID}/${SLUG}` +
      `?orgId=1&theme=${theme}&kiosk=1&from=now-12h&to=now&timezone=UTC&refresh=off&viewPanel=${panelId}`;
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(8000);
    await page
      .waitForSelector(
        '[data-testid^="data-testid Panel header"], .panel-content, canvas, table',
        { timeout: 30000 },
      )
      .catch(() => {});
    await page.waitForTimeout(4000);
    const file = `trust-panel-${panelId}-closeup.png`;
    const filePath = path.join(outputDir, file);
    await page.screenshot({ path: filePath, fullPage: false });
    const buf = fs.readFileSync(filePath);
    const sha = crypto.createHash("sha256").update(buf).digest("hex");
    shots.push({
      panel_id: panelId,
      title: TITLES[panelId],
      file,
      bytes: buf.length,
      sha256: sha,
      state,
      pipeline,
      run_type: runType,
      run_id: runId,
    });
    console.log(`captured ${file} (${buf.length} bytes)`);
  }

  await browser.close();
  const manifest = {
    schema_version: 1,
    issue: "#8576",
    related_issue: "#8578",
    uid: UID,
    capture_state: 	rust-validation-panel-closeups:,
    generated_at: new Date().toISOString(),
    viewport: { width, height, theme, kiosk: "full", viewPanel: true },
    screenshots: shots,
    notes: [
      "Close-ups via Grafana viewPanel solo mode.",
      "Default range selector; populated/empty/QUERY_ERROR variants need controlled data fixtures.",
    ],
  };
  fs.writeFileSync(
    path.join(outputDir, "closeups-manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
    "utf8",
  );
  console.log(`wrote closeups-manifest.json count=${shots.length}`);
  if (shots.length !== PANEL_IDS.length) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
