# Improved cyclic docs audit — iteration 1

Cycle-run: `20260827T0846Z-docs-new-b9aa36efdd`

| Field | Value |
| --- | --- |
| `prompt_id` | `prompt.audit.project.new.docs` |
| `MODE` | `full` |
| `ALLOW_*` | all **false** (operator paste; library on `origin/main` currently defaults true) |
| `WORK_BRANCH` | `fix/docs-cycle-new-17ef2a3d25` |
| `origin/main` | `b9aa36efdd` |
| `content_surface_score` | **2** |
| `pipeline_surface_score` | **2** |
| `surface_score` | **2** |

## Content (A)

- README purpose and 22+composite config claim: **OK** (22 non-composite + 5 composite).
- RULES.md `Version: 6.1.11` is docs versioning, not `pyproject.toml` `6.1.0`.
- `# TODO|FIXME` operational holes: **нет** P0.
- Secret values in docs: **не найдены**.
- P1: POSIX-only `.venv` fallback vs Windows `.venv-win` (`AUD-DOC-002`) — paydown in worktree.
- P2: runbook cleanup-inventory submodule path (`AUD-DOC-001`) — paydown in worktree.

## Pipeline (B)

| Command | Exit | Note |
| --- | --- | --- |
| `python -m scripts.docs check-links --links --specs --configs` | 0 | broken relative links = 0 |
| `python -m scripts.docs check-drift --runtime-mirrors --freshness` | 0 | 0 errors / 0 warnings |
| `python -m scripts.docs check-kpi` | 0 | monitoring; outside-nav 127 / hard 135; orphans 0 |
| `python -m scripts.docs generate-cleanup-inventory --check` | 0 | after `--update` for doc + inventory drift |
| `python -m scripts.docs verify --skip-build` | **1** | `check-docstrings` functions 88.7% < 90% (missing=795) |
| `python -m scripts.docs verify` (MkDocs `--strict`) | skipped | blocked by docstring step |

Exit 0 ≠ semantics: link checker does not prove Windows venv instructions.

`tests.yml` docs-runtime producer captures `verify --skip-build` then `exit 0` (fail-open for that job).

## Plan (C)

Restore-SSOT-link for 001/002. Hold 003 (do not raise docstring 90%). Hold 004 (do not raise KPI hard limit).

## Issues (D)

`ALLOW_ISSUE_WRITE=false` → **0 created**. `new_issues_1=0`, `open_cycle_issues=0`.

## Paydown (E)

1. Runbook → `python -m scripts.docs generate-cleanup-inventory --check|--update`.
2. `docs-verification.md` / `quick-start.md` → `.venv-win` + `getting-started.md`.
3. `python -m scripts.docs generate-cleanup-inventory --update` (counts 3513→3552; includes `new2` pack already on main).

## Validate (F)

- Re-sampled edited relative links (`getting-started.md`).
- `check-links` exit 0 after edits.
- Inventory `--check` synchronized after `--update`.
- Close skipped (`ALLOW_CLOSE=false`). Not on `origin/main`.

## Early-stop

STOP after iteration 1: `new_issues_i==0` ∧ `open_cycle_issues==0`. Cycles 2–10 not invented.
