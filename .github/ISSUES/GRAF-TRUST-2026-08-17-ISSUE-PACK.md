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

| Code | Pri | Issue | Title |
| --- | --- | --- | --- |
| GRAF-TRUST-00 | meta/P0 | [#8935](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8935) | Separate processing success from Trust / replay readiness |
| GRAF-TRUST-01 | P0 | [#8939](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8939) | Trust status model and HTTP contract |
| GRAF-TRUST-02 | P0 | [#8940](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8940) | Repair write-side lineage closure and identity |
| GRAF-TRUST-03 | P1 | [#8938](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8938) | Persist manifest contract / replay-anchor evidence |
| GRAF-TRUST-04 | P0 | [#8941](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8941) | Make retention evidence run-scoped |
| GRAF-TRUST-05 | P1 | [#8936](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8936) | Forensic HTTP budget and failure rendering |
| GRAF-TRUST-06 | P1 | [#8937](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8937) | Trust D0 UX, inventory, and docs closeout |

## Dependency order

1. [#8939](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8939)
2. [#8940](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8940), [#8938](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8938), [#8941](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8941) after 01
3. [#8936](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8936) after 04
4. [#8937](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8937) last (D1–D6 stay on #8932)
