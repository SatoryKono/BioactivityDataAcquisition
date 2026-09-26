# Architecture Residual Issue Pack — 2026-07-27 (post ARCH-QA)

**Audit basis:** Independent architecture quality review after ARCH-QA-00…08 closeout.
**Independent integral:** **9.02** · committed scorecard **9.11**
**Prior closed wave:** ARCH-QA-00…08 (#6740–#6748)

## Snapshot (evidence)

| Metric | Value | Source |
|---|---|---|
| Layer violations | 0 | `module-dependency-map.json` |
| Debt gates | 45 pass / 0 fail | `debt-governance-gates.json` |
| application_core files_ge_250 | **5/5 at_budget** | `hotspot-family-baseline.json` |
| factories fan-in | **3/3 at_budget** | same |
| runtime_builders fan-in | 4/5 near | same |
| control_plane files_ge_250 | 12/16 | same |
| Partial modules | **816** | `module-coverage-inventory.json` |
| Constructor waivers | **3** | `constructor_waivers.yaml` |
| Uncovered / unmeasured | 0 / 0 | coverage inventory |

## Issue codes — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| ARCH-RES-00 | meta | #6749 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6749 |
| ARCH-RES-01 | P1 | #6753 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6753 |
| ARCH-RES-02 | P1 | #6750 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6750 |
| ARCH-RES-03 | P1 | #6751 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6751 |
| ARCH-RES-04 | P2 | #6752 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6752 |
| ARCH-RES-05 | P2 | #6754 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6754 |
| ARCH-RES-06 | P3 | #6755 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6755 |

Publish record: `reports/quality/architecture-residual-2026-07-27-issue-publish.json`

## Constraints

1. No debt budget growth.
2. Domain I/O-free; DI only in composition.
3. Prefer extract helpers / collaborator bags over layer exceptions.
4. Do not reopen closed ARCH-QA issues; this is a residual ownership wave.
