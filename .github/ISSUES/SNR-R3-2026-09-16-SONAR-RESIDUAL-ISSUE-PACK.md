# SonarCloud residual remediation issue pack (SNR-R3)

**Status:** open (published 2026-09-16)  
**Wave code:** SNR-R3  
**Date:** 2026-09-16  
**Epic:** [#10477](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10477)  
**Predecessor epic:** [#8366](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8366) (closed, SNR-R2)  
**Publish artifact:** `reports/quality/snr-r3-2026-09-16-issue-publish.json`  
**Project:** `SatoryKono_BioactivityDataAcquisition`

## Why SNR-R3

SNR-R2 closed at `open=0` / quality gate OK (ledger 2026-08-20). Live snapshot on `origin/main` `91166c5f` (2026-09-16) is again **29 OPEN**, gate **ERROR**, security rating **C** because of one new vulnerability.

This is a **new residual**, not the historical 726-issue backlog.

## Live snapshot (2026-09-16)

| Metric | Value |
|--------|------:|
| OPEN | **29** |
| Bugs | 0 |
| Vulnerabilities | **1** |
| Code smells | 28 |
| Quality gate | **ERROR** |
| Security rating | **C** |
| Reliability | A |
| `sqale_index` | 420 min |
| Analysis revision | `91166c5f` (= `origin/main`) |

Rules: `python:S3776` (14), `python:S1192` (5), `python:S3358` (5), `javascript:S7744` (1), `python:S1481` (1), `python:S5886` (1), `python:S7504` (1), `pythonsecurity:S8705` (1).

## Issue matrix (published)

| Code | Issue | Pri | Wave | Title |
|------|------:|-----|------|-------|
| SNR-R3-00 | [#10477](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10477) | meta | 0 | Epic: residual burn-down |
| SNR-R3-01 | [#10478](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10478) | P0 | R1 | Delete CodeRabbit recovery pack (S8705) |
| SNR-R3-02 | [#10479](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10479) | P1 | R2 | `recent_pipeline_runs.py` (5 keys) |
| SNR-R3-03 | [#10480](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10480) | P1 | R3 | `src/bioetl` control-plane / observability (6 keys) |
| SNR-R3-04 | [#10481](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10481) | P1 | R4 | Grafana dashboard state follow-up (7 keys) |
| SNR-R3-05 | [#10482](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10482) | P1 | R5 | `render_nav_bus` complexity + S1192 (5 keys) |
| SNR-R3-06 | [#10483](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10483) | P2 | R6 | Grafana/QA long-tail (3 keys) |
| SNR-R3-07 | [#10484](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10484) | P0 | R7 | Closeout total=0 + gate OK |

## Delivery order

1. **#10478** live security (unblocks rating A)
2. **#10479** HTTP catalog
3. **#10480** remaining `src/bioetl`
4. **#10481** ‖ **#10482** Grafana follow-up / nav-bus
5. **#10483** long-tail
6. **#10484** closeout → close **#10477**

## Constraints (all children)

- Do **not** increase tech-debt budgets / thresholds / `sonar.*exclusions`
- Do **not** mass-`NOSONAR` without per-sink confinement/validation evidence
- Hex/DDD/import matrix intact; agent runtimes stay out of `src/bioetl`
- Behavior-changing fixes need regression tests
- Prefer small file-cluster PRs; track by Sonar **key** + rule + path
- Grafana Docker stack only if explicitly needed (ADR-010)
- No `.env*` create/edit/delete without explicit per-task user approval
- Work from a feature branch, not `main`

## Exit (epic)

- [ ] Live residual ledger refreshed under `reports/quality/sonar/`
- [ ] Sonar `statuses=OPEN` total = **0**
- [ ] Quality gate **OK**; security rating **A**
- [ ] No budget/exclusion growth
- [ ] Inventory hash current if `src/bioetl` touched
