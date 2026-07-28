# Architecture Refactoring Issue Pack — 2026-07-28

**Audit basis:** Independent architecture quality review (post ARCH-CONT).  
**Independent integral:** **8.82** · committed scorecard **9.11**  
**Prior closed waves:** ARCH-QA (#6740–#6748), ARCH-RES (#6749–#6755), ARCH-CONT (#6757–#6764)

## Snapshot (evidence at pack time)

| Metric | Value | Source |
|---|---|---|
| Layer violations | 0 | scorecard / dep-map |
| Scorecard integral | 9.11 | `architecture-quality-scorecard.json` |
| Independent integral | 8.82 | live architecture review |
| application_core files_ge_250 | 0/5 | hotspot baseline (live) |
| control_plane files_ge_250 | **8/16** | hotspot baseline |
| control_plane max_internal_fan_in | **4/4 at_budget** | hotspot baseline |
| runtime_builders fan-in | 3/5 | hotspot baseline |
| Partial modules | **800** | `module-coverage-inventory.json` |
| Constructor waivers | **1** (intentional `QuarantineEntry`) | `constructor_waivers.yaml` |
| Services root modules | **85/85 at cap** | `application_services_root_ratchet.yaml` |

## Issue codes — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| ARCH-REF-00 | meta | #6817 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6817 |
| ARCH-REF-01 | P0 | #6820 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6820 |
| ARCH-REF-02 | P0 | #6825 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6825 |
| ARCH-REF-03 | P1 | #6824 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6824 |
| ARCH-REF-04 | P1 | #6818 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6818 |
| ARCH-REF-05 | P1 | #6822 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6822 |
| ARCH-REF-06 | P2 | #6819 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6819 |
| ARCH-REF-07 | P2 | #6821 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6821 |
| ARCH-REF-08 | P3 | #6823 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6823 |

Publish record: `reports/quality/architecture-refactoring-2026-07-28-issue-publish.json`

## Constraints

1. No technical-debt **budget growth**.
2. Domain I/O-free; DI only in composition.
3. Prefer extract helpers / collaborator bags over layer exceptions.
4. Do not reopen closed ARCH-QA / ARCH-RES / ARCH-CONT issues; this is a **new residual wave**.
5. Layer violations must remain **0**.
