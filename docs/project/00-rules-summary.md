# Rules Summary

## 1. Архитектура и структура

- Hexagonal (Ports & Adapters) + DDD.
- Слои: domain, application, infrastructure, interfaces.
- Пайплайны: `src/bioetl/application/pipelines/<provider>/<entity>/`.
- Документация: kebab-case с NN- префиксом, синхронизирована с кодом; пайплайны описываются в `docs/application/pipelines/<provider>/<entity>/`.
 - Инварианты: одна сущность → один публичный пайплайн; строгая последовательность `extract→transform→validate→export`.

## 2. Именование

- Классы: `PascalCase` + суффикс (Factory, Client, Impl, ABC, etc.).
- Модули: `snake_case`.
- Функции: `snake_case` + префикс (get, fetch, create, etc.).
- Доки: `kebab-case`.
 - Pipeline docs: `NN-<entity>-<provider>-<topic>.md`.
 - Naming‑linter в CI, исключения — через `configs/naming_exceptions.yaml`.

## 3. Данные и Схемы

- Pandera-схемы для всех выходов.
- Полный регламент валидации: `docs/domain/schemas/01-pandera-validation-rules.md` (ValidationService + SchemaRegistry, strict/coerce, OUTPUT_COLUMN_ORDER, обязательные системные колонки, lazy-валидация).
- Pydantic для конфигов и JSON.
- Валидация перед записью.
- Детерминизм: сортировка, атомарная запись, чек-суммы.
- `input_mode`/`input_path`/`csv_options` в конфиге ChEMBL выбирают источник данных (api|csv|id_only).
 - UTC‑время, каноническая сериализация JSON; неизменяемые артефакты.

## 4. Код и Качество

- PEP8, Black, Ruff, Mypy (strict).
- Логирование через `UnifiedLogger` (структурное).
- Тесты: Unit (mock net), Integration, Golden. Coverage ≥85%.
- Zero-sum class count при дублировании.
- Чек-лист ревью пайплайнов: `docs/templates/pipeline-review-checklist.md`.
 - Запрет `print()`, секреты не логируются; pre‑commit/CI блокируют нарушения.

## 5. API и Инфраструктура

- `UnifiedAPIClient` для всех запросов (retry, backoff).
- Секреты в ENV.
- CLI на Typer.
 - Rate limit и circuit breaker при необходимости; корректная пагинация и частичные сбои.
 - Стандартизированные sidecar‑файлы `meta.yaml`, QC‑отчёты при экспорте.

## 6. Документация

- Автогенерируемые секции помечаются `<!-- generated -->` и не редактируются вручную.
- Синхронизация docs ↔ код ↔ схемы обязательна; breaking changes фиксируются в `CHANGELOG.md` и ADR.

## 7. Рефакторинг модулей

- **Контекст**: Подготовка к рефакторингу модуля X в BioETL.
- **Задача**: Составить карту зависимостей для безопасного рефакторинга.
- **Действия**:
  1. Найти все импорты модуля: `grep -r "from bioetl.domain.X import" src/` и `grep -r "import bioetl.domain.X" src/`
  2. Найти все использования классов/функций: `grep -r "X\." src/ --include="*.py"`
  3. Найти упоминания в тестах: `grep -r "X" tests/ --include="*.py"`
  4. Проверить re-exports в `__init__.py`: `grep -r "X" src/bioetl/domain/__init__.py`
- **Формат вывода**:
  - Список файлов, импортирующих модуль
  - Список файлов, использующих конкретные классы
  - Список тестов для обновления
  - Рекомендации по порядку миграции
- **Правило**: Рефакторинг без карты зависимостей запрещён; тесты обновляются до изменения реализации; breaking changes документируются.
