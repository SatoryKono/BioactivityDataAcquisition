---
name: "source-command-review"
description: "Ревью текущего diff через skill py-audit-bot"
---

# source-command-review

Use this skill when the user asks to run the migrated source command `review`.

## Command Template

Канон:

- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Выполни skill `py-audit-bot` (`.codex/skills/py-audit-bot/SKILL.md`) по текущему diff. Текст после `/review` в промпт не подставляется.

Не копируй чеклист из Windsurf или Devin workflow. Процедура ревью — этот skill.

Ответ: blocker / warning / note, с путём и конкретным исправлением. Текст GitHub review — на русском.

<!-- bioetl:managed-cursor-command -->
