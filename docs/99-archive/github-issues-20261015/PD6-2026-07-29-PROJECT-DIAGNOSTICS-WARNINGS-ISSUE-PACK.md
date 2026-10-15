# PD6 issue pack — ~15k product warnings + residual suppressions/workspace

Created: 2026-07-29T06:05:56Z  
**Status: CLOSED 2026-07-29** — closeout `reports/quality/pd6-campaign-closeout-2026-07-29.md`  
Epic #7042 and children #7043–#7052 closed on GitHub.

## Epic
- #7042 — chore(types): PD6 Project Diagnostics — ~15k product warnings + residual suppressions/workspace
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7042

## Children
- **PD6-0** #7043: chore(types): PD6-0 explain ~15k IDE diagnostics as product warnings + lock baselines
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7043
- **PD6-1** #7044: fix(types): PD6-1 product Host Protocol suppressions 220 → ≤150 files
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7044
- **PD6-2** #7045: fix(types): PD6-2 product InvalidCast / ArgumentType / ImportCycles residual
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7045
- **PD6-3** #7046: fix(types): PD6-3 Port/application boundary Any/Unknown warning burn (non-schema)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7046
- **PD6-4** #7047: fix(types): PD6-4 schema generator strategy for silver_*/gold contract warning megatrees
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7047
- **PD6-5** #7048: test(types): PD6-5 residual tests burn-down (repo_backed, neo4j support, interfaces/domain)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7048
- **PD6-6** #7049: chore(types): PD6-6 src/memory typing pass or hardened exclude policy
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7049
- **PD6-7** #7050: chore(types): PD6-7 scripts engineering entrypoints advisory typing
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7050
- **PD6-8** #7051: chore(types): PD6-8 product warnings pilots (ImplicitOverride / unused / string concat)
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7051
- **PD6-9** #7052: chore(types): PD6-9 warning snapshot tooling + docs/IDE hygiene closeout
  https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7052

## Baseline
- IDE reported approx: 15062
- product errors: 0
- product warnings: ~15523
- workspace errors live: ~2174
- tests residual errors: ~907
- suppression files: ~220
- plan: `reports/quality/PROJECT_DIAGNOSTICS_15062_AUDIT_AND_PLAN_2026-07-29.md`

## Sequencing
1. PD6-0 first
2. PD6-1 and PD6-2 suppressions structural
3. PD6-3 non-schema warnings parallel
4. PD6-4 schema generator before silver bulk
5. PD6-5/6/7 residual workspace
6. PD6-8 pilots optional
7. PD6-9 tooling + closeout last
