# Tech-Debt residual issue pack (principal audit 2026-07-29)

**Status:** published  
**Wave code:** TD2  
**Date:** 2026-07-29  
**Baseline SHA:** `4b3469bf01` (local `main` at pack authoring)  
**Implementation epic:** [#7033](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7033)

**Audit basis:** Principal architecture / tech-debt audit (evidence-first, 2026-07-29)  
**Prior residual wave:** TD-R #6676–#6685 (2026-07-27 pack)  
**Policy:** debt budgets must not increase (`Agents.md`, `debt_scorecard.yaml`)

## Snapshot (evidence)

| Metric | Value | Source |
|---|---|---|
| Debt gates | **44 pass / 1 fail** | `reports/quality/debt-governance-gates.md` |
| Fail gate | `generated_artifact_drift` stale_artifact_count=1 | same |
| Integral score | **9.41** | `architecture-quality-scorecard.json` |
| Layer violations | 0 | scorecard + `.importlinter` |
| Transition/sunset/expired compat | 0/0/0 | `debt_scorecard.yaml` + census |
| Twin pairs | 0 | census |
| Retained public entrypoints / facades | 12 / 4 | census + facade inventory |
| Uncovered / unmeasured modules | 0 / 0 of 2311 | module-coverage-inventory |
| Hotspot budget warnings | 0 (control_plane **at** fan_in budget) | hotspot-family-baseline |
| Zero-ref supporting scripts | 15 (limit 17) | debt gates |
| Product basedpyright errors | 0 | basedpyright-error-snapshot |
| Suppression files | 220 | basedpyright-suppression-inventory |
| Domain I/O violations | 0 | domain-io-taint-inventory |

## Parallel programs (do **not** re-open as TD2 children)

| Program | Epic | Scope |
|---|---|---|
| PD5 typing | #6994 | suppressions / workspace diagnostics |
| TEST-SYS | #7020 | test cost/quality / partial floors |
| SNR-R Sonar | #6938 | static analysis residual |
| ARCH-CR2 | #7005 | CodeRabbit architecture residual |
| RH5 root | #7015 closed | root allowlist 37≡37 |

TD2 tracks **debt-governance residual** not already owned by those epics.

## Issue matrix

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| TD2-00 | [#7033](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7033) | meta | Tech-debt residual after 2026-07-29 principal audit |
| TD2-01 | [#7034](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7034) | P0 | Clear `generated_artifact_drift` (regenerate stale quality JSON) |
| TD2-02 | [#7035](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7035) | P1 | Control-plane hotspot fan-in headroom (at budget 3/3) |
| TD2-03 | [#7036](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7036) | P1 | Application-core hotspot fan-in headroom (near budget 8/10) |
| TD2-04 | [#7037](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7037) | P1 | Internal compatibility shim inventory review (3 shims) |
| TD2-05 | [#7038](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7038) | P2 | Refresh debt audit + compat census snapshots / registry pin |
| TD2-06 | [#7039](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7039) | P2 | Ratchet zero-reference supporting scripts (15 → ≤12, target 0) |
| TD2-07 | [#7040](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7040) | P3 | Quarterly sanctioned public API review (12 entrypoints + 4 facades) |
| TD2-08 | [#7041](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7041) | P3 | Tracking — coordinate PD5 / TEST-SYS / SNR-R without budget growth |

## Delivery order

1. **PR-0** TD2-01 artifact drift (unblocks release_gate)  
2. **PR-1a/b** TD2-02 / TD2-03 hotspot headroom  
3. **PR-1c** TD2-04 shim review  
4. **PR-2** TD2-05 / TD2-06 process ratchets  
5. **Track** TD2-07 / TD2-08  

## Exit (epic)

- [ ] Debt-governance gates **45/45** pass (`generated_artifact_drift=0`)  
- [ ] Hotspot families not saturated (control_plane fan_in headroom)  
- [ ] Shim inventory reviewed with importer proof or removal  
- [ ] Audit registry / census dates current after regen  
- [ ] Scripts zero-ref max_count ratcheted ≤ current after cleanup  
- [ ] No debt budget increases  

## Normative sources

- `configs/quality/debt_scorecard.yaml`  
- `configs/quality/technical_debt_audit_registry.yaml`  
- `configs/quality/compatibility_facade_inventory.yaml`  
- `configs/quality/internal_compatibility_shim_inventory.yaml`  
- `reports/quality/debt-governance-gates.json`  
- `reports/quality/architecture-quality-scorecard.json`  
- `reports/quality/compatibility-importer-census.json`  
- `reports/quality/hotspot-family-baseline.json`  
- `reports/quality/dead-code-inventory.json`  
- `.importlinter`  

## Publish record

- `reports/quality/td2-2026-07-29-issue-publish.json`
