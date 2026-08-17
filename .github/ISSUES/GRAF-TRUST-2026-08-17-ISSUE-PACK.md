# Grafana Trust / exact-run evidence issue pack — 2026-08-17

**Wave code:** GRAF-TRUST
**Date:** 2026-08-17
**Plan:** `reports/observability/remediation/20260817/plan_grafana_trust_rf_audit.md`

This wave is the remaining Lane A from the seven-dashboard QA plan
(GRAF-QA-001…011). It does **not** replace OBS-FILL (#8927–#8932 / PR #8933).

## Constraints (all children)

- No `.env` mutation
- No tech-debt budget / threshold / exemption increase
- No `run_id` Prometheus labels
- No PromQL `or vector(0)` on first-screen verdicts
- No raising forensic HTTP deadline or `retention_days`
- Additive HTTP fields only; do not map `UNKNOWN` → `OK`
- Do not implement on the dirty `#8859` / OBS-FILL worktree

## Issue matrix

Created live in the same session as this pack. Fill numbers after create.

| Code | Pri | Issue | Title |
| --- | --- | --- | --- |
| GRAF-TRUST-00 | meta/P0 | TBD | Separate processing success from Trust / replay readiness |
| GRAF-TRUST-01 | P0 | TBD | Trust status model and HTTP contract |
| GRAF-TRUST-02 | P0 | TBD | Repair write-side lineage closure and identity |
| GRAF-TRUST-03 | P1 | TBD | Persist manifest contract / replay-anchor evidence |
| GRAF-TRUST-04 | P0 | TBD | Make retention evidence run-scoped |
| GRAF-TRUST-05 | P1 | TBD | Forensic HTTP budget and failure rendering |
| GRAF-TRUST-06 | P1 | TBD | Trust D0 UX, inventory, and docs closeout |

## Dependency order

1. GRAF-TRUST-01
2. GRAF-TRUST-02, GRAF-TRUST-03, GRAF-TRUST-04 in parallel after 01
3. GRAF-TRUST-05 after 04
4. GRAF-TRUST-06 last (after 01–05; D1–D6 stay on #8932)
