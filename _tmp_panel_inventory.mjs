const fs = require('fs');
const path = require('path');

const ROOT = 'E:/g-drive/05_AI/github/BioactivityDataAcquisition2';
const DASH = path.join(ROOT, 'grafana/dashboards');
const OUT = path.join(ROOT, 'docs/03-guides/dashboards/panel-title-inventory.md');

const HEADER = `# Panel Title Inventory

Generated from \`grafana/dashboards/*.json\`.

## KPI ownership contract anchors

Machine-readable SSOT: \`docs/03-guides/dashboards/contracts/navigation-links.yaml\` (\`kpi_ownership\`).

| KPI key | Canonical UID | Mirror panel(s) |
|---|---|---|
| \`failed_runs_in_range\` | \`bioetl-overview-v2\` | \`bioetl-runtime#205\` |
| \`worst_lag_stage\` | \`bioetl-overview-v2\` | \`bioetl-runtime#237\` |
| \`worst_backlog_stage\` | \`bioetl-overview-v2\` | \`bioetl-runtime#238\` |

| Dashboard | Panel ID | Title |
| --- | ---: | --- |
`;

function iterPanels(panels) {
  const discovered = [];
  const stack = [...(panels || [])];
  while (stack.length) {
    const panel = stack.shift();
    if (!panel || typeof panel !== 'object') continue;
    discovered.push(panel);
    const nested = panel.panels;
    if (Array.isArray(nested)) {
      stack.unshift(...nested.filter((item) => item && typeof item === 'object'));
    }
  }
  return discovered;
}

const rows = [];
const counts = {};
for (const name of fs.readdirSync(DASH).filter((f) => f.endsWith('.json')).sort()) {
  const payload = JSON.parse(fs.readFileSync(path.join(DASH, name), 'utf8'));
  let c = 0;
  for (const panel of iterPanels(payload.panels || [])) {
    const id = panel.id;
    const title = panel.title;
    if (id == null || !title) continue;
    rows.push(`| ${name} | ${id} | ${title} |`);
    c++;
  }
  counts[name] = c;
}

const content = HEADER + rows.join('\n') + '\n';
fs.writeFileSync(OUT, content, 'utf8');
console.log(`wrote ${rows.length} panel rows -> ${OUT}`);
for (const [k, v] of Object.entries(counts).sort()) console.log(`${k}: ${v}`);
console.log(`TOTAL: ${Object.values(counts).reduce((a, b) => a + b, 0)}`);
