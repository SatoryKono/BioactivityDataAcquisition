# Cursor Rules

Структурированные правила для Cursor AI, основанные на стандартах проекта BioETL.

## Структура

Правила организованы по категориям и применяются автоматически на основе триггеров и glob-паттернов.

## Основные правила (Always On)

- **00-core-principles.mdc** — базовые принципы проекта (детерминизм, схемы, логирование, CI)
- **cursorrules.mdc** — основной файл правил проекта (всегда применяется)

## Правила по триггерам (Model Decision)

- **01-naming-conventions.mdc** — именование документации (lowercase-hyphen, NN- префиксы)
- **02-python-style.mdc** — стиль Python кода (ruff/black, mypy, типы)
- **03-logging.mdc** — логирование (UnifiedLogger, структурированные события)
- **04-data-schemas.mdc** — схемы данных (Pandera, валидация перед записью)
- **05-deterministic-io.mdc** — детерминированный I/O (сортировка, UTC, атомарная запись)
- **06-testing.mdc** — тестирование (категории, golden tests, покрытие ≥85%)
- **07-cli-contracts.mdc** — контракты CLI (Typer, exit codes, валидация)
- **08-api-clients.mdc** — клиенты API (UnifiedAPIClient, retry, rate limit)
- **09-etl-architecture.mdc** — архитектура ETL (пайплайны, unified components)
- **10-secrets-and-config.mdc** — секреты и конфигурация (env, Pydantic, profiles)
- **11-abc-default-impl-policy.mdc** — политика ABC/Default/Impl (трёхслойный паттерн)
- **12-entity-naming-policy.mdc** — политика именования сущностей (классы, функции, модули)
- **13-documentation-standards.mdc** — стандарты документации (синхронизация, автогенерация)

## Использование

Правила применяются автоматически при редактировании соответствующих файлов. Каждое правило содержит:

- `trigger` — когда применять правило
- `description` — описание назначения правила
- `globs` — паттерны файлов, к которым применяется правило

## Связанная документация

- `docs/00-styleguide/` — подробные руководства по стилю
- `docs/02-pipelines/` — документация по пайплайнам
- `docs/cli/` — документация по CLI

