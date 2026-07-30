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

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-review-orchestrator` or `code-review` | diff inspection; no external writes |
| Investigate and fix CI | write only after root cause | GitHub CI workflow / `py-debug-bot` | failed checks plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | `create-pr` | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-architecture-debt-bot` | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only
unless the user also asks for implementation. Load the selected skill and
relevant sources/tests; do not load every ADR or the whole repository by
default.

## Risk-Based Validation

| Tier | Typical scope | Minimum checks |
| --- | --- | --- |
| V1 | docs-only | targeted links/drift and mirror sync |
| V2 | focused Python/tooling | targeted Ruff plus related unit tests |
| V3 | config/runtime contract | schema/contract checks plus related tests |
| V4 | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests |

Every closeout reports checks run, skipped checks with exact reasons/follow-up,
runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or
`worsened`). A lower tier cannot bypass an applicable architecture,
determinism, security, or technical-debt gate. `worsened` cannot be hidden by
raising a budget or exemption limit.

## Related Runtime Surfaces

- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/skills/`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
