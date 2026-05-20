# Deprecated Alias: `ORCHESTRATION.md`

This document path is deprecated.

Canonical file: [../agents/ORCHESTRATION.md](../agents/ORCHESTRATION.md)

Do not edit this alias directly.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
