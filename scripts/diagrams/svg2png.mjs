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
 *   node scripts/diagrams/svg2png.mjs docs/02-architecture/diagrams
 *   node scripts/diagrams/svg2png.mjs --scale 3 docs/02-architecture/diagrams/architecture/svg/01-high-level-hexagonal.svg
 */

import {createRequire} from "node:module";
import {promises as fs} from "node:fs";
import path from "node:path";

// Resolve puppeteer from PUPPETEER_MODULE_PATH or a local/node_modules install.
const require = createRequire(import.meta.url);
let puppeteer;
const moduleCandidates = [
  process.env.PUPPETEER_MODULE_PATH,
  "puppeteer",
].filter(Boolean);

for (const candidate of moduleCandidates) {
  try {
    puppeteer = require(candidate);
    break;
  } catch {
    // Try the next resolution candidate.
  }
}

if (!puppeteer) {
  console.error(
    "ERROR: puppeteer not found. Set PUPPETEER_MODULE_PATH or install puppeteer."
  );
  process.exit(2);
}

// ── CLI args ─────────────────────────────────────────────────
let scale = 3;
let jobs = 4;
const targets = [];

const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--scale" && i + 1 < args.length) {
    scale = Number.parseInt(args[++i], 10);
  } else if (args[i] === "--jobs" && i + 1 < args.length) {
    jobs = Number.parseInt(args[++i], 10);
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
svgFiles.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

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

  // Extract SVG dimensions — prefer viewBox (always numeric),
  // width/height may be "100%" which is not useful.
  const viewBoxMatch = svgContent.match(
    /viewBox="(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)/
  );
  const widthMatch = svgContent.match(/\bwidth="([\d.]+)(?:px)?"/);
  const heightMatch = svgContent.match(/\bheight="([\d.]+)(?:px)?"/);

  let svgWidth, svgHeight;
  if (viewBoxMatch) {
    svgWidth = Number.parseFloat(viewBoxMatch[3]);
    svgHeight = Number.parseFloat(viewBoxMatch[4]);
  } else if (widthMatch && heightMatch) {
    svgWidth = Number.parseFloat(widthMatch[1]);
    svgHeight = Number.parseFloat(heightMatch[1]);
  } else {
    svgWidth = 800;
    svgHeight = 600;
  }

  // Auto-reduce scale for very large diagrams to avoid Chrome OOM/timeout
  let effectiveScale = scale;
  if (svgWidth * svgHeight > 4_000_000) {
    effectiveScale = Math.min(scale, 2);
  }

  // Use ceil to avoid fractional pixels
  const vpWidth = Math.ceil(svgWidth);
  const vpHeight = Math.ceil(svgHeight);

  const page = await browser.newPage();
  await page.setViewport({
    width: vpWidth,
    height: vpHeight,
    deviceScaleFactor: effectiveScale,
  });

  // Load SVG inline (not as img src) so <text> elements render with full font support
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: ${vpWidth}px; height: ${vpHeight}px; overflow: hidden; background: white; }
  svg { width: ${vpWidth}px; height: ${vpHeight}px; display: block; }
</style></head><body>
${svgContent}
</body></html>`;

  await page.setContent(html, { waitUntil: "networkidle0" });

  // Wait for fonts to load
  await page.evaluate(() =>
    document.fonts ? document.fonts.ready : new Promise((r) => setTimeout(r, 300))
  );

  await page.screenshot({
    path: pngPath,
    clip: { x: 0, y: 0, width: vpWidth, height: vpHeight },
    omitBackground: false,
  });

  await page.close();

  const stat = await fs.stat(pngPath);
  const sizeKB = Math.round(stat.size / 1024);
  console.log(`  ✓ PNG  [${idx}/${total}]  ${baseName}  (${sizeKB}K)`);
}

// ── Parallel execution ───────────────────────────────────────
async function main() {
  const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || undefined;
  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    protocolTimeout: 120_000,
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

try {
  await main();
} catch (err) {
  console.error("Fatal error:", err);
  process.exit(2);
}
