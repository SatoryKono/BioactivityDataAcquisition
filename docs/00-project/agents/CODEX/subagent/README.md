# CODEX Subagents

Каталог спецификаций subagent-ов Codex для BioETL.

## Структура
- `pyPlanBot/SUBAGENT.md` — планирование и консолидация плана
- `pyTestBot/SUBAGENT.md` — разработка/запуск тестов, анализ результатов
- `pyDebugBot/SUBAGENT.md` — отладка падений тестов и регрессий
- `pyDocBot/SUBAGENT.md` — обновление документации и docstring
- `pyAuditBot/SUBAGENT.md` — baseline/final аудит соответствия RULES/ADR

## Артефакты
Все subagent-ы пишут отчёты в `reports/plans/<task_id>/` согласно workflow из `docs/00-project/agents/CODEX.md`.
