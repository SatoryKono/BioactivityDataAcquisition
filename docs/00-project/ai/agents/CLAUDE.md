# CLAUDE (Compatibility Stub)

Deprecated compatibility path.

- Canonical guide: [guides/CLAUDE.md](guides/CLAUDE.md)
- Runtime-oriented docs: [../memory/agent-memory.md](../memory/agent-memory.md)
- Dashboard extension playbook (LLM): [../../../03-guides/dashboards/dashboard-extension-llm.md](../../../03-guides/dashboards/dashboard-extension-llm.md)

*Synchronized with `docs/00-project/RULES.md` (read header `Version:`; do not pin a copy here)*

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
