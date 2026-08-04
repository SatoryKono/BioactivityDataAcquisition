# CODEX-RUNTIME.md — Runtime Map For BioETL Agents

## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`

## Purpose

Map logical BioETL `py-*` profiles onto the native Codex runtime roles used in this repository.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Recommended Mapping

- `py-audit-bot` -> `default`
- `py-architecture-debt-bot` -> `default`
- `py-plan-bot` -> `default`
- `py-test-bot` -> `default` or `worker`
- `py-config-bot` -> `worker`
- `py-debug-bot` -> `worker`
- `py-doc-bot` -> `worker`
- `py-test-swarm` -> `default`
- `py-review-orchestrator` -> `default`

## Related Runtime Surfaces

- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/skills/`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
