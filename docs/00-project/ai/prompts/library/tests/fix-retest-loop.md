---
id: prompt.tests.fix-retest
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MAX_ITERATIONS, LANGUAGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - scripts/engineering/dev/run_pytest.sh
  - scripts/engineering/dev/run_pytest.ps1
anti_patterns:
  - Expanding test scope without justification
  - Silent infra blockers
  - Infinite fix loops without iteration cap
tags: [tests, debug, operator]
summary: Run → fix → retest until green or blocked
---

# Test fix / re-test loop

Debug and fix until tests are green via **run → fix → run**.

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
