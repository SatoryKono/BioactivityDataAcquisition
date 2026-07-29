# PD3 issue pack — structural suppression debt

Governed diagnostic reporters:

- `scripts/engineering/qa/report_basedpyright_error_snapshot.py`
- `scripts/engineering/qa/report_basedpyright_suppression_inventory.py`
- `scripts/engineering/qa/report_basedpyright_tests_snapshot.py`

Created: 2026-07-28T16:31:16Z

## Epic
- #6961 — chore(types): PD3 structural burn-down of basedpyright suppression debt
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6961

## Children
- **PD3-0** #6962: chore(types): PD3-0 suppression governance + product snapshot guard
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6962
- **PD3-1** #6963: fix(types): PD3-1 S1 adapter mixin Host Protocols (drop uninit/attr flags)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6963
- **PD3-2** #6964: fix(types): PD3-2 S1 storage mixin Host Protocols (bronze/silver/gold)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6964
- **PD3-3** #6965: fix(types): PD3-3 S1 application Host Protocols (core/composite/services)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6965
- **PD3-4** #6966: fix(types): PD3-4 S2 InvalidCast → Protocol self / free helpers
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6966
- **PD3-5** #6967: refactor(types): PD3-5 S3 import cycles break + allowlist shrink
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6967
- **PD3-6** #6968: fix(types): PD3-6 S4 product ArgumentType boundaries without flags
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6968
- **PD3-7** #6969: test(types): PD3-7 S5 entity unit-test residual (20 → 0)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6969
- **PD3-8** #6970: chore(types): PD3-8 S6 warnings pilot (implicit override + Port Any sample)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6970
- **PD3-9** #6971: chore(types): PD3-9 suppression inventory ratchet + burn-down ledger
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6971

## Baseline
- product errors: 0
- product warnings: ~14967
- entity tests errors: 20
- suppression files: ~309
- audit: `reports/quality/PROJECT_DIAGNOSTICS_AUDIT_2026-07-28.md`
