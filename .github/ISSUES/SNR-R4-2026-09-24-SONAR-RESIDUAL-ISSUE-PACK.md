# SonarCloud residual remediation issue pack (SNR-R4)

**Status:** open (published 2026-09-24)  
**Wave code:** SNR-R4  
**Date:** 2026-09-24  
**Epic:** [#10988](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10988)  
**Predecessor epic:** [#10477](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10477) (closed, SNR-R3)  
**Publish artifact:** `reports/quality/snr-r4-2026-09-24-issue-publish.json`  
**Project:** `SatoryKono_BioactivityDataAcquisition`

## Why SNR-R4

SNR-R3 closed at `open=0` / quality gate OK (2026-09-16). Live snapshot on `origin/main` `6b9c73935f1b` (2026-09-24) is again **38 OPEN**, gate **ERROR**. Security rating remains **A** (no vulnerabilities). This is a **new residual**, not the historical 726-issue backlog.

## Live snapshot (2026-09-24)

| Metric | Value |
|--------|------:|
| OPEN | **38** |
| Bugs | 0 |
| Vulnerabilities | 0 |
| Code smells | 38 |
| Quality gate | **ERROR** |
| Security rating | **A** |
| Reliability | A |
| `sqale_index` | 764 min |
| Analysis revision | `6b9c73935f1b` (= `origin/main`) |

Rules: `python:S3776` (15), `python:S1192` (11), `python:S5886` (4), `python:S107` (2), `python:S1172` (1), `python:S1481` (1), `python:S3358` (1), `python:S5655` (1), `python:S5864` (1), `python:S5890` (1).

## Issue matrix (published)

| Code | Issue | Pri | Wave | Title |
|------|------:|-----|------|-------|
| SNR-R4-00 | [#10988](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10988) | meta | 0 | Epic: residual burn-down |
| SNR-R4-01 | [#10989](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10989) | P1 | W1 | dataclasses.replace typing and unused (10 keys) |
| SNR-R4-02 | [#10990](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10990) | P1 | W2 | Grafana custom.* and SELECT RUN constants (9 keys) |
| SNR-R4-03 | [#10991](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10991) | P1 | W3 | Grafana S3776 including apply_corrections CC 300 (10 keys) |
| SNR-R4-04 | [#10992](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10992) | P1 | W4 | HTTP selector complexity and S107 (4 keys) |
| SNR-R4-05 | [#10993](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10993) | P2 | W5 | remaining src/bioetl and census (5 keys) |
| SNR-R4-06 | [#10994](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10994) | P0 | W6 | closeout total=0 + quality gate OK |

## Delivery order

1. **#10989** typing / unused
2. **#10990** Grafana S1192 (on existing grafana WIP branch)
3. **#10991** Grafana S3776 / `apply_corrections` CC 300 (same grafana branch)
4. **#10992** HTTP selector
5. **#10993** remaining `src/bioetl` + census
6. **#10994** closeout → close **#10988**

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
