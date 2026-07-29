# PD5 issue pack — workspace ~10k diagnostics + product suppression debt

Created: 2026-07-29T05:19:20Z

## Epic
- #6994 — chore(types): PD5 Project Diagnostics — workspace ~10k tests + product suppression debt
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6994

## Children
- **PD5-0** #6995: chore(types): PD5-0 explain ~12k IDE diagnostics vs product zero + refresh snapshots
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6995
- **PD5-1** #6996: test(types): PD5-1 shared test doubles library (RunID, Protocol stubs, settings)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6996
- **PD5-2** #6997: test(types): PD5-2 tests/unit/application diagnostics burn-down
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6997
- **PD5-3** #6998: test(types): PD5-3 tests/unit/composition diagnostics burn-down
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6998
- **PD5-4** #6999: test(types): PD5-4 tests/unit/infrastructure diagnostics burn-down
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6999
- **PD5-5** #7000: test(types): PD5-5 fixture TypedDict / index / missing-type-args pass
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7000
- **PD5-6** #7001: fix(types): PD5-6 product Host Protocol suppressions → ≤150 files
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7001
- **PD5-7** #7002: fix(types): PD5-7 product InvalidCast / cycles / ArgumentType residual
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7002
- **PD5-8** #7003: chore(types): PD5-8 scripts + src/memory + tools advisory typing
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7003
- **PD5-9** #7004: chore(types): PD5-9 product warnings pilot (non-blocking)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7004

## Baseline
- IDE reported approx: 12662
- workspace errors live: ~10005
- tests errors: ~8784
- product errors: 0
- product warnings: ~15512
- suppression files: ~228
- plan: `reports/quality/PROJECT_DIAGNOSTICS_12662_AUDIT_AND_PLAN_2026-07-28.md`

## Sequencing
1. PD5-0 first
2. PD5-1 then PD5-2…PD5-4
3. PD5-6 product suppressions parallel
4. PD5-5/7/8 next
5. PD5-9 optional
