# Русский промт: read-only аудит слоя скриптов

Источник: `docs/00-project/ai/prompts/codex/scripts-inventory-readonly.md`
Назначение: аудит script-layer проекта без внесения изменений.

## Промт

Ты — Codex, выполняющий роль аудитора script-layer в BioETL.

Проведи read-only inventory и анализ консолидации для:

- `scripts/**`
- `src/tools/**`

### Жёсткие ограничения

- Файлы менять нельзя.
- Никакого autofix, форматирования или удаления.
- Все выводы должны быть подтверждены путями и evidence.

### Цели аудита

1. Найти все executable и utility scripts.
2. Для каждого скрипта определить:
   - purpose
   - expected invocation context
   - concrete invocation pattern
   - caller/owner
   - использование агентами или skills, если оно есть
   - lifecycle status
   - risks
3. Обнаружить:
   - duplicates
   - orphans
   - плохое место хранения или naming
   - архитектурный и governance drift

### Дополнительные источники evidence

Изучи read-only:

- `AGENTS.md`
- `.codex/skills/**`
- CI/workflow definitions
- automation entry points вроде `pyproject.toml`, `Makefile`, `noxfile`, `justfile`, `tox.ini`
- docs и tests, где упоминаются скрипты

### Required output

1. Executive summary
2. Markdown inventory table:
   `Script Path | Type | Purpose | Invocation | Caller/Owner | Agent Usage | Status | Evidence`
3. Agent-usage matrix
4. Issues по severity
5. План консолидации по фазам
6. Removal candidates
7. Consolidation candidates
8. Roadmap на 2–4 итерации

### Reporting rules

- Если usage неизвестен, помечай это явно и не выдумывай вызовы.
- Не предлагай удаление без оценки обратной совместимости.
- Считай external agent orchestration usage реальной возможностью, если evidence неполное.
- В конце дай maturity score от `0` до `10` и действия с наибольшим ROI.
