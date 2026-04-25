# План миграции: удаление root `memory/` shim и переход на `src/memory`

## Цель

Убрать корневой shim `memory/__init__.py` и оставить единственный источник истины в `src/memory`, без регресса импортов, CLI и CI.

## Текущее состояние

- `src/memory/` уже канонический пакет.
- `memory/__init__.py` в корне — compatibility shim.
- Есть потребители с импортами вида `from memory...` (это нормально), но важно где и как запускаются команды (какой `PYTHONPATH`).

## Критерии готовности миграции

1. В репозитории нет необходимости в корневом пакете `memory/`.
2. Все команды/скрипты и тесты, использующие `memory`, работают через `src`-layout.
3. CI зелёный на архитектурных, unit, integration и docs lane.
4. Документация и onboarding отражают новый контракт запуска.

## План миграции (поэтапно)

### 1. Инвентаризация и freeze

1. Зафиксировать ветку миграции (`chore/memory-shim-removal`).
2. Собрать список всех запусков, где используется `import memory`:
   - `scripts/memory/*`
   - `testing_support/*`
   - `tests/unit/memory/*`
   - локальные команды из README/SKILL.
3. Заморозить параллельные изменения в `src/memory`, `scripts/memory`, `pyproject.toml` на время миграции.

### 2. Определить целевой runtime-контракт

1. Принять единый способ запуска:
   - через `.venv/bin/python -m ...` из корня, где `src` гарантированно в пути, или
   - через editable install (`pip install -e .`), или
   - через явный `PYTHONPATH=src`.
2. Закрепить это в одном месте:
   - `pyproject.toml` (если нужно package-dir/entrypoints),
   - `scripts/*` wrappers (если нужно экспортировать `PYTHONPATH=src`).

### 3. Подготовить кодовую базу к удалению shim

1. Пройтись по `scripts/memory/*.py` и `testing_support/*`:
   - убрать неявную зависимость от корневого пакета.
   - при необходимости добавить bootstrap `sys.path` только в CLI-обёртки (не в библиотечный код).
2. Проверить, что импорты `from memory...` резолвятся из `src/memory`, а не из корня.
3. Обновить smoke-команды в `scripts/memory/README.md` и `docs/00-project/ai/memory/README.md`.

### 4. Мягкий переход (deprecation window)

1. На 1 релиз оставить shim, но добавить предупреждение `DeprecationWarning` в `memory/__init__.py`.
2. В warning указать дату удаления и требуемый контракт запуска.
3. Добавить тест, проверяющий наличие предупреждения и корректный fallback в `src/memory`.

### 5. Удаление shim

1. Удалить `memory/__init__.py` и пустую директорию `memory/`.
2. Удалить связанные исключения/обходы в тестах, если были.
3. Обновить docs и внутренние инструкции на “только `src/memory`”.

### 6. Валидация

1. Быстрый прогон:
   - `ruff check src tests`
   - `mypy` для пакетов `src/memory`, `scripts/memory`, `testing_support`.
2. Таргетный прогон:
   - `tests/unit/memory`
   - `tests/unit/scripts` (особенно `scripts/memory`)
   - `tests/architecture` (import policy, drift, formatting)
3. Полный шардовый прогон CI lanes, где раньше были падения по импорту/форматированию.
4. Ручной smoke:
   - `python -m scripts.memory.__main__ --help`
   - ключевые команды из `scripts/memory/README.md`.

### 7. Роллбек-план

1. Если ломаются прод-команды/CI:
   - вернуть `memory/__init__.py` одним коммитом.
   - оставить deprecation и открыть issue на конкретный проблемный рантайм.
2. Хранить rollback-коммит готовым до закрытия релиза.

## Технические риски и меры

- Риск: локальные IDE/runner не добавляют `src` в `sys.path`.
  Мера: зафиксировать единый способ запуска и проверить в CI/Windows/WSL.
- Риск: скрытые зависимости в скриптах.
  Мера: таргетные smoke-тесты `scripts/memory/*`.
- Риск: дрейф документации.
  Мера: обновить docs в том же PR и прогнать docs-check.

## Рекомендуемая нарезка на PR

1. PR-1: контракт запуска + docs + deprecation warning (без удаления).
2. PR-2: удаление shim + cleanup + тесты.
3. PR-3 (опционально): ужесточение проверок (например, тест “root `memory/` отсутствует”).

## Definition of Done

- Нет директории `memory/` в корне.
- Все тестовые lane проходят.
- Все documented команды для memory работают.
- В docs явно указано: канонический пакет только `src/memory/`.
