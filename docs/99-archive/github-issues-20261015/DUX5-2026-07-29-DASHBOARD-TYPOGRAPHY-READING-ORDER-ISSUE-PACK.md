# Dashboard typography & operator reading-order residual — DUX5

**Status:** closed (2026-07-29)
**Wave code:** DUX5
**Date:** 2026-07-29
**Source audit:** read-only screenshot UX audit (SG-01..SG-07; Run Explorer to Trust)
**Predecessor wave:** DUX4 epic #7088 (visual enforcement) after DUX3 #7053
**Baseline:** post-DUX4 working tree / local `main`
**Audit mode:** screenshot-based only — no dashboard JSON/provisioning/Prometheus/API/code changes during audit

## Context

DUX3 closed **contracts** (scope/family/typed-state grammar, shell collapse).
DUX4 closed **visual enforcement residual** at contract/description + partial pixel level.

A **second-pass screenshot audit** still rates the system **WARN / redesign required** because:

1. Typography/color/text structure do **not** enforce operator decision order
2. Largest on-screen objects are often bare `UNKNOWN` / `OK` / `SCRAPING` / `INCOMPLETE` / `100.00%` / `0`
3. Reason, impact, confidence, and action are missing, microtext, under fold, or behind **internal scrollbars**
4. Provider Health shows literal Markdown / copy mismatches; Incident shows `Value #*` headers
5. Zeros can read as failure or health without **applicability**

This wave is **DUX5 = operator reading-order + typography + copy safety**.
It is **not** a greenfield rewrite and **not** a reopen of DUX4 as failed — it is residual evidence from screenshots.

## Accepted decisions (normative)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Portfolio | Keep **7 stable UIDs** |
| 2 | SOT | Surgical edits to `grafana/dashboards/*.json` after live JSON validation |
| 3 | Reading order | Context → Status → Reason → Impact → Action → Evidence |
| 4 | Ownership | Run Explorer = forensic detail; domain boards = concise decisions; Overview = routing; Incident = ranked triage; Trust = replay confidence |
| 5 | Semantics | Health / Execution / Evidence / Applicability vocabularies; Grafana renders bounded states only |
| 6 | Metrics | No invent metrics; no Prom `run_id` labels |
| 7 | Incident | Read-only |
| 8 | Measurement | Screenshot + geometry/text-floor assertions (no MTT*) |

## Screenshot inventory

| Group | Dashboard | File | Notes |
| --- | --- | --- | --- |
| SG-01 | Run Explorer | `Snag_8cefdb5.png` | Tall; Record accounting partially visible |
| SG-02 | Incident Workspace | `Snag_8cefe90.png` | First-screen-like |
| SG-03 | Data Quality | `Snag_8cefeee.png` | ~1366-class width capture |
| SG-04 | Provider Health | `Snag_8ceffd8.png` | Top titles may be cropped (UNKNOWN evidence) |
| SG-05 | Pipeline Diagnostics | `Snag_8cf0084.png` | Narrow stitched; density stress |
| SG-06 | Overview | `Snag_8cf0268.png` | Tall; unused space around Workflow status |
| SG-07 | Trust | `Snag_8cf0334.png` | Very narrow; worst-case identity tables |

> Image size is not a guaranteed browser viewport. Live validation required for zoom/DPR/fonts.

## Critical conclusions (from audit)

### P0

1. Replace bare `UNKNOWN`, `No data`, `VALID_EMPTY`, `N/A`, and context-free `0` with formal **Health / Execution / Evidence / Applicability** model
2. Remove internal vertical scroll from mandatory triage panels; Status/Reason/Impact/Action simultaneous
3. Fix literal Markdown, auto-generated `Value #*` headers, clipping, metric/copy mismatch (Provider Health + tables)
4. Show **Not started** for inapplicable Silver/Gold; red only for confirmed violation

### P1

1. Neutral surface + icon/badge/severity strip instead of full-color stat backgrounds by default
2. Shorten IDs/paths; add Copy/Open; full values in tooltip/explorer/URL
3. Unified typography tokens; forbid auto-shrink below minimums

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DUX5-00 | #7116 | meta | epic | chore(grafana): DUX5 epic — typography & operator reading-order residual (screenshot audit) |
| DUX5-01 | #7117 | P0 | V1 | feat(grafana): DUX5-01 Replace ambiguous UNKNOWN and generic No data |
| DUX5-02 | #7118 | P0 | V1 | refactor(grafana): DUX5-02 Remove internal scrollbars from mandatory triage panels |
| DUX5-03 | #7119 | P0 | V1 | fix(grafana): DUX5-03 Fix false-red and zero-state applicability |
| DUX5-04 | #7120 | P0 | V1 | fix(grafana): DUX5-04 Repair raw Markdown, copy mismatches and exposed endpoint syntax |
| DUX5-05 | #7121 | P0 | V1 | fix(grafana): DUX5-05 Replace meaningless table headers and prevent clipping |
| DUX5-06 | #7122 | P0 | V1 | feat(grafana): DUX5-06 Shorten long identifiers and add copy actions |
| DUX5-10 | #7123 | P1 | V2 | chore(grafana): DUX5-10 Adopt a dashboard typography token system |
| DUX5-11 | #7124 | P1 | V2 | feat(grafana): DUX5-11 Standardize the operator status card |
| DUX5-12 | #7125 | P1 | V2 | refactor(grafana): DUX5-12 Normalize panel titles and operator vocabulary |
| DUX5-13 | #7126 | P1 | V2 | refactor(grafana): DUX5-13 Redesign selectors and navigation |
| DUX5-14 | #7127 | P1 | V2 | refactor(grafana): DUX5-14 Consolidate repeated Run context and accounting |
| DUX5-20 | #7128 | P2 | V3 | docs(grafana): DUX5-20 Rewrite verbose panel body copy |
| DUX5-21 | #7129 | P2 | V3 | refactor(grafana): DUX5-21 Refactor dense forensic tables |
| DUX5-22 | #7130 | P2 | V3 | refactor(grafana): DUX5-22 Rationalize charts and empty-state panels |
| DUX5-23 | #7131 | P2 | V3 | fix(grafana): DUX5-23 Align units, precision and numeric grammar |
| DUX5-30 | #7132 | P3 | V4 | docs(grafana): DUX5-30 Establish copy and library-panel governance |
| DUX5-31 | #7133 | P3 | V4 | test(grafana): DUX5-31 Add screenshot and accessibility regression matrix |

## Delivery order

1. **PR-V1 (P0 safety)** DUX5-01 → DUX5-02 → DUX5-03 → DUX5-04 → DUX5-05 → DUX5-06
   (01 semantics first; 04/05 are small surgical wins; 02/03 layout+color; 06 density)
2. **PR-V2 (system patterns)** DUX5-10 → DUX5-11 → DUX5-12 → DUX5-13 → DUX5-14
3. **PR-V3 (polish)** DUX5-20 → DUX5-21 → DUX5-22 → DUX5-23
4. **PR-V4 (governance)** DUX5-30 → DUX5-31

## Wave exit criteria

### V1 (P0)

- [ ] No primary status card shows bare `UNKNOWN` / `No data` without reason+evidence class
- [ ] Zero internal vertical scroll on first-screen status/reason/action/scope panels at 1366/1440/1920
- [ ] Zero is red only on validated failure; Not started / Not available labelled neutrally
- [ ] No literal Markdown markers, `Value #*` headers, or raw GET URLs in panel bodies
- [ ] Run/Manifest IDs short-form + Copy; no new Prom high-cardinality labels

### V2 (P1)

- [ ] Typography token floors enforced (body >=13px, secondary >=12px, table >=12px, axis >=11px at 1366)
- [ ] First-screen status card pattern on domain boards (state+reason+action visible)
- [ ] Titles <=2 lines; nav active state distinguishable without color alone
- [ ] Non-explorer boards use compact run strip; forensic tables owned by Run Explorer

### V3 (P2)

- [ ] Primary cards pass 5-second comprehension review
- [ ] Dense tables limited to operator columns; full evidence one click away
- [ ] Optional empty charts collapsed/below fold
- [ ] Numeric precision/units consistent; denom=0 → Not available

### V4 (P3)

- [ ] Copy dictionary + library-panel ownership documented
- [ ] Screenshot/a11y regression matrix runnable; dark verified; light verified or documented unsupported

## Epic-level acceptance (audit)

- Status, Reason, Impact, Action, Scope, Freshness visually distinct; mandatory action without tooltip/scrollbar
- No bare developer tokens as primary empty states
- Full-color backgrounds not default for OK/zero; color not sole state carrier
- WCAG 2.2 AA contrast against real theme tokens (live measure)
- Verdict semantics not invented only in Grafana transforms

## Constraints / risks

| Risk | Mitigation |
| --- | --- |
| Semantic oversimplification | Caveats in description/runbook; show evidence/freshness on card |
| Plugin limits | Library panels + field overrides first |
| Business logic drift | API/recording-rule owners + contract tests |
| Screenshot brittleness | Assert clipping/geometry/state text ranges, not pure pixels |
| Responsive collapse | 1366/125% is blocking baseline |
| Loss of forensic depth | Keep Run Explorer + Copy/Open paths |

## Assertions still UNKNOWN (require JSON/live)

- Exact fontSize/lineHeight/gridPos/auto-size behavior
- Whether each scrollbar is panel vs row vs capture artifact
- Exact WCAG ratios and theme tokens
- PromQL/transforms/value mappings behind each state
- Root cause of each UNKNOWN/No data
- Whether red Silver zeros are applicability vs real violation
- Whether Provider top titles are hidden or cropped
- Viewport/zoom/DPR of captures
- Keyboard/focus/aria/copy-button behavior
- Light-theme support

## Rejected

- Greenfield rewrite / second monorepo
- Delete Trust or DQ UID
- Incident write-path
- Invent metrics / Prom `run_id`
- Causal MTT* claims

## Evidence anchors

- Parsed roadmap: `reports/quality/_ux_audit_roadmap_parsed.json`
- Bodies: `.github/ISSUES/_dux5_bodies/`
- Publish script: `.github/ISSUES/_dux5_bodies/publish_dux5_issues.py`
- Related docs: `docs/03-guides/dashboards/verdict-ontology.md`, `design-system.md`, `operator-ux-v2.md`, `dux3-residual-contracts.md`
- Nav bus generator: `scripts/ops/observability/grafana/render_nav_bus.py`
- Predecessor pack: `.github/ISSUES/DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md`

## Publish record

- Closed: 2026-07-29 (all children #7117–#7133 + epic #7116)
- Closeout: 

- Published at: 2026-07-29T08:18:01Z
- Epic: #7116
- Record: 
- Issues: 18 (1 epic + 17 children)
