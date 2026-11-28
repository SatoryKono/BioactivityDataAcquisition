---
name: "source-command-post-change"
description: "Чеклист post-change по skill bioetl-post-change"
---

# source-command-post-change

Use this skill when the user asks to run the migrated source command `post-change`.

## Command Template

Канон:

- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

Выполни skill `bioetl-post-change` (`docs/00-project/ai/grok/skills/bioetl-post-change/SKILL.md`). Политика: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

Текст после `/post-change` в промпт не подставляется. Не заводи второй чеклист.

<!-- bioetl:managed-cursor-command -->
