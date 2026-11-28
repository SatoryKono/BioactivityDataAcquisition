---
name: "source-command-pre-commit"
description: "Локальные гейты перед коммитом"
---

# source-command-pre-commit

Use this skill when the user asks to run the migrated source command `pre-commit`.

## Command Template

Канон:

- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Следуй `docs/00-project/ai/rules/windsurf/workflows/pre-commit.md`. Поле `auto_execution_mode` игнорируй.

Команда смотрит текущие изменения. Текст после `/pre-commit` в промпт не подставляется.

<!-- bioetl:managed-cursor-command -->
