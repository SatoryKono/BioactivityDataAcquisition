/**
 * RF-002 / #8576: capture default-row first fold at 1920×1080 for seven UIDs.
 * Requires GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN.
 */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { execFileSync } = require("node:child_process");

const UIDS = (
  process.env.GRAFANA_SCREENSHOT_UIDS ||
  [
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
  ].join(",")
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const base = (process.env.GRAFANA_BASE_URL || "http://127.0.0.1:3000").replace(
  /\/$/,
  "",
);
const user = process.env.GRAFANA_USERNAME || "admin";
const pass = process.env.GRAFANA_PASSWORD || "";
const token = process.env.GRAFANA_SERVICE_ACCOUNT_TOKEN || "";
const theme = (process.env.GRAFANA_SCREENSHOT_THEME || "dark").toLowerCase();
const outDir =
  process.env.OUT_DIR ||
  path.join(
    "reports",
    "observability",
    "grafana",
    "visual-baseline-20260811",
    "default-row-first-fold-1920x1080-rf002",
  );
const settleMs = Number(process.env.SETTLE_MS || 8000);
const navTimeout = Number(process.env.NAV_TIMEOUT_MS || 180000);

function gitSha() {
  try {
    return execFileSync("/usr/bin/git", ["rev-parse", "HEAD"], {
      encoding: "utf8",
    }).trim();
  } catch {
    return "";
  }
}

async function main() {
  if (!pass && !token) {
    console.error("Set GRAFANA_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN");
    process.exit(9);
  }
  fs.mkdirSync(outDir, { recursive: true });
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
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
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
      page
        .waitForNavigation({ waitUntil: "networkidle", timeout: navTimeout })
        .catch(() => null),
      page.click('button[type="submit"]'),
    ]);
  }

  const results = [];
  let renderErrors = 0;
  for (const uid of UIDS) {
    const file = `${uid}-dark-first-fold-1920x1080.png`;
    const outPath = path.join(outDir, file);
    process.stdout.write(`capturing ${uid} -> ${outPath}\n`);
    try {
      await page.goto(
        `${base}/d/${uid}?orgId=1&from=now-12h&to=now&theme=${theme}&kiosk`,
        { waitUntil: "networkidle", timeout: navTimeout },
      );
      await page.waitForTimeout(settleMs);
      // Fail closed on Grafana render/error banners when visible.
      const errText = await page
        .locator("text=RENDER_ERROR")
        .count()
        .catch(() => 0);
      if (errText > 0) {
        renderErrors += 1;
        process.stdout.write(`WARN RENDER_ERROR visible on ${uid}\n`);
      }
      await page.screenshot({ path: outPath, fullPage: false });
      const buf = fs.readFileSync(outPath);
      const sha = crypto.createHash("sha256").update(buf).digest("hex");
      results.push({
        uid,
        file,
        bytes: buf.length,
        sha256: sha,
        viewport: { width: 1920, height: 1080 },
        fullPage: false,
        theme,
        kiosk: true,
        row_state: "default",
        terminal_state: errText > 0 ? "RENDER_ERROR" : "ok",
      });
      process.stdout.write(`wrote ${file} sha=${sha}\n`);
    } catch (err) {
      renderErrors += 1;
      results.push({
        uid,
        file,
        error: String(err && err.message ? err.message : err),
        terminal_state: "CAPTURE_ERROR",
      });
      process.stdout.write(`ERROR ${uid}: ${err}\n`);
    }
  }
  await browser.close();
  const manifest = {
    schema_version: 1,
    issue: "#8576",
    related_issues: ["#8578", "#8579", "#8593", "#8598"],
    kind: "default-row-first-fold-1920x1080",
    generated_at: new Date().toISOString(),
    git_sha: gitSha(),
    base_url: base,
    theme,
    viewport: { width: 1920, height: 1080 },
    render_error_count: renderErrors,
    screenshots: results,
  };
  fs.writeFileSync(
    path.join(outDir, "render-manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
  );
  console.log(
    JSON.stringify(
      { count: results.length, render_error_count: renderErrors, outDir },
      null,
      2,
    ),
  );
  process.exit(renderErrors === 0 && results.length === UIDS.length ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
