# SonarCloud residual remediation issue pack

**Status:** in progress (SNR-R-01 closed; residual burn-down active on `main`)
**Wave code:** SNR-R
**Date:** 2026-07-28
**Epic:** [#6938](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6938)
**Predecessor PR:** [#6936](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/6936) **merged**
**Plan SSOT:** `reports/plans/sonar-remediation-plan-2026-07-28/01-plan-initial.md`
**Ledger (pre):** `reports/quality/sonar/live-issues-20260728-manifest.json`
**Ledger (post-merge):** `reports/quality/sonar/live-issues-20260728-postmerge-full.json`
**Publish artifact:** `reports/quality/snr-r-2026-07-28-issue-publish.json`
**Project:** `SatoryKono_BioactivityDataAcquisition` (SonarCloud)

### Live progress (server analysis)

| Checkpoint | Total | Blocker | Bugs | Vulns | Smells |
|------------|------:|--------:|-----:|------:|-------:|
| Program start | 726 | 5 | 9 | 113 | 604 |
| Post-#6936 (`85bd9507`) | 435 | 0 | 0 | 26 | 409 |
| Later tip (`41be8ea4`) | **382** | 0 | 0 | **5** | **377** |

## Context

Live SonarCloud baseline at program start (2026-07-28): **~725–726** unresolved, quality gate **ERROR**.

PR **#6936** landed and merged with:

| Wave | Scope | PR commits (approx) |
|------|--------|---------------------|
| W1 | 5 BLOCKER | `b823068c93` |
| W2 | 9 BUG | `b823068c93` |
| W3 | path/cmd taint bulk + Docker/GHA pins | `df522d62c9` |
| W4 partial | campaign / Grafana audit / inventory complexity extracts | `b1edda6971` |

Follow-on `main` commits continue W4t2/W5/security residual burn-down. SNR-R-01 / #6939 is **closed** with post-merge rebaseline artifacts.

## Constraints (all children)

- Do **not** increase tech-debt budgets / thresholds / `sonar.*exclusions`
- Do **not** mass-`NOSONAR` without per-sink confinement/validation evidence
- Hex/DDD/import matrix intact; agent runtimes stay out of `src/bioetl`
- Behavior-changing fixes need regression tests
- Prefer small file-cluster PRs; track by issue **key** + rule + path (not line alone)
- Grafana Docker stack only if explicitly needed for render work (ADR-010)

## Issue matrix (published)

| Code | Issue | Pri | Phase | Title |
|------|------:|-----|-------|-------|
| SNR-R-00 | [#6938](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6938) | meta | 0 | Epic: Sonar residual after #6936 |
| SNR-R-01 | [#6939](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6939) **closed** | P0 | 1 | Merge #6936 + Sonar re-scan rebaseline |
| SNR-R-02 | [#6940](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6940) | P1 | 2 | W4t2: `check_scripts_inventory` S3776 |
| SNR-R-03 | [#6941](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6941) | P1 | 2 | W4t2: Grafana cjs + residual audit panels S3776 |
| SNR-R-04 | [#6942](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6942) | P1 | 2 | W4t2: inventory/semantic residual S3776 |
| SNR-R-05 | [#6943](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6943) | P1 | 3 | W5: S1192 duplicated literals burn-down |
| SNR-R-06 | [#6944](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6944) | P0 | 3 | W3 residual security after re-scan |
| SNR-R-07 | [#6945](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6945) | P2 | 4 | W6: Python long-tail smells |
| SNR-R-08 | [#6946](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6946) | P2 | 4 | W7: PowerShell + shell findings |
| SNR-R-09 | [#6947](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6947) | P2 | 4 | W8: JS / GHA / Docker residual |
| SNR-R-10 | [#6948](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6948) | P1 | 5 | W9: Sonar closeout total=0 + gate OK |

## Delivery order

1. **SNR-R-01** first (merge + rebaseline) — unblocks honest residual counts
2. **SNR-R-02..04** in parallel (W4t2 complexity)
3. **SNR-R-05** + **SNR-R-06** (literals + security residual)
4. **SNR-R-07..09** in parallel where safe
5. **SNR-R-10** closeout

## Exit (epic)

- [ ] #6936 merged; Sonar analysis on tip reflects W1–W4 partial
- [ ] Live residual ledger refreshed under `reports/quality/sonar/`
- [ ] W4t2 / W5 / residual W3 / W6–W8 closed or deferred with dated rationale
- [ ] Sonar `resolved=false` total = **0** (or reviewed exceptions only)
- [ ] Quality gate **OK**; no budget/exclusion growth

## Rejected / out of scope

- Raising Sonar exclusions to greenwash
- Greenfield rewrite of tooling trees
- Starting Grafana monitoring stack for pure smell refactors
