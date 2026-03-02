# Branch Diff Matrix: Diagram Render Scripts & Settings (2026-03-01)

Baseline: local branch `TMP01-01`.
Compared branches:
- `claude/bioetl-architecture-prompts-v3-lLJJu`
- `claude/audit-fix-diagrams-hZglG`
- `claude/audit-diagram-docs-scripts-fUJUM`
- `claude/improve-diagram-design-K2XMN`

## Matrix (Render/Theme Scope)

| File | claude/bioetl-architecture-prompts-v3-lLJJu | claude/audit-fix-diagrams-hZglG | claude/audit-diagram-docs-scripts-fUJUM | claude/improve-diagram-design-K2XMN |
|---|---|---|---|---|
| `docs/02-architecture/mmd-diagrams/render.sh` | Added skip for diagrams marked `%% @status superseded` (not rendered). | No changes. | No changes. | Added dark mode: `--dark`, `DARK_MODE`, `BG=#0f172a`, dark output dirs `svg-dark/png-dark`, optional dark config/css switch. |
| `docs/02-architecture/mmd-diagrams/theme/mermaid-config.json` | No changes. | No changes. | `flowchart.padding: 24 -> 32`. | `clusterBkg` and `fillType5` palette shift; `nodeSpacing 50 -> 55`, `rankSpacing 45 -> 50`; ELK spacing `40/30/20 -> 45/35/25`. |
| `docs/02-architecture/mmd-diagrams/theme/custom.css` | No changes. | No changes. | Added `.cluster-label` + `.cluster-label .nodeLabel` padding/line-height. | Large visual restyle: stronger stroke/shadow, edge label readability tweaks, hover/contrast/readability rules. |
| `docs/02-architecture/mmd-diagrams/_template.mmd` | No changes. | No changes. | Added generic linkStyle guideline (`stroke:#475569,...`). | Large template/style-guide rewrite (metadata formatting, palette tiers, naming/format rules, spacing guidance). |
| `assets/javascripts/mermaid-loader.js` | No changes. | No changes. | Default Mermaid version `10.4.0 -> 10.6.1`. | No changes. |
| `assets/javascripts/MERMAID_VERSION` | No changes. | No changes. | `10.4.0 -> 10.6.1`. | No changes. |
| `assets/stylesheets/mermaid.css` | No changes. | No changes. | No changes. | Added contrast enhancements for embedded Mermaid (cluster/node shadows, edgeLabel weight, hover feedback). |
| `docs/02-architecture/mmd-diagrams/theme/custom-dark.css` | No changes. | No changes. | No changes. | New file (dark theme CSS profile). |
| `docs/02-architecture/mmd-diagrams/theme/mermaid-config-dark.json` | No changes. | No changes. | No changes. | Not present (render dark-mode code expects it, but branch does not add it). |


## Continuation: Policy/Docs/Scripts Matrix

| File | claude/bioetl-architecture-prompts-v3-lLJJu | claude/audit-fix-diagrams-hZglG | claude/audit-diagram-docs-scripts-fUJUM | claude/improve-diagram-design-K2XMN |
|---|---|---|---|---|
| `docs/02-architecture/decisions/ADR-040-diagram-governance.md` | No changes. | Rewrites D7/D8 thresholds (`<=10`, `11-30`, `>30`), adds sequence-diagram ELK exception note, updates LAYOUT-001/002 conditions. | Minor doc sync: source-line references and linkStyle count wording (`5 -> 6`). | No changes. |
| `docs/02-architecture/06-diagram-policy.md` | No changes. | No changes. | Replaces multiline ELK init example with one-line `%%{init:...}%%`; explicitly states init directive must be one line in `.mmd`. | No changes. |
| `docs/02-architecture/architecture-diagrams.md` | No changes. | No changes. | Bulk link hygiene: `.mermaid -> .mmd` in file references; fixes wrong target for `30-port-adapter-mapping`. | No changes. |
| `docs/02-architecture/mmd-diagrams/docs/00-diagramming-policy.md` | No changes. | No changes. | Large reduction/refactor: historical long policy replaced by compact canonical-pointer policy text. | No changes. |
| `docs/02-architecture/mmd-diagrams/00-legend.mmd` | **New file** (legend diagram, classes + linkStyle legend blocks). | No changes. | No changes. | No changes. |
| `scripts/lint_diagrams.py` | Adds skip logic for superseded/legend diagrams; introduces approved fill list checks integration. | No changes. | Includes same lint hardening (+ additional updates from newer line base): keeps skip logic and expands lint policy checks. | Same change profile as fUJUM in this file (+71/-12 vs local). |
| `scripts/check_diagram_quality_gates.py` | No changes. | No changes. | Hardens edge parser: detects more forbidden operators (`x--`, `<--`, `<==>`), strips quoted text before operator validation to reduce false positives. | No changes. |
| `scripts/fix_diagram_links.py` | No changes. | No changes. | Refactored to safer regex-only markdown link rewrites (`.mmd -> .mermaid` in links only), typed helpers, explicit return code. | No changes. |
| `scripts/uniform_diagram_sizes.py` | No changes. | No changes. | Regex bugfix for node label closing bracket pattern (`\"]\)` variant). | No changes. |
| `scripts/add_svg_text_fallback.py` | No changes. | No changes. | Refactor to in-memory processing (`_process_tree`), explicit `write` flag; check/dry-run paths no longer rely on restoring original text. | No changes. |
| `scripts/reindex_linkstyles.py` | No changes. | No changes. | No changes. | **New file**: audit/check tool for stale `linkStyle` indices (check/fix reporting mode). |
| `mkdocs.yml` | Adds `validation` + `not_in_nav`, removes index pages from nav, keeps docs strictness maintenance. | No changes. | Compared to local: branch is missing local `mkdocs.yml` updates (net `0/+8` from local perspective). | Same as fUJUM for `mkdocs.yml` delta vs local (missing local updates). |
| `.github/workflows/docs.yml` | Adds workflow `concurrency` block (`group`, `cancel-in-progress`). | No changes. | No changes. | No changes. |
| `assets/javascripts/MERMAID_VERSION` | No changes. | No changes. | `10.4.0 -> 10.6.1`. | No changes. |
| `assets/javascripts/mermaid-loader.js` | No changes. | No changes. | Embedded default Mermaid version `10.4.0 -> 10.6.1`. | No changes. |
| `assets/stylesheets/mermaid.css` | No changes. | No changes. | No changes. | Adds embedded-mermaid contrast/style layer (cluster/node shadowing, edge label weight, hover feedback). |

## Notes

- `claude/audit-fix-diagrams-hZglG` is mostly diagram-source normalization; render/theme/script layer impact is intentionally minimal.
- `claude/improve-diagram-design-K2XMN` introduces dark-mode rendering flow in `render.sh` and `custom-dark.css`, but does **not** include `mermaid-config-dark.json`, so dark-mode config switch is only partially wired.

