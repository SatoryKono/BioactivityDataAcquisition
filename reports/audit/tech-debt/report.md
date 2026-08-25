# Tech-debt cycle report

run_id: `20260825T1419Z-debt-cycle-cdff5b63`  
prompt: `prompt.audit.tech-debt-cycle` v1.0.0 + domain `prompt.audit.tech-debt` v1.2.0  
MODE=full N=10 LANGUAGE=ru AUDIT_MODE=full  
SCOPE: `src/bioetl/` `configs/quality/`  
SHA audited: `cdff5b63e6f31bee5c31ae1d3c19a4fe7045481b` (`origin/main`)  
branch: `fix/audit-tech-debt-cycle-cdff5b63`

## Gate

**WARN** — paydown validated on the feature branch (45/45 live gates, audit pin ok). `origin/main` remains stale until merge (`ALLOW_MERGE=false`).

## surface_score

**2** (acceptable). Mapping: core debt mechanism works; release-gate drift was real and is paid down on the branch; remaining residuals are governed (constructor waiver 1, import-cycle allowlist 30, wrapper_contract_drift 1 already #9643, control_plane at_budget already #9618).

No P0 in this SCOPE. Score not capped at 1.

## Executive summary

1. On clean `origin/main@cdff5b63e6` the tech-debt audit pin was **PROVEN** stale (`REQ-GOV-012`) and live `--check` failed on `generated_artifact_drift` (`remote_main_baseline` only).
2. Issues reused: **#9646** (P2 re-pin), **#9647** (P1 artifact refresh). No new issues (same root cause; SHA moved past PR #9648 / e57d281869).
3. Paydown: canonical remote-main baseline `--update` + gates `--update` + registry/report re-pin. **No budget increase.**
4. After paydown: `validate-technical-debt-audit --json` → `ok: true`; `report-debt-governance-gates --check --changed-from-ref origin/main` → 0 fail.
5. Named `WORK_BRANCH=fix/audit-tech-debt-cycle` was occupied and was **not** touched.

## Residual delta (touched surfaces)

| Family | Before (origin/main @ cdff5b63e6 committed) | After (worktree) | Trend |
| --- | --- | --- | --- |
| live `--check` fail_count | 1 (`generated_artifact_drift`) | 0 | ↓ |
| remote_main_sha | e57d281869 | cdff5b63e6 | aligned |
| audit pin SHA | 9f57924063 | cdff5b63e6 | aligned |
| integral_score (report vs live) | 9.41 vs 9.28 | 9.28 aligned | aligned |
| source_module_count (report vs live) | 2450 vs 2435 | 2435 aligned | aligned |
| unmeasured/uncovered | 0/0 | 0/0 | flat |
| constructor waivers | 1 | 1 | flat |
| exemptions | 0 | 0 | flat |
| scorecard budgets | unchanged | unchanged | flat |

## REJECTED_POLICY

- Raise `repo_wide_zero_import_candidate_count` max_count to satisfy `test_debt_scorecard_declares_retirement_governance_kpis`.
- Hand-edit fingerprints.
- Touch occupied dirty/locked `fix/audit-tech-debt-cycle` worktree.
- Open duplicate issues for the new SHA.

## Issues

- #9646 TECH-DEBT-001
- #9647 TECH-DEBT-002

Close only after merge to `origin/main`.
