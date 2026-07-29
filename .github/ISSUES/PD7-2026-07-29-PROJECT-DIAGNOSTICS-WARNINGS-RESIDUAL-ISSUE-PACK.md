# PD7 issue pack — ~15.9k product warnings + suppressions residual

Created: 2026-07-29T06:50:46Z

## Epic
- #7078 — chore(types): PD7 Project Diagnostics — ~15.9k product warnings + suppressions residual
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7078

## Children
- **PD7-0** #7079: chore(types): PD7-0 explain ~15.9k IDE diagnostics as product warnings + refresh workspace floors
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7079
- **PD7-1** #7080: fix(types): PD7-1 product Host Protocol suppressions 195 → ≤150 (no host-default Any)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7080
- **PD7-2** #7081: fix(types): PD7-2 product InvalidCast / ArgumentType / ImportCycles residual
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7081
- **PD7-3** #7082: fix(types): PD7-3 non-schema Port/application Any/Unknown warning burn
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7082
- **PD7-4** #7083: fix(types): PD7-4 schema generator implementation for silver_*/gold warning megatrees
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7083
- **PD7-5** #7084: fix(types): PD7-5 PrivateUsage + unannotated host attribute burn-down
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7084
- **PD7-6** #7085: chore(types): PD7-6 workspace residual after regen (scripts / memory / contract tails)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7085
- **PD7-7** #7086: chore(types): PD7-7 residual warnings pilots (ImplicitOverride / string concat / unused)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7086
- **PD7-8** #7087: chore(types): PD7-8 campaign closeout + ledger hygiene
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7087

## Baseline
- IDE reported approx: 15890
- product errors: 0
- product warnings: ~15774
- Any/Unknown family: ~10790
- schema-ish warnings: ~3351
- suppression files: ~195
- workspace errors (stale export): ~2174
- plan: `reports/quality/PROJECT_DIAGNOSTICS_15890_AUDIT_AND_PLAN_2026-07-29.md`

## Sequencing
1. PD7-0 first
2. PD7-1 and PD7-2 suppressions structural
3. PD7-3 non-schema Any/Unknown parallel
4. PD7-4 schema generator implementation before silver bulk
5. PD7-5 private/unannotated attrs
6. PD7-6 workspace residual after regen
7. PD7-7 pilots optional
8. PD7-8 closeout last
