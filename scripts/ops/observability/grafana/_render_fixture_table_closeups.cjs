/**
 * Render Trust validation fixture JSON as dark Grafana-like tables and screenshot.
 * Used when Ops HTTP datasource is provisioned read-only and cannot be repointed.
 */
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const PANEL_MAP = {
  9413: "checkpoint-validation",
  9414: "manifest-validation",
  9415: "lineage-validation",
  9416: "retention-compliance",
  9417: "failure-reasons",
};
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

function statusColor(status) {
  switch (String(status || "").toUpperCase()) {
    case "OK":
      return "#73BF69";
    case "WARNING":
      return "#FF9830";
    case "ERROR":
      return "#F2495C";
    case "UNKNOWN":
      return "#8E8E8E";
    default:
      return "#CCCCDC";
  }
}

function tableHtml(title, panelId, state, httpStatus, payload) {
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  const keys = rows.length
    ? Object.keys(rows[0])
    : ["check", "status", "reason", "detail"];
  const head = keys.map((k) => `<th>${k}</th>`).join("");
  const body = rows.length
    ? rows
        .map((row) => {
          const tds = keys
            .map((k) => {
              const v = row[k];
              const text = v === null || v === undefined ? "null" : String(v);
              const color =
                k === "status" ? statusColor(text) : "#CCCCDC";
              return `<td style="color:${color}">${escapeHtml(text)}</td>`;
            })
            .join("");
          return `<tr>${tds}</tr>`;
        })
        .join("")
    : `<tr><td colspan="${keys.length}" style="color:#8E8E8E;font-style:italic">No rows (Infinity noValue path)</td></tr>`;

  return `<!doctype html>
<html><head><meta charset="utf-8"/>
<style>
  body { margin:0; background:#111217; color:#CCCCDC; font:13px/1.4 Inter,Segoe UI,sans-serif; }
  .panel { margin:16px; border:1px solid #2c3235; border-radius:3px; background:#181b1f; }
  .header { padding:10px 12px; border-bottom:1px solid #2c3235; display:flex; justify-content:space-between; gap:12px; }
  .title { font-weight:600; font-size:14px; color:#d8d9da; }
  .meta { color:#8e8e8e; font-size:12px; }
  .badge { padding:2px 8px; border-radius:3px; font-weight:600; font-size:12px; }
  table { width:100%; border-collapse:collapse; }
  th { text-align:left; padding:8px 10px; color:#8e8e8e; border-bottom:1px solid #2c3235; font-weight:600; }
  td { padding:8px 10px; border-bottom:1px solid #22252b; vertical-align:top; }
  .foot { padding:8px 12px; color:#6e6e6e; font-size:11px; }
</style></head>
<body>
  <div class="panel">
    <div class="header">
      <div>
        <div class="title">${escapeHtml(title)} <span class="meta">#${panelId}</span></div>
        <div class="meta">fixture_state=${escapeHtml(state)} · endpoint=${escapeHtml(payload.endpoint || "")} · http=${httpStatus}</div>
      </div>
      <div class="badge" style="background:${statusColor(payload.status)}22;color:${statusColor(payload.status)};border:1px solid ${statusColor(payload.status)}">
        ${escapeHtml(String(payload.status || "UNKNOWN"))}
      </div>
    </div>
    <table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    <div class="foot">Contract fixture close-up for #8576/#8578 · not a live Grafana render · selector chembl_activity / incremental / 00000000-0000-0000-0000-000000008576</div>
  </div>
</body></html>`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function main() {
  const fixtureRoot = path.resolve(
    arg("--fixture-root", "tests/fixtures/grafana/control_plane_validation"),
  );
  const outputDir = path.resolve(
    arg(
      "--output-dir",
      "reports/observability/grafana/visual-baseline-20260811/trust-closeups-by-state",
    ),
  );
  const states = arg(
    "--states",
    "populated,valid_empty_or_unknown,backend_error,service_unavailable,empty_rows",
  )
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const localNm = path.join(
    process.env.LOCALAPPDATA || "",
    "bioetl-playwright",
    "node_modules",
  );
  if (fs.existsSync(path.join(localNm, "playwright", "package.json"))) {
    module.paths.unshift(localNm);
  }
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1920, height: 900 },
    deviceScaleFactor: 1,
  });

  const all = [];
  for (const state of states) {
    const stateDir = path.join(outputDir, state);
    fs.mkdirSync(stateDir, { recursive: true });
    const shots = [];
    for (const [panelId, endpoint] of Object.entries(PANEL_MAP)) {
      const fixturePath = path.join(fixtureRoot, endpoint, `${state}.json`);
      if (!fs.existsSync(fixturePath)) {
        console.error(`missing fixture ${fixturePath}`);
        continue;
      }
      const payload = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
      const httpStatus =
        state === "service_unavailable" || payload.http_status === 503 ? 503 : 200;
      const html = tableHtml(
        TITLES[panelId],
        Number(panelId),
        state,
        httpStatus,
        payload,
      );
      const htmlPath = path.join(stateDir, `panel-${panelId}-${state}.html`);
      fs.writeFileSync(htmlPath, html, "utf8");
      await page.goto("file://" + htmlPath.replaceAll("\\", "/"), {
        waitUntil: "domcontentloaded",
      });
      await page.waitForTimeout(300);
      const file = `trust-panel-${panelId}-${state}-closeup.png`;
      const pngPath = path.join(stateDir, file);
      await page.screenshot({ path: pngPath, fullPage: true });
      const buf = fs.readFileSync(pngPath);
      const shot = {
        panel_id: Number(panelId),
        title: TITLES[panelId],
        endpoint,
        state,
        http_status: httpStatus,
        payload_status: payload.status,
        row_count: Array.isArray(payload.rows) ? payload.rows.length : 0,
        file,
        bytes: buf.length,
        sha256: crypto.createHash("sha256").update(buf).digest("hex"),
        fixture: path.relative(process.cwd(), fixturePath).replaceAll("\\", "/"),
      };
      shots.push(shot);
      all.push(shot);
      console.log(`captured ${file} status=${payload.status} rows=${shot.row_count}`);
    }
    fs.writeFileSync(
      path.join(stateDir, "closeups-manifest.json"),
      JSON.stringify(
        {
          schema_version: 1,
          issue: "#8576",
          related_issue: "#8578",
          capture_mode: "fixture-html-table",
          state,
          generated_at: new Date().toISOString(),
          screenshots: shots,
        },
        null,
        2,
      ) + "\n",
      "utf8",
    );
  }

  fs.writeFileSync(
    path.join(outputDir, "MATRIX_SUMMARY.json"),
    JSON.stringify(
      {
        schema_version: 1,
        issue: "#8576",
        related_issue: "#8578",
        capture_mode: "fixture-html-table",
        generated_at: new Date().toISOString(),
        note:
          "Grafana Ops HTTP datasource is provisioned read-only; close-ups render contract fixtures as dark tables matching panel row fields.",
        states,
        screenshot_count: all.length,
        screenshots: all,
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );
  await browser.close();
  console.log(`done total=${all.length} -> ${outputDir}`);
  if (all.length < states.length * Object.keys(PANEL_MAP).length) process.exit(1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
