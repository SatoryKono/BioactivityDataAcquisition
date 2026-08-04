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

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=codex \
BIOETL_AI_AGENT=<active-profile-or-codex> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Native Project Discovery

- `.codex/config.toml` contains portable trusted-project settings only.
- `.codex/agents/py-*.toml` exposes the nine governed profiles to native Codex
  custom-agent discovery. Each thin descriptor routes to its matching Markdown
  profile, skill, and memory sheet; the parent model is inherited.
- `.codex/skills/**` remains the behavioral skill source. Generated,
  platform-neutral `.agents/skills/*/SKILL.md` adapters expose that catalog to
  native repository discovery without requiring copies in the user home.
- Validate these surfaces with
  `python3 scripts/ai/codex/doctor.py static --no-write`.

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
- `.codex/config.toml`
- `.codex/agents/py-*.toml`
- `.codex/skills/`
- `.agents/skills/`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
