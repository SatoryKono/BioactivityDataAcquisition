# Dashboard readability re-audit residual — DUX6

**Status:** closed (2026-07-29)
**Wave code:** DUX6
**Date:** 2026-07-29
**Source audit:** re-submitted screenshot UX audit SG-01..SG-07 (WARN / redesign required)
**Predecessor:** DUX5 epic #7116 (closed #7117–#7133)
**Audit mode:** read-only screenshot-based; no JSON/Prometheus/API edits during capture

## Context

DUX5 closed **contract/copy residual** from the same audit family. The re-submitted
screenshot report still rates the portfolio **WARN / redesign required** because
operator-visible pixels still allow dangerous interpretations (bare UNKNOWN, giant
100%/0, scroll/clipping, full UUIDs, Value # headers).

**DUX6 = residual live/pixel enforcement after DUX5.**

## Critical P0

1. Formal Health/Execution/Evidence/Applicability instead of bare UNKNOWN/No data/VALID_EMPTY/0
2. No internal scroll on mandatory triage; Status/Reason/Impact/Action simultaneous
3. Fix literal Markdown, Value #*, clipping, metric/copy mismatch (Provider)
4. Not started for inapplicable Silver/Gold; red only for confirmed failure

## Critical P1

1. Neutral surface + severity strip vs full-color stat backgrounds
2. Short IDs + Copy/Open
3. Typography tokens + no auto-shrink below floors

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DUX6-00 | #7139 | meta | epic | chore(grafana): DUX6 epic — screenshot readability re-audit residual after DUX5 |
| DUX6-01 | #7140 | P0 | V1 | feat(grafana): DUX6-01 Replace ambiguous UNKNOWN and generic No data (residual) |
| DUX6-02 | #7141 | P0 | V1 | refactor(grafana): DUX6-02 Remove internal scrollbars from mandatory triage panels (residual) |
| DUX6-03 | #7142 | P0 | V1 | fix(grafana): DUX6-03 Fix false-red and zero-state applicability (residual) |
| DUX6-04 | #7143 | P0 | V1 | fix(grafana): DUX6-04 Repair raw Markdown, copy mismatches and exposed endpoint syntax (residual) |
| DUX6-05 | #7144 | P0 | V1 | fix(grafana): DUX6-05 Replace meaningless table headers and prevent clipping (residual) |
| DUX6-06 | #7145 | P0 | V1 | feat(grafana): DUX6-06 Shorten long identifiers and add copy actions (residual) |
| DUX6-10 | #7146 | P1 | V2 | chore(grafana): DUX6-10 Adopt a dashboard typography token system (residual) |
| DUX6-11 | #7147 | P1 | V2 | feat(grafana): DUX6-11 Standardize the operator status card (residual) |
| DUX6-12 | #7148 | P1 | V2 | refactor(grafana): DUX6-12 Normalize panel titles and operator vocabulary (residual) |
| DUX6-13 | #7149 | P1 | V2 | refactor(grafana): DUX6-13 Redesign selectors and navigation (residual) |
| DUX6-14 | #7150 | P1 | V2 | refactor(grafana): DUX6-14 Consolidate repeated Run context and accounting (residual) |
| DUX6-20 | #7151 | P2 | V3 | docs(grafana): DUX6-20 Rewrite verbose panel body copy (residual) |
| DUX6-21 | #7152 | P2 | V3 | refactor(grafana): DUX6-21 Refactor dense forensic tables (residual) |
| DUX6-22 | #7153 | P2 | V3 | refactor(grafana): DUX6-22 Rationalize charts and empty-state panels (residual) |
| DUX6-23 | #7154 | P2 | V3 | fix(grafana): DUX6-23 Align units, precision and numeric grammar (residual) |
| DUX6-30 | #7155 | P3 | V4 | docs(grafana): DUX6-30 Establish copy and library-panel governance (residual) |
| DUX6-31 | #7156 | P3 | V4 | test(grafana): DUX6-31 Add screenshot and accessibility regression matrix (residual) |

## Delivery order

1. V1 P0: DUX6-01 → 02 → 03 → 04 → 05 → 06
2. V2 P1: DUX6-10 → 11 → 12 → 13 → 14
3. V3 P2: DUX6-20 → 21 → 22 → 23
4. V4 P3: DUX6-30 → 31

## Exit criteria (summary)

### V1
- Live first-screen cards never show bare UNKNOWN without reason class
- Zero internal scroll on Status/Provenance/First Action/Next actions at 1366
- Red zero only on validated failure; Not started labelled
- No Value #* / raw endpoints / VALID_EMPTY tokens in bodies
- Short IDs + copy path without Prom cardinality

### V2–V4
- Typography floors enforced in render evidence
- Status card pattern dominant; compact run strip outside explorer
- Tables/charts/copy residual closed
- Live screenshot matrix + governance owners documented

## Constraints

- 7 UIDs; no invent metrics; no Prom run_id; incident read-only
- Titles Approach B unless harness lands first
- Verdict logic outside Grafana transforms

## Evidence

- Parsed roadmap: `reports/quality/_ux_audit_roadmap_parsed_reaudit.json`
- Bodies: `.github/ISSUES/_dux6_bodies/`
- DUX5 closeout: `reports/quality/dux5-2026-07-29-closeout.md`
- Docs: `dux5-copy-dictionary.md`, `dux5-screenshot-regression-protocol.md`

## Publish record

- Closed: 2026-07-29 (epic #7139 + #7140–#7156)
- Closeout: `reports/quality/dux6-2026-07-29-closeout.md`

- Published at: 2026-07-29T09:28:32Z
- Epic: #7139
- Record: 
- Issues: 18 (1 epic + 17 children)
- Predecessor: DUX5 #7116
