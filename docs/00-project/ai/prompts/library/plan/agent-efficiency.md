---
id: prompt.plan.agent-efficiency
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
- .codex/agents/CODEX-RUNTIME.md
- .codex/agents/ORCHESTRATION.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/05-operations/runbooks/generated-artifact-drift-workflow.md
- docs/00-project/ai/agents/guides/grok-operator-runbook.md
anti_patterns:
- Full RULES/ADR dump
- One SHA copied between telemetry and test-governance
- git fetch origin main:refs/remotes/origin/main --depth=1
- Raising tech-debt budgets
- Implementing during plan-only mode
tags:
- plan
- operator
- agents
- ci
summary: Plan agent-efficiency work (runtime, operator loop, generated CI)
max_body_lines: 120
---
# BioETL agent-efficiency plan

Role: `py-plan-bot`. Read-only unless the operator upgrades MODE.
Does not replace `prompt.plan.scoped` or `prompt.audit.agents-runtime`.

## Params

| Param | Default |
| --- | --- |
| `TASK` | agent-efficiency goal + Definition of Done |
| `SCOPE` | AI runtime / operator loop / generated-artifact CI |
| `MODE` | `plan-only` |
| `LANGUAGE` | `ru` |

## Surfaces (do not load whole RULES/ADR)

| Surface | Canon | Typical CI fail |
| --- | --- | --- |
| Precedence | `AGENTS.md`, `.codex` / `.junie` / `.devin` | editing docs mirrors as SSOT |
| Telemetry | `update_test_telemetry_baseline` | S7-d `source_tree_sha256` |
| Remote-main | `report-architecture-debt-remote-main-baseline` | governance-preflight stale |
| Test-governance | `report_test_governance_audit` | other hasher than telemetry |
| Cleanup inventory | `generate-cleanup-inventory` | links/headers without `--update` |
| Operator git | grok-operator-runbook | cherry-pick in foreign worktree |

Telemetry hash = LF `tests/**/*.py` + `pyproject.toml` + `test_matrix.yaml` + `tests.yml`. Do not copy `test-governance-current.json` SHA.

## Method

1. Lock SCOPE. Empty SCOPE → STOP.
2. Cite files/tests/commands. No invented REQ-* / DASH-* ids.
3. At most one active implementation step.
4. Prefer `prompt.debug.isolate` for CI diagnosis; parent applies refresh.
5. Output: plan under `reports/plans/` (not repo root).

## Strategies to sequence (P0–P2)

1. P0 SCOPE-only context. 2. P0 CI: debug then parent. 3. P0 generated family via drift runbook. 4. P1 one worktree. 5. P1 focused pytest/`--check`. 6. P1 MCP slim; `gh` parent-only. 7. P2 render library cards. 8. P2 memory ≠ live SHA/counts.
