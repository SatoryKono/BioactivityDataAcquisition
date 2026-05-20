______________________________________________________________________

Version: 1.1.2
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-29'

______________________________________________________________________

# Agent Memory Runtime Alias

Deprecated compatibility alias for the shared BioETL agent memory.

- Canonical memory surface: [../../memory/agent-memory.md](../../memory/agent-memory.md)
- Memory usage policy: [../guides/MEMORY_USAGE.md](../guides/MEMORY_USAGE.md)
- Post-change validation policy: [../policy/POST_CHANGE_VALIDATION.md](../policy/POST_CHANGE_VALIDATION.md)

This file exists only to preserve legacy runtime/docs references. Do not fork
content here. Update the canonical memory file instead.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
