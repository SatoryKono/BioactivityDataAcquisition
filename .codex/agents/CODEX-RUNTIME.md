# CODEX-RUNTIME.md — Runtime Map For BioETL Agents

## Purpose

This file adapts BioETL's logical `py-*` agent profiles to the actual Codex runtime
available in this repository.

## Required Context

Before invoking a logical profile:

- use `AGENTS.md` as the root precedence contract
- read `docs/00-project/NORMATIVE_SOURCES.md` for the normative stack index
- read `docs/00-project/RULES.md` and `docs/01-requirements/REQUIREMENTS.md`
- use accepted ADRs in `docs/02-architecture/decisions/` for decision-specific rules
- read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- read `docs/00-project/ai/memory/agent-memory.md`
- read the matching `docs/00-project/ai/memory/memory-py-*.md` sheet when one
  exists for the selected logical profile
- for write-capable work, follow
  `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.
- Switch away from Russian only when the user explicitly requests another
  language.

`docs/00-project/ai/**` remains a mirror/guidance layer and must not override
runtime behavior defined in `.codex/**`.

Generic imported profiles still inherit BioETL guardrails from `AGENTS.md`,
`MEMORY_USAGE.md`, and the Local-Only runtime constraints even when they are not
fully BioETL-specific.

## Dashboard Skill Routing

- Use `.codex/skills/grafana-dashboard-render/` when the task is to render,
  preflight-check, or collect screenshot/live-audit evidence for shipped
  Grafana dashboards.
- Use `.codex/skills/grafana-dashboard-extension/` when the task is to change
  dashboard JSON, panel queries, navigation, variables, or operator-facing UX.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes `scorecard budgets`, exemption limits, hotspot thresholds,
  hotspot family caps, and any equivalent budget/threshold surface.
- If a task hits a limit, reduce scope, decompose the change, or escalate; do
  not raise the limit.

## Key Rule

`py-*` names in `.codex/agents/` are **logical project profiles**, not native
`spawn_agent()` enum values.

In this Codex environment, use:

- `default` for orchestration, audit, planning, review, and documentation analysis
- `explorer` for narrow read-only codebase questions
- `worker` for isolated implementation work with an explicit write scope

## Invocation Pattern

Use the native agent type plus a prompt that points to the BioETL profile file.

Example:

```text
spawn_agent(
  agent_type="default",
  message="Follow .codex/agents/py-audit-bot.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/."
)
```

## Recommended Mapping

| Logical profile            | Preferred Codex agent type | Notes                                                                                                      |
| -------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `py-audit-bot`             | `default`                  | Read-only audit/review work                                                                                |
| `py-architecture-debt-bot` | `default`                  | Debt-reduction orchestration surface; may own `src/`/`tests/` implementation while delegating configs/docs |
| `py-plan-bot`              | `default`                  | Planning and decomposition                                                                                 |
| `py-test-bot`              | `default` or `worker`      | `worker` only when editing tests                                                                           |
| `py-config-bot`            | `worker`                   | Owns `configs/` write scope                                                                                |
| `py-debug-bot`             | `worker`                   | Owns isolated fix scope in `src/` or `tests/`                                                              |
| `py-doc-bot`               | `worker`                   | Owns `docs/` / docstring edits                                                                             |
| `py-test-swarm`            | `default`                  | L1 orchestration, delegates further                                                                        |
| `py-review-orchestrator`   | `default`                  | L1 review orchestration                                                                                    |

Repo-wide documentation audits should use the `documentation-audit` /
`documentation-cascade-audit` skill surfaces instead of the retired
documentation-only logical profile.

## Ownership Rules

- Main orchestrator keeps ownership of `src/bioetl/` unless there is a clear,
  non-overlapping parallelization opportunity.
- `configs/` changes should be delegated only to the logical `py-config-bot`
  profile.
- When using `worker`, always state the owned files or directories explicitly.
- Do not ask child agents to revert unrelated user changes.

## Output Convention

When invoking a logical BioETL profile through a native Codex agent:

- mention the profile file path explicitly
- pass `task_id`, `phase` / `mode`, and `scope`
- require the expected artifact path when the profile defines one

## Related Files

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `.codex/agents/ORCHESTRATION.md`
- `.codex/skills/agent-orchestration/SKILL.md`
- `AGENTS.md`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
