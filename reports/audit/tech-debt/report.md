# Tech-debt cycle report

run_id: `20260825T134536Z-debt-cycle-d9ac42612b`  
prompt: `prompt.audit.cycle.tech-debt` v1.1.0  
MODE=full N=10 LANGUAGE=ru  
SCOPE: `src/bioetl/` `configs/quality/`  
SHA audited: `e57d2818691442c4bc8d7857eea3e39755bdc2a9` (`origin/main` at paydown)  
branch: `fix/audit-cycle-tech-debt-d9ac42612b`

## Gate

**WARN** — paydown validated on the feature branch (45/45 gates, audit pin ok). `origin/main` remains stale until merge (`ALLOW_MERGE=false`).

## surface_score

**2** (acceptable). Mapping: core debt mechanism works; release-gate drift was real and is paid down on the branch; remaining residuals are governed (constructor waiver 1, import-cycle allowlist 30, scorecard dead-code KPI 4 vs inventory 8 — pre-existing, budget not raised).

No P0. Score not capped at 1.

## Executive summary

1. On clean `origin/main` the tech-debt audit pin and live debt-governance gates were **PROVEN** stale/failing (`REQ-GOV-012`).
2. Issues: **#9646** (P2 re-pin), **#9647** (P1 artifact refresh).
3. Paydown: canonical `refresh_governance_artifacts` + remote-main baseline `--update` + registry/report re-pin. **No budget increase.**
4. After paydown: `validate-technical-debt-audit --json` → `ok: true`; `report-debt-governance-gates --check --changed-from-ref origin/main` → 0 fail.
5. Named `WORK_BRANCH=fix/audit-cycle-tech-debt` was occupied by a dirty worktree @ `27105f8536` and was **not** touched.

## Residual delta (touched families)

| Family | Before (origin/main @ e57d2818 committed) | After (worktree) | Trend |
| --- | --- | --- | --- |
| debt-governance fail_count | 1 (committed JSON) / 3 live `--check` | 0 | ↓ |
| generated_artifact_drift | stale scorecard+inventory+remote_main | 0 | ↓ |
| integral_score | 9.28 committed / live mismatch | 9.28 aligned | flat/aligned |
| source_module_count | inventory 2435 vs scorecard 2440 | 2435/2435 | aligned |
| unmeasured/uncovered | 0/0 | 0/0 | flat |
| constructor waivers | 1 | 1 | flat |
| exemptions | 0 | 0 | flat |
| control_plane hotspot files/loc | 143 / 16463 | 142 / 16452 | ↓ |
| dead-code inventory | 8 classified / 0 untriaged | 8 / 0 (restored; not raised) | flat |

## REJECTED_POLICY

- Raise `repo_wide_zero_import_candidate_count` max_count 4→7/8 to satisfy `test_debt_scorecard_declares_retirement_governance_kpis`.
- Hand-edit fingerprints.
- Touch occupied dirty `fix/audit-cycle-tech-debt` worktree.
- Regenerate `docs/02-architecture/generated/module-dependency-map.*` (#9334).

## Issues

- #9646 TECH-DEBT-001
- #9647 TECH-DEBT-002

Close only after merge to `origin/main`.
