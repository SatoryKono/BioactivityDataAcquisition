# PD2 issue pack (post-PD Project Diagnostics)

Created: 2026-07-28T16:03:19Z

## Epic
- #6949 — chore(types): Project Diagnostics burn-down post-PD residual (basedpyright)
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6949

## Children
- **PD2-0** #6950: chore(types): dual basedpyright baseline product vs tests (post-PD)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6950
- **PD2-1** #6951: fix(types): W1 adapter mixin host protocols (basedpyright uninit/attr)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6951
- **PD2-2** #6952: fix(types): W1 storage mixin host protocols (bronze/silver/gold)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6952
- **PD2-3** #6953: fix(types): W1 application mixin hosts (core/composite/services/observability)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6953
- **PD2-4** #6954: fix(types): W1 domain aggregates mixin host typing
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6954
- **PD2-5** #6955: fix(types): W2 invalid cast cleanup + host Protocol completeness
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6955
- **PD2-6** #6956: fix(types): W3 product reportArgumentType clusters
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6956
- **PD2-7** #6957: fix(types): W4 overrides, constants, optional/call tail
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6957
- **PD2-8** #6958: refactor(types): W5 import cycles break or allowlist shrink
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6958
- **PD2-9** #6959: test(types): W6 entity unit-test fixture typing (~5k basedpyright errors)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6959
- **PD2-10** #6960: chore(types): W7 remaining tests + scripts basedpyright advisory backlog
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6960

## Baseline
- product: 989 errors
- workspace: 16275 errors
- entity tests: 5181 errors
- plan: `reports/quality/PROJECT_DIAGNOSTICS_REMEDIATION_PLAN_2026-07-28.md`

## Sequencing
1. PD2-0 first
2. PD2-1…PD2-4 parallelizable
3. PD2-5 after hosts
4. PD2-9 anytime (IDE ROI)
5. PD2-6…PD2-8 after W1
6. PD2-10 continuous
