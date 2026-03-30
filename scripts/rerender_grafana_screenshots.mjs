import fs from "node:fs";
import path from "node:path";

import { chromium } from "playwright";

const baseUrl = "http://localhost:3000";
const outputDir = path.resolve("output", "playwright");

const dashboards = [
  { uid: "bioetl-overview-v2", file: "bioetl-overview-v2.png" },
  { uid: "bioetl-dq-v2", file: "bioetl-dq-v2.png" },
  { uid: "bioetl-provider-health-v2", file: "bioetl-provider-health-v2.png" },
  { uid: "bioetl-runtime", file: "bioetl-runtime.png" },
];

async function ensureOutputDir() {
  await fs.promises.mkdir(outputDir, { recursive: true });
}

async function login(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.getByLabel(/email or username/i).fill("admin");
  await page.getByLabel(/^password$/i).fill("admin");
  await page.getByRole("button", { name: /log in/i }).click();
  await page.waitForLoadState("networkidle");
}

async function renderDashboard(page, uid, file) {
  const target = `${baseUrl}/d/${uid}`;
  await page.goto(target, { waitUntil: "networkidle", timeout: 60_000 });
  await page.waitForTimeout(8_000);
  await page.screenshot({
    path: path.join(outputDir, file),
    fullPage: true,
  });
  console.log(`rendered ${uid} -> ${file}`);
}

(async () => {
  await ensureOutputDir();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 2200 } });
  try {
    await login(page);
    for (const dashboard of dashboards) {
      await renderDashboard(page, dashboard.uid, dashboard.file);
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
