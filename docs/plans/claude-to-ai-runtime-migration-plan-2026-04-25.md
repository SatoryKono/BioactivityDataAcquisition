# План миграции `.claude/*` → `ai/claude/*`

Дата: 2026-04-25
Статус: Draft
Владелец: Engineering / Architecture

## Цель

Перенести runtime-артефакты из `.claude/` в `ai/claude/` с обновлением ссылок, тестов и скриптов так, чтобы:

- не сломать CI;
- сохранить обратную совместимость на переходный период;
- после стабилизации безопасно удалить `.claude/`.

## Целевая структура

- `.claude/agents/*` → `ai/claude/agents/*`
- `.claude/rules/*` → `ai/claude/rules/*`
- `.claude/skills/*` → `ai/claude/skills/*`

## Фаза 1. Миграция с обратной совместимостью

1. Создать целевые директории `ai/claude/agents`, `ai/claude/rules`, `ai/claude/skills`.
2. Перенести содержимое `.claude/*` в `ai/claude/*`.
3. Оставить `.claude/*` как compatibility-layer на один релиз:
   - либо через дубли/stub-файлы с указанием нового пути;
   - либо через временное сохранение копий (предпочтительно для кроссплатформенности).
4. Обновить runtime-ссылки в `.codex/skills/*/SKILL.md`, где встречается `../../../.claude/...`.

### Критерий выхода Фазы 1

- Все runtime-сценарии работают и с новым путем `ai/claude/*`.
- Старые пути `.claude/*` пока еще не удалены.

## Фаза 2. Обновление тестов и скриптов

1. Исправить архитектурные тесты с жесткой привязкой к `.claude`:
   - `tests/architecture/test_runtime_orchestration_surfaces.py`
   - `tests/architecture/test_codex_skill_agent_links.py`
   - `tests/architecture/test_architecture_debt_agent_surface.py`
2. Исправить утилиты/диагностику/CI, где захардкожен `.claude`:
   - `scripts/engineering/repo/preflight_cleanup.sh`
   - `scripts/engineering/repo/audit_root_cleanliness.py`
   - `scripts/engineering/diagnostics/audit_structure.py`
   - `scripts/engineering/qa/py_review_orchestrator.py`
   - `scripts/engineering/ci/apply_ci_fixes.py`
   - связанные PowerShell-скрипты в `scripts/engineering/ci/`

### Критерий выхода Фазы 2

- Архитектурные тесты и инженерные скрипты не требуют `.claude/*`.

## Фаза 3. Документация и политика

1. Обновить документы, где `.claude/*` указан как canonical:
   - `docs/00-project/ai/README.md`
   - `docs/00-project/ai/agents/README.md`
   - `docs/00-project/ai/skills/README.md`
   - `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`
   - `README.md` и governance-документы при необходимости.
2. В `CHANGELOG.md` добавить запись о миграции путей.
3. Исторические упоминания старого пути не переписывать, если это описания прошлого состояния.

### Критерий выхода Фазы 3

- Документация синхронизирована с новой структурой `ai/claude/*`.

## Фаза 4. Деактивация и удаление `.claude`

1. Удалить compatibility-layer `.claude/*`.
2. Проверить отсутствие живых ссылок:
   - `rg -n "\.claude/" .`
3. При необходимости оставить только архивную ссылку в документации (без runtime-зависимости).

### Критерий выхода Фазы 4

- В коде, тестах, CI и активной документации нет runtime-зависимости от `.claude/*`.

## Проверочный чек-лист (после каждой фазы)

1. `pytest tests/architecture -q`
2. `python -m mypy --strict src/bioetl/`
3. `pytest -q` (или штатный shard/xdist pipeline проекта)
4. `rg -n "\.claude/" .` и ревью всех найденных вхождений

## Стратегия внедрения

- Рекомендуется выполнить в двух PR:
  - PR1: перенос + compatibility-layer + обновление ссылок/тестов/скриптов;
  - PR2: удаление `.claude/*` после стабилизации и прохождения CI.

