# Dashboard UX residual — post-DSA screenshot audit (DUX3)

**Status:** published (local pack; GH numbers filled after publish)
**Wave code:** DUX3
**Date:** 2026-07-29
**Source audit:** `BIOETL-GRAFANA-UX-AUDIT-20260729-085334` (screenshot-first, read-only)
**Plan anchor:** session verification of audit vs `grafana/dashboards/*.json` + closed DS2/DSA residual
**Baseline:** local `main` at pack authoring (2026-07-29)

**Predecessors (closed / do not re-open as-is):**
- #6800 DUX Phase-1
- #6844 DRM residual semantics
- #6853 DRM-R layout residual
- #6901 DS2 refactor (W0–W1)
- #6911 ADR-053 Scenes shell
- #6915 DSS Scenes scaffold
- #6982 DSA deep-audit residual (A0–A2 closed)

## Context

DSA closed contract/narrative residuals and shipped `state × confidence × basis × next_action` grammar mostly in **panel descriptions**. A follow-up **screenshot UX audit** (2026-07-29) still finds operator-facing residual:

1. **Scope collision** — NOW / RANGE / RUN / WORKFLOW / GLOBAL mixed without durable visual grammar
2. **UNKNOWN as universal bucket** — missing, empty selection, valid-empty, stale, backend error collapse to one word
3. **Area spent on giant words/zeros** — UNKNOWN/OK/SCRAPING/100%/0 dominate; cause/confidence/action below fold
4. **Cross-dashboard contradictions** at the same selection (Runtime OK+SCRAPING vs Gold accounting; Provider 0/0 green; Trust Replay Safety OK vs INCOMPLETE; Incident cross-pipeline suspect)

This wave is **not** greenfield rewrite, not UID retirement, not re-open of DS2-01…09 / DSA-01…08 as-is.
This wave is **post-DSA residual enforcement**: evidence lock → semantic P0 → first-screen compression → regression gates.

## Accepted decisions (normative)

| # | Topic | Decision |
| --- | --- | --- |
| 1 | Portfolio | Keep **7 stable UIDs**; logical IA = 6 task workspaces (Trust+DQ tabs only via Scenes/IA) |
| 2 | Migration | Surgical JSON edits on SOT `grafana/dashboards/*.json`; no second monorepo tree |
| 3 | Shadow | Scenes dual-path only where ADR-053 allows; not a Wave-0 rewrite |
| 4 | Incident | Remains **read-only** (no owner/ack without ADR + backend) |
| 5 | Viz | Node graph / Sankey / waterfall only **contract-gated** (track); no invent metrics |
| 6 | Measurement | Usability **proxies** only; no causal MTTD/MTTI/MTTR claims |
| 7 | Grammar | First-screen cell = `scope × family × state × evidence quality × action` |

## Constraints (all children)

- Portfolio ≤7; do not delete Trust/DQ UIDs in this wave
- ADR-010: Grafana optional; no required Docker/Redis
- No invent metrics; no `run_id` Prometheus labels
- No Loki/Tempo/Silver Reject UI without ADR
- Tech-debt budgets must not increase
- Color secondary; green only with expectedness; expected absence must not look broken
- Execution phase must not use health color
- Rollback unit = one PR/issue; preserve panel IDs where possible
- SOT: repo dashboard JSON; screenshots are evidence, not edit authority

## Portfolio (fixed UIDs)

| # | uid | Audit shot | Role |
| ---: | --- | --- | --- |
| 0 | `bioetl-control-plane-v1` | S7 | Trust / Recovery |
| 1 | `bioetl-overview-v2` | S6 | Operations Home |
| 2 | `bioetl-runtime` | S5 | Pipeline Diagnostics |
| 3 | `bioetl-provider-health-v2` | S4 | Provider Health |
| 4 | `bioetl-dq-v2` | S3 | Data Quality |
| 5 | `bioetl-incident-v1` | S2 | Incident Workspace (read-only) |
| 6 | `bioetl-run-explorer-v1` | S1 | Run Explorer (exact-run hub) |

## Issue matrix

| Code | Issue | Pri | Wave | Title |
|------|-------|-----|------|-------|
| DUX3-00 | [#7053](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7053) | meta | epic | Dashboard UX residual (post-DSA screenshot audit) |
| DUX3-01 | [#7054](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7054) | P0 | W0 | Evidence pack — first-screen inventory + query/variable dump |
| DUX3-02 | [#7055](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7055) | P0 | W0 | Scope grammar SSOT — panel → NOW/RANGE/RUN/WORKFLOW/GLOBAL |
| DUX3-03 | [#7056](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7056) | P0 | W0 | Zero / UNKNOWN / color contract (no green 0/0, no red expected zero) |
| DUX3-10 | [#7057](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7057) | P0 | W1 | Runtime — split Execution Status vs Telemetry Confidence (SCRAPING) |
| DUX3-11 | [#7058](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7058) | P0 | W1 | Provider — applicability gate + zero-denominator honesty |
| DUX3-12 | [#7059](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7059) | P0 | W1 | DQ — first-screen UNKNOWN vs 100% contradiction |
| DUX3-13 | [#7060](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7060) | P0 | W1 | Trust — qualify Replay Safety + fix red expected zeros |
| DUX3-14 | [#7061](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7061) | P1 | W1 | Incident — mark cross-pipeline blast-radius scope |
| DUX3-15 | [#7062](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7062) | P1 | W1 | Typed UNKNOWN expansion (MISSING/STALE/N/A/VALID_EMPTY/…) |
| DUX3-20 | [#7063](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7063) | P1 | W2 | Overview — freshness/confidence + blast radius above fold |
| DUX3-21 | [#7064](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7064) | P1 | W2 | Runtime — compact verdict strip + layout compression |
| DUX3-22 | [#7065](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7065) | P1 | W2 | Provider — fleet-first layout residual |
| DUX3-23 | [#7066](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7066) | P1 | W2 | DQ — promote Medallion accounting; demote giant scores |
| DUX3-24 | [#7067](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7067) | P1 | W2 | Trust — gate strip + collapse forensics |
| DUX3-25 | [#7068](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7068) | P1 | W2 | Run Explorer — selected-run narrative above browse table |
| DUX3-26 | [#7069](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7069) | P1 | W2 | Finish DSA-04 — ID/Processed Records off first screen (non-Run boards) |
| DUX3-27 | [#7070](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7070) | P1 | W2 | Scroll hygiene — kill internal scrollbars; shrink giant stats |
| DUX3-30 | [#7071](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7071) | P2 | W3 | Scope badge chrome consistency across 7 boards |
| DUX3-31 | [#7072](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7072) | P2 | W3 | Color/token contract + non-color cues + contrast notes |
| DUX3-32 | [#7073](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7073) | P2 | W3 | Screenshot regression at 1366 / 1440 / 1920 |
| DUX3-33 | [#7074](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7074) | P2 | W3 | Semantic fixture states for empty/trust/error classes |
| DUX3-34 | [#7075](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7075) | P2 | W3 | Data-link contract re-check (time/vars; run_id only run-scoped) |
| DUX3-35 | [#7076](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7076) | P2 | W3 | Usability proxy remeasure (proxies only) |
| DUX3-40 | [#7077](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7077) | P3 | track | Track — Scenes tabs / viz upgrades / UID cutover (no unsolicited impl) |

## Delivery order

1. **PR-W0** DUX3-01 → DUX3-02 → DUX3-03 (evidence then contracts; blocks trustworthy redesign)
2. **PR-W1a…f** DUX3-10…15 (parallelizable by board after W0)
3. **PR-W2a…h** DUX3-20…27 (layout compression; DUX3-26 may land with each board or as final sweep)
4. **PR-W3** DUX3-30…35 (gates + a11y + remeasure)
5. **Track** DUX3-40 only when ADR/data gates open

## Wave exit criteria

### W0
- [ ] First-screen inventory committed for 7 UIDs (id/title/type/gridPos/datasource/scope intent)
- [ ] Scope SSOT documented + testable mapping for first-screen panels
- [ ] Zero/UNKNOWN/color contract written; checklist covers green 0/0 and red expected zero bans

### W1
- [ ] Runtime: execution vs telemetry not peer health cards
- [ ] Provider: empty selection / zero denominator not green success
- [ ] DQ: first screen does not show UNKNOWN + VALID_EMPTY + dual 100% as peer truths
- [ ] Trust: Replay Safety evidence-qualified; overall INCOMPLETE owns headline when incomplete
- [ ] Incident: cross-pipeline suspects labeled WORKFLOW/GLOBAL when not pipeline-filtered
- [ ] Typed reasons preferred over bare UNKNOWN where series already distinguish

### W2
- [ ] Each board first viewport: ≤1 dominant viz + ≤4 compact verdict cells
- [ ] ID/Processed Records not first-screen KPI on ≥3 non-Run boards (collapsed thin shell only)
- [ ] No internal vertical scrollbars on triage text panels
- [ ] Giant stats reduced to compact grid budget

### W3
- [ ] Scope badge chrome consistent
- [ ] Screenshot regression hooks/docs for 1366/1440/1920
- [ ] Semantic fixture list documented
- [ ] Data-link contract re-verified
- [ ] Usability proxies updated (no MTT* claims)

### Track
- [ ] Scenes Trust+DQ tabs / viz / UID cutover only with ADR + data contract

## Rejected in this wave

- Immediate portfolio shrink / delete Trust or DQ UID
- Merge Runtime + Run Explorer into one board
- One mega-dashboard
- Incident owner/ack write-path
- Topology / Sankey / waterfall without contract gate
- Causal MTT* as release KPI
- Greenfield shadow monorepo replacing SOT JSON
- Inventing Prometheus metrics for prettier UI

## Target first viewport (all triage boards)

```text
[Nav bus h≤3]
[Context: workflow/pipeline/run_type · range · freshness · scope legend]
[Health | Execution | Evidence | Impact]  ≤4 compact cells
[Primary cause / VALID_EMPTY reason | Primary action]
[One dominant viz: matrix | timeline | funnel]
── fold ──
[Collapsed forensics / ID shell / trends]
```

## Evidence anchors

- Audit report: BIOETL-GRAFANA-UX-AUDIT-20260729-085334 (screenshots S1–S7)
- SOT JSON: `grafana/dashboards/*.json`
- Operator UX: `docs/03-guides/dashboards/operator-ux-v2.md`, `verdict-ontology.md`
- Prior packs: `DS2-2026-07-28-*.md`, `DSA-2026-07-28-*.md`
- ADR-010 optional Grafana; ADR-053 optional Scenes shell
- Tests: `tests/integration/test_grafana_*.py`, `test_pipeline_runtime_dashboard.py`
- Bodies: `.github/ISSUES/_dux3_bodies/`

## Publish record

- Local bodies ready under `_dux3_bodies/`
- After `gh issue create`, fill Issue column + write `reports/quality/dux3-2026-07-29-issue-publish.json`

## Suggested publish commands

```bash
# Epic first
gh issue create --title "chore(grafana): DUX3 epic — dashboard UX residual post-DSA screenshot audit" \
  --body-file .github/ISSUES/_dux3_bodies/DUX3-00.md \
  --label "observability,grafana,technical-debt"

# Then children (set EPIC=<number>)
# for code in 01 02 03 10 11 12 13 14 15 20 21 22 23 24 25 26 27 30 31 32 33 34 35 40; do
#   gh issue create --title "$(rg -n "DUX3-$code" .github/ISSUES/_dux3_bodies/TITLES.md)" \
#     --body-file ".github/ISSUES/_dux3_bodies/DUX3-$code.md"
# done
```
