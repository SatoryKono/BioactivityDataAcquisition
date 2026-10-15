# SonarCloud residual remediation issue pack (SNR-R2)

**Status:** open (published 2026-08-07)  
**Wave code:** SNR-R2  
**Date:** 2026-08-07  
**Epic:** [#8366](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8366)  
**Predecessor epic:** [#6938](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6938) (closed)  
**Predecessor PR:** [#6936](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/6936)  
**Plan SSOT:** `reports/plans/sonar-remediation-residual-2026-08-07/01-plan-residual.md`  
**Ledger (post-#6936):** `reports/quality/sonar/live-issues-20260728-postmerge-full.json`  
**Publish artifact:** `reports/quality/snr-r2-2026-08-07-issue-publish.json`  
**Project:** `SatoryKono_BioactivityDataAcquisition`

## Why SNR-R2

SNR-R (#6938–#6948) was closed while Sonar residual remained open (postmerge ledger **435**; later claim ~382). SNR-R2 is the **honest residual burn-down** to `total=0` + quality gate **OK**.

## Progress context

| Checkpoint | Total | Blocker | Bugs | Vulns | Smells |
|------------|------:|--------:|-----:|------:|-------:|
| Program start | 726 | 5 | 9 | 113 | 604 |
| Post-#6936 ledger | **435** | 0 | 0 | **26** | **409** |
| Later tip (claim) | ~382 | 0 | 0 | ~5 | ~377 |

## Issue matrix (published)

| Code | Issue | Pri | Wave | Title |
|------|------:|-----|------|-------|
| SNR-R2-00 | [#8366](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8366) | meta | 0 | Epic: residual burn-down |
| SNR-R2-01 | [#8372](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8372) | P0 | W0′ | Live Sonar rebaseline + ledger |
| SNR-R2-02 | [#8368](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8368) | P0 | R1 | Security residual (26 vulns) |
| SNR-R2-03 | [#8367](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8367) | P0 | R2 | `src/bioetl` maintainability (~96) |
| SNR-R2-04 | [#8369](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8369) | P1 | R3 | Complexity S3776 residual |
| SNR-R2-05 | [#8371](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8371) | P1 | R4 | S1192 duplicated literals |
| SNR-R2-06 | [#8370](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8370) | P2 | R5 | Python long-tail smells |
| SNR-R2-07 | [#8375](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8375) | P2 | R6 | Shell / PowerShell residual |
| SNR-R2-08 | [#8377](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8377) | P2 | R7 | JS / GHA / Docker residual |
| SNR-R2-09 | [#8376](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8376) | P1 | R8 | Ghost / missing-path cleanup |
| SNR-R2-10 | [#8378](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8378) | P0 | R9 | Closeout total=0 + gate OK |

## Delivery order

1. **#8372** live rebaseline (unblocks honest key lists)  
2. **#8368** security residual  
3. **#8367** product `src/bioetl`  
4. **#8369** complexity  
5. **#8371** S1192  
6. **#8370 ‖ #8375 ‖ #8377** long-tail / shell / JS-GHA-Docker  
7. **#8376** ghost paths  
8. **#8378** closeout → close **#8366**

## Constraints (all children)

- Do **not** increase tech-debt budgets / thresholds / `sonar.*exclusions`
- Do **not** mass-`NOSONAR` without per-sink confinement/validation evidence
- Hex/DDD/import matrix intact; agent runtimes stay out of `src/bioetl`
- Behavior-changing fixes need regression tests
- Prefer small file-cluster PRs; track by issue **key** + rule + path
- Grafana Docker stack only if explicitly needed (ADR-010)
- No `.env*` create/edit/delete without explicit per-task user approval

## Exit (epic)

- [ ] Live residual ledger refreshed under `reports/quality/sonar/`
- [ ] Sonar `resolved=false` total = **0** (or reviewed exceptions only)
- [ ] Quality gate **OK**
- [ ] No budget/exclusion growth
- [ ] Inventory hash current if `src/bioetl` touched
