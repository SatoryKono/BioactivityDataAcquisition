---
id: prompt.tests.fix-retest
version: 2.3.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE =  tests/
- MAX_ITERATIONS = 5
- LANGUAGE = ru
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- scripts/engineering/dev/run_pytest.sh
- scripts/engineering/dev/run_pytest.ps1
anti_patterns:
- Expanding test scope without justification
- Silent infra blockers
- Infinite fix loops without iteration cap
- Closing an issue before the same-scope tests are green
- Skipping the plan audit
- Shrinking a debt budget by deleting a live config field or a still-imported module
tags:
- tests
- debug
- operator
summary: Plan, audit, implement, then run → fix → retest and close the issue
---
# Test fix / re-test loop

For each task, in order: plan, audit that plan, update the GitHub issue,
implement, run → fix → retest until green, close the issue, then the next task.
Do not start the next task while the current one is red or `BLOCKED`.

Step 0: if this is a CI/generated-artifact failure, require a
`prompt.debug.isolate` diagnosis first (family + refresh command). Then apply
the pin/refresh and re-run **the same focused scope** — not full
`architecture-fast`.

## Per task

1. **Plan.** Outcome, files, non-goals, debt effect (budgets only stay or
   fall), tests, and rollback. One task in progress.
2. **Audit the plan** against the checkout. Fix plan errors before any product
   edit. A shrink that deletes a live field or a still-imported module is a
   plan error.
3. **Update the GitHub issue** with the audited plan, in Russian. Do not close
   it yet.
4. **Implement** only the audited plan. Never commit on `main`. If the gate
   already enforces the acceptance on `origin/main`, do not invent a shrink;
   record `VERIFIED_ALREADY_RESOLVED` with path, SHA, and command.
5. **Tests** — section 1–4 below, same scope, at most `MAX_ITERATIONS`.
6. **Close** the issue only after acceptance is met and that scope is green.
   Then take the next task.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | minimal relevant test path/node ids |
| `MAX_ITERATIONS` | `5` |
| `LANGUAGE` | `ru` |

## 1) Run tests (targeted, minimal)

- Known failure → only affected tests
- No known failure → minimal relevant scope for the task
- Commands:
  - Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <scope> --maxfail=1 -q`
  - Windows: `.\scripts\engineering\dev\run_pytest.ps1 <scope> --maxfail=1 -q`
  - fallback: `python -m pytest <scope> -q`
- Record each run: command, scope, status, fail count, first errors

## 2) If green — stop

- Exit code 0 → record result and finish
- Report: what was tested, status, scope, command

## 3) If red — fix and return to step 1

- Root-cause the highest-priority failure
- Minimal sufficient fix (no needless scope expansion)
- Re-run **the same scope**
- Repeat until green, non-actionable blocker documented, or `MAX_ITERATIONS`

## 4) Stop conditions

Finish only when all tests green **or** iteration limit with blockers and next
steps. Always report: iterations, errors fixed, state
(`green` / `partially green` / `blocked`), next step for external blockers.
