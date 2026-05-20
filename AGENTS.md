# BioETL AI Runtime Entry Point

This file is the root operating contract for AI runtime surfaces in this
repository.

## Canonical Precedence

For AI runtime behavior and workflow conflicts, use this priority:

1. active runtime source for the current agent or skill:
   - `.codex/agents/CODEX-RUNTIME.md`
   - `.gemini/agents/GEMINI-RUNTIME.md`
1. runtime profiles and skills in the matching runtime tree
1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs in `docs/02-architecture/decisions/`
1. docs mirrors and helper AI docs in `docs/00-project/ai/**` for navigation
   and guidance only

Docs mirrors MUST NOT redefine runtime behavior on their own.

## Required AI Context

Before planning, auditing, or editing:

1. Read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`.
1. Read `docs/00-project/ai/memory/agent-memory.md`.
1. Read the relevant `docs/00-project/ai/memory/memory-py-*.md` file when a
   role-specific memory sheet exists.
1. Use the canonical memory workflow from `src/memory/DAILY_WORKFLOW.md`
   through `python -m memory.tooling.workflow pre-task ...` and
   `python -m memory.tooling.workflow post-task ...`.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.
- Switch away from Russian only when the user explicitly requests another
  language.

## Post-Change Validation

For any write-capable task, follow
`docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

Minimum expectation:

1. Re-scan impacted code/config/doc/runtime surfaces before finalizing.
1. Use repo search plus memory/evidence anchors to find related tests, docs,
   contracts, configs, and workflows.
1. Edit runtime source first, then sync docs mirrors when behavior or
   contributor guidance changed.
1. Report checks run, skipped checks, and mirror-sync status explicitly.

## Guardrails

- BioETL remains local-only by default; do not introduce Docker, Redis, or
  external orchestration requirements unless the task explicitly requires them.
- `.codex/**` is the canonical Codex runtime source.
- `.gemini/**` is the canonical Gemini runtime source.
- `.claude/**` is not an active runtime source for Codex/Gemini behavior in
  this change program and is treated as unavailable until a local checkout
  proves otherwise.
- `docs/00-project/ai/memory/mcp-memory.json` and
  `docs/00-project/ai/memory/gemini-memory.json` are machine-readable memory
  artifacts, not human source of truth.

## Related Files

- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
