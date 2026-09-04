---
id: prompt.plan.scoped
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- TASK
- SCOPE
- MODE
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
- fragments/orchestrator-guards.md
related_ssot:
- AGENTS.md
- .codex/agents/py-plan-bot.md
- docs/00-project/NORMATIVE_SOURCES.md
anti_patterns:
- Plan that silently raises debt budgets
- Implementing during plan-only mode
tags:
- plan
- operator
summary: Scoped implementation plan (py-plan-bot) — one active step
max_body_lines: 120
---
# BioETL scoped plan

Role: `py-plan-bot`. Read-only unless the operator upgrades MODE.

## Params

| Param | Default |
| --- | --- |
| `TASK` | goal + Definition of Done |
| `SCOPE` | paths / issues / theme |
| `MODE` | `plan-only` |
| `LANGUAGE` | `ru` |

## Method

1. Lock SCOPE. Empty SCOPE → STOP.
2. Cite files, tests, ADRs, configs. No invented REQ-* / DASH-* ids.
3. Sequence at most one active implementation step.
4. List exact verification commands. Do not raise debt budgets.
5. Output: plan markdown under `reports/plans/` (not repo root).
