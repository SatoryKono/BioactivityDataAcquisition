# Grafana dashboard cycle-1 issue pack — 2026-08-17

**Wave code:** DASH-CYCLE  
**Date:** 2026-08-17  
**Plan:** `reports/observability/remediation/20260817/plan_dashboard_cycle1.md`  
**Audit:** seven shipped dashboards, gate **BLOCK**, selectors
`workflow=chembl_baseline`, `pipeline=chembl_assay`, `run_type=backfill`,
`run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b`.

Siblings (do **not** reopen):

- OBS-FILL [#8927](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8927) / PR [#8933](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/8933)
- GRAF-TRUST [#8935](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8935) / leftover generator work from [#8937](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8937)

## Constraints (all children)

- No `.env` mutation
- No tech-debt budget / threshold / exemption increase
- No invented Prometheus series; no `run_id` Prom labels
- No PromQL `or vector(0)` on first-screen verdicts
- Do not map `UNKNOWN` / `INCOMPLETE` / `EMPTY DOMAIN` / `None observed` to healthy
- Do not rewrite D0–D5 PromQL to hide CRIT / `RULE/SERIES GAP`
- Grafana remains optional (ADR-010)

## Issue matrix

| Code | Pri | Issue | Title |
| --- | --- | --- | --- |
| DASH-CYCLE-00 | meta/P1 | [#8944](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8944) | Unblock seven-dashboard cycle-1 (gate BLOCK) |
| DASH-CYCLE-001 | P1 | [#8946](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8946) | Run Explorer loses selected-run Infinity binding |
| DASH-CYCLE-002 | P1 | [#8947](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8947) | Prove OBS-FILL live after bioetl recreate |
| DASH-CYCLE-003 | P1 | [#8945](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8945) | Panel-matrix generator still locked at 226 |
| DASH-CYCLE-005 | P2 | [#8948](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8948) | Cycle-2 re-audit of repaired D6 and unfinished visual matrix |

**Not opened:** DASH-CYCLE-004 (`max_over_time` 41 vs 40). Policy and live
count are both 41 on this tree and `origin/main`.

## Dependency order

1. [#8946](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8946) — WP-0 Inspect URL/payload, then WP-1 JSON/tests
2. [#8945](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8945) — parallel; no Grafana required
3. [#8947](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8947) — independent ops; do not rewrite D0–D5 JSON while open
4. [#8948](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8948) — last, after 001 re-render and 003 `--check`

## Current-tree facts (do not re-count from memory)

| Surface | Count |
| --- | ---: |
| JSON leaf+row | 235 |
| YAML `panel_count` sum | 235 |
| `EXPECTED_PANEL_COUNT` | 226 |
| `reviewed_expression_count` | 41 = live 41 |
