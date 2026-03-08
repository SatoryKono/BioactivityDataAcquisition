#!/usr/bin/env node
/**
 * Batch SVG → PNG converter using Puppeteer (Chrome headless).
 *
 * Converts post-processed SVG files (with <text> fallback, no foreignObject)
 * into high-quality PNG images. Designed as fallback for systems without
 * rsvg-convert or inkscape.
 *
 * Usage:
 *   node scripts/diagrams/svg2png.mjs [--scale N] [--jobs N] <svg-dir|svg-file> ...
 *   node scripts/diagrams/svg2png.mjs docs/02-architecture/mmd-diagrams
 *   node scripts/diagrams/svg2png.mjs --scale 3 docs/02-architecture/mmd-diagrams/architecture/svg/01-high-level-hexagonal.svg
 */

import { createRequire } from "module";
import { promises as fs } from "fs";
import path from "path";

// Resolve puppeteer from mmdc's node_modules
const require = createRequire(import.meta.url);
let puppeteer;
const mmdc_puppeteer =
  "C:/Users/Fedor/AppData/Roaming/npm/node_modules/@mermaid-js/mermaid-cli/node_modules/puppeteer";
try {
  puppeteer = require("puppeteer");
} catch {
  try {
    puppeteer = require(mmdc_puppeteer);
  } catch {
    console.error(
      "ERROR: puppeteer not found. Install via: npm install -g puppeteer"
    );
    process.exit(2);
  }
}

// ── CLI args ─────────────────────────────────────────────────
let scale = 3;
let jobs = 4;
const targets = [];

const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--scale" && i + 1 < args.length) {
    scale = parseInt(args[++i], 10);
  } else if (args[i] === "--jobs" && i + 1 < args.length) {
    jobs = parseInt(args[++i], 10);
  } else if (args[i] === "--help" || args[i] === "-h") {
    console.log(
      "Usage: node svg2png.mjs [--scale N] [--jobs N] <svg-dir|svg-file> ..."
    );
    process.exit(0);
  } else {
    targets.push(args[i]);
  }
}

if (targets.length === 0) {
  console.error("ERROR: no SVG files or directories specified");
  process.exit(1);
}

// ── Collect SVG files ────────────────────────────────────────
async function collectSvgFiles(target) {
  const stat = await fs.stat(target);
  if (stat.isFile() && target.endsWith(".svg")) {
    return [target];
  }
  if (stat.isDirectory()) {
    const files = [];
    // Recursively find **/svg/*.svg
    async function walk(dir) {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      for (const e of entries) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) {
          await walk(full);
        } else if (e.isFile() && e.name.endsWith(".svg") && path.basename(dir) === "svg") {
          files.push(full);
        }
      }
    }
    await walk(target);
    return files;
  }
  return [];
}

let svgFiles = [];
for (const t of targets) {
  svgFiles.push(...(await collectSvgFiles(t)));
}
svgFiles.sort();

if (svgFiles.length === 0) {
  console.error("No SVG files found in specified targets");
  process.exit(1);
}

console.log(`Found ${svgFiles.length} SVG files, scale=${scale}x, jobs=${jobs}`);

// ── Convert ──────────────────────────────────────────────────
async function convertOne(browser, svgPath, idx, total) {
  const svgDir = path.dirname(svgPath);
  const parentDir = path.dirname(svgDir); // go up from /svg/
  const pngDir = path.join(parentDir, "png");
  const baseName = path.basename(svgPath, ".svg");
  const pngPath = path.join(pngDir, `${baseName}.png`);

  await fs.mkdir(pngDir, { recursive: true });

  const svgContent = await fs.readFile(svgPath, "utf-8");

  // Extract SVG dimensions
  const widthMatch = svgContent.match(/width="([\d.]+)/);
  const heightMatch = svgContent.match(/height="([\d.]+)/);
  // Also try viewBox
  const viewBoxMatch = svgContent.match(
    /viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)/
  );

  let svgWidth = widthMatch ? parseFloat(widthMatch[1]) : 800;
  let svgHeight = heightMatch ? parseFloat(heightMatch[1]) : 600;
  if (
    (!widthMatch || !heightMatch) &&
    viewBoxMatch
  ) {
    svgWidth = parseFloat(viewBoxMatch[1]);
    svgHeight = parseFloat(viewBoxMatch[2]);
  }

  const page = await browser.newPage();
  await page.setViewport({
    width: Math.ceil(svgWidth * scale),
    height: Math.ceil(svgHeight * scale),
    deviceScaleFactor: scale,
  });

  // Load SVG as data URI in a simple HTML page
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * { margin: 0; padding: 0; }
  body { background: white; display: flex; align-items: flex-start; justify-content: flex-start; }
  img { width: ${svgWidth}px; height: ${svgHeight}px; }
</style></head><body>
  <img src="data:image/svg+xml;base64,${Buffer.from(svgContent).toString("base64")}" />
</body></html>`;

  await page.setContent(html, { waitUntil: "networkidle0" });

  // Wait a bit for fonts to load
  await page.evaluate(
    () => new Promise((resolve) => setTimeout(resolve, 200))
  );

  await page.screenshot({
    path: pngPath,
    clip: { x: 0, y: 0, width: svgWidth, height: svgHeight },
    omitBackground: false,
  });

  await page.close();

  const stat = await fs.stat(pngPath);
  const sizeKB = Math.round(stat.size / 1024);
  console.log(`  ✓ PNG  [${idx}/${total}]  ${baseName}  (${sizeKB}K)`);
}

// ── Parallel execution ───────────────────────────────────────
async function main() {
  const browser = await puppeteer.launch({
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--font-render-hinting=none",
    ],
  });

  const total = svgFiles.length;
  let idx = 0;
  const errors = [];

  // Process in batches of `jobs`
  for (let i = 0; i < svgFiles.length; i += jobs) {
    const batch = svgFiles.slice(i, i + jobs);
    const promises = batch.map((svgPath) => {
      idx++;
      const currentIdx = idx;
      return convertOne(browser, svgPath, currentIdx, total).catch((err) => {
        console.error(`  ✗ PNG  [${currentIdx}/${total}]  ${path.basename(svgPath, ".svg")}: ${err.message}`);
        errors.push(svgPath);
      });
    });
    await Promise.all(promises);
  }

  await browser.close();

  console.log(`\nDone: ${total - errors.length}/${total} converted`);
  if (errors.length > 0) {
    console.log(`Errors: ${errors.length}`);
    errors.forEach((e) => console.log(`  - ${e}`));
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(2);
});
