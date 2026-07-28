# PD4 issue pack — Host Protocol / residual suppression burn-down

Created: 2026-07-28T17:27:26Z

## Epic
- #6972 — chore(types): PD4 structural Host Protocol burn-down (post zero-errors)
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6972

## Children
- **PD4-0** #6973: chore(types): PD4-0 KPI lock — product errors=0 + suppression inventory floor
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6973
- **PD4-1** #6974: fix(types): PD4-1 W1-A composite/runner Host Protocols (drop uninit/attr flags)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6974
- **PD4-2** #6975: fix(types): PD4-2 W1-B core/services/observability Host Protocols
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6975
- **PD4-3** #6976: fix(types): PD4-3 W1-C adapters/storage Host Protocols
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6976
- **PD4-4** #6977: fix(types): PD4-4 W2 InvalidCast → Protocol self / free helpers
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6977
- **PD4-5** #6978: refactor(types): PD4-5 W3 import cycles break + allowlist shrink
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6978
- **PD4-6** #6979: fix(types): PD4-6 W4 product ArgumentType boundaries without flags
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6979
- **PD4-7** #6980: fix(types): PD4-7 W5 incompatible override tail
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6980
- **PD4-8** #6981: chore(types): PD4-8 W6 warnings pilot (implicit override / Port Any sample)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6981

## Baseline
- product errors: 0
- product warnings: ~15378
- suppression files: 239
- suppression rules: 296
- entity tests errors: 0
- plan: `reports/quality/PROJECT_DIAGNOSTICS_AUDIT_AND_PLAN_2026-07-28.md`

## Sequencing
1. PD4-0 first
2. PD4-1…PD4-3 parallel
3. PD4-4 after hosts
4. PD4-5…PD4-7 next
5. PD4-8 optional
