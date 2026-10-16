# Architecture Continuation Issue Pack — 2026-07-28

**Audit basis:** Independent architecture quality review (2026-07-28).
**Independent integral:** **9.04** · committed scorecard **9.11**
**Prior closed waves:** ARCH-QA (#6740–#6748), ARCH-RES (#6749–#6755)

## Snapshot (evidence)

| Metric | Value | Source |
|---|---|---|
| Layer violations | 0 | `module-dependency-map.json` |
| Debt gates | 45 pass / 0 fail | `debt-governance-gates.json` |
| application_core files_ge_250 | **5/5 at_budget** | `hotspot-family-baseline.json` |
| families_at_budget | `["application_core"]` | `architecture-quality-scorecard.json` |
| factories fan-in | 2/3 (headroom) | hotspot baseline |
| control_plane files_ge_250 | 11/16 | hotspot baseline |
| runtime_builders fan-in | 4/5 near | hotspot baseline |
| Partial modules | **815** | `module-coverage-inventory.json` |
| Constructor waivers | **2** | `constructor_waivers.yaml` |
| Services root modules | **86/86** | `application_services_root_ratchet.yaml` |

## Issue codes — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| ARCH-CONT-00 | meta | #6757 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6757 |
| ARCH-CONT-01 | P1 | #6763 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6763 |
| ARCH-CONT-02 | P1 | #6764 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6764 |
| ARCH-CONT-03 | P1 | #6758 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6758 |
| ARCH-CONT-04 | P2 | #6760 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6760 |
| ARCH-CONT-05 | P2 | #6759 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6759 |
| ARCH-CONT-06 | P2 | #6762 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6762 |
| ARCH-CONT-07 | P3 | #6761 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6761 |

Publish record: `reports/quality/architecture-continuation-2026-07-28-issue-publish.json`

## Constraints

1. No debt budget growth.
2. Domain I/O-free; DI only in composition.
3. Prefer extract helpers / collaborator bags over layer exceptions.
4. Do not reopen closed ARCH-QA/ARCH-RES issues; this is a continuation wave.
