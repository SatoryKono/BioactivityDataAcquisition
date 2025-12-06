# 00 Rules Summary

## 1. Архитектура и структура
- Hexagonal (Ports & Adapters) + DDD.
- Слои: domain, application, infrastructure, interfaces.
- Пайплайны: `src/bioetl/application/pipelines/<provider>/<entity>/`.
- Документация: kebab-case с NN- префиксом, синхронизирована с кодом; пайплайны описываются в `docs/application/pipelines/<provider>/<entity>/`.

## 2. Именование
- Классы: `PascalCase` + суффикс (Factory, Client, Impl, ABC, etc.).
- Модули: `snake_case`.
- Функции: `snake_case` + префикс (get, fetch, create, etc.).
- Доки: `kebab-case`.

## 3. Данные и Схемы
- Pandera-схемы для всех выходов.
- Полный регламент валидации: `docs/domain/schemas/01-pandera-validation-rules.md` (ValidationService + SchemaRegistry, strict/coerce, OUTPUT_COLUMN_ORDER, обязательные системные колонки, lazy-валидация).
- Pydantic для конфигов и JSON.
- Валидация перед записью.
- Детерминизм: сортировка, атомарная запись, чек-суммы.
- `input_mode`/`input_path`/`csv_options` в конфиге ChEMBL выбирают источник данных (api|csv|id_only).

## 4. Код и Качество
- PEP8, Black, Ruff, Mypy (strict).
- Логирование через `UnifiedLogger` (структурное).
- Тесты: Unit (mock net), Integration, Golden. Coverage ≥85%.
- Zero-sum class count при дублировании.

## 5. API и Инфраструктура
- `UnifiedAPIClient` для всех запросов (retry, backoff).
- Секреты в ENV.
- CLI на Typer.
