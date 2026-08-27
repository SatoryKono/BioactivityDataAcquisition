# Improved cyclic tech-debt audit — iteration 1

Cycle-run: `20260827T0815Z-debt-new-1a46a2e394`

| Field | Value |
| --- | --- |
| `prompt_id` | `prompt.audit.project.new.tech-debt` |
| `MODE` | `full` |
| `ALLOW_*` | all **false** |
| `WORK_BRANCH` | `fix/tech-debt-cycle-new-1a46a2e394` |
| `origin/main` | `1a46a2e394` (#9741 already merged) |
| `surface_score` | **2** |
| `debt_outcome` | **improved** |

## Register (A)

- `# TODO|FIXME|HACK` в `src/bioetl`: нет (ложные `ADR-XXX` / `CVCL_XXXX`).
- Gates committed: 45/45, но live `--check` ловил stale `remote_main_baseline` (pin `2caccbe446` vs `1a46a2e394`) и drift `adr_enforcement_matrix`.
- Leftover cap: `supporting_scripts_governance.zero_reference_supporting_script_count` max **15** при live **0**.
- Freeze at cap: lazy 97/97, private 15/15, config 27/419, control_plane fan-in 2/2, runtime_builders 3/3, assertless 87.
- Fan-in slack from previous cycle already on main (10→7, 5→3).

## Risk (B)

| ID | P | Blast | Paydown |
| --- | --- | --- | --- |
| AUD-TD-N-001 | P2 | gates `generated_artifact_drift` fail-closed | re-pin remote-main + ADR matrix via SSOT |
| AUD-TD-N-002 | P2 | leftover max 15 hides zero-budget honesty | ratchet 15→0 |
| freeze cluster | P2 | cost-of-change | hold; live drop first |

P0/P1 security/data: **нет**.

## Issues (C)

`ALLOW_ISSUE_WRITE=false` → payloads only, **0 created**. `new_issues_1=0`, `open_cycle_issues=0`.

## Paydown (D)

1. `max_count` 15→0 for zero-reference supporting scripts (live 0).
2. `report-architecture-debt-remote-main-baseline --update` → SHA `1a46a2e394`.
3. `report-adr-enforcement-matrix --update` (ADR-010 142→145, ADR-040 30→33 evidence rows; still enforced, no new gaps).
4. gates `--update/--check --changed-from-ref origin/main` → 45/45, `budget_increase_count=0`.

## Validate (E)

```text
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
# exit 0
pytest tests/architecture/test_tech_debt_issues_5956_5961_closeout.py \
  tests/architecture/test_tech_debt_issues_5564_5603_closeout.py \
  tests/architecture/test_quality_debt_scorecard.py
# 0 fail (2 skip: Windows inventory walk; retired warn_until)
```

## Residual delta

| Metric | Before | After | Trend |
| --- | --- | --- | --- |
| supporting_scripts max_count | 15 | **0** | ↓ |
| gates supporting_scripts limit | 15 | **0** | ↓ |
| remote_main_sha pin | `2caccbe446` | `1a46a2e394` | aligned |
| generated_artifact_drift | live fail | **0** | ↓ |
| lazy/private/config/assertless | at cap | at cap | hold |

## REJECTED_POLICY

- Raise any cap/exemption/floor
- `application_core` 7→6 (`#6032` live < budget)
- bootstrap fan-in 3→2 (`#6034`)
- factories `files_ge_250_loc` 2→0 (`#5648` `== 2` pin)
- lazy 97 / private 15 without live shrink

## Early-stop

Iteration 2–10 skipped: `new_issues_i==0` and `open_cycle_issues==0`. Empty form cycles forbidden.
