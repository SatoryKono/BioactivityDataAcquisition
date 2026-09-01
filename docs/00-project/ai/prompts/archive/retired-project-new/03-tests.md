---
id: prompt.audit.project.new.tests
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - LANE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - MAX_FIXES_PER_CYCLE
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md
  - docs/00-project/ai/prompts/library/audit/tests-system.md
  - docs/00-project/ai/prompts/library/tests/test-cycle.md
  - configs/quality/test_matrix.yaml
  - reports/quality/test-governance-current.json
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Full-suite first feedback without LANE/SCOPE budget
  - Raising skip/xfail/debt budgets to greenwash
  - Retries as a flaky fix
  - Inventing a coverage target the project does not define
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Confusing MODE=full with LANE=full
tags: [audit, tests, cycle, quality, operator]
summary: Improved cyclic test-system audit plus bounded LANE retest, ALLOW_* true, early-stop
max_body_lines: 240
---

# Improved cyclic test-layer audit

Улучшает `prompt.audit.cycle.tests` и встраивает bounded run-loop из
`prompt.tests.cycle` (не путать: LANE=full ≠ MODE=full). Method:
`prompt.audit.tests-system`. Loop: `prompt.audit.orchestrator`.

Library defaults: **`ALLOW_*=true`**. Пустые циклы запрещены.
**УВЕЛИЧИВАТЬ skip/xfail/debt бюджеты ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `tests/ configs/quality/ pyproject.toml` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `LANE` | `unit` (`unit` \| `arch` \| `fast` \| `full`) |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_FIXES_PER_CYCLE` | `8` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/tests-cycle-new-<shortsha>` |

## Anchors

- Matrix: `configs/quality/test_matrix.yaml`
- Runners: `scripts/engineering/dev/run_pytest.ps1` / `.sh`
- Windows: only `.\.venv-win\Scripts\python.exe -m pytest …`
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA; toolchain. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-tests-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Lanes, markers, skip/xfail/quarantine, what actually blocks merge. |
| **B Risk gaps** | Critical paths → tests. Optional **bounded** LANE run for evidence — not full suite unless LANE=full. |
| **C Flaky** | Re-run suspected flaky N times; record outcomes. Retries ≠ fix. Skip needs owner/issue. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[tests][<REQ-id>][P#]`. |
| **E Fix** | Minimal diff. Cap `MAX_FIXES_PER_CYCLE`. No new skip/xfail as “fix”. |
| **F Retest** | Same LANE/SCOPE. Record delta. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1, без new failures, без skip-budget growth → STOP.

## Success

- Test-system findings with command evidence
- Retest same LANE/SCOPE after fixes
- No coverage-threshold invention
