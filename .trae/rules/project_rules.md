# Проект BioETL

- **Ответы**: на русском, кратко.
- **Детерминизм**: обязателен (стабильный порядок колонок/строк, UTC, атомарная запись через temp→os.replace).
- **Валидация**: Pandera-схемы для всех таблиц перед записью.
- **Архитектура**:
  - Логирование: `UnifiedLogger`.
  - API: `UnifiedAPIClient` (retry/backoff/rate limit).
  - Трёхслойный паттерн: ABC (infrastructure/clients/base/contracts) → Default factory → Impl.
- **Именование**:
  - Модули: snake_case.
  - Классы: PascalCase (Factory, Client, Impl, Config).
  - Функции: snake_case (get_, fetch_, iter_, create_).
- **Docs**: kebab-case с `NN-` префиксом в `docs/application/pipelines/`.
- **Тесты**: coverage ≥85%, golden-тесты, без сети в unit-тестах.
- **Секреты**: env/secret manager.
- **Пути**:
  - Pipelines: `src/bioetl/application/pipelines/<provider>/<entity>/<stage>.py`.
  - Clients: `src/bioetl/infrastructure/clients/`.

- Проект BioETL: ответы на русском, кратко. Детерминизм обязателен (стабильный порядок колонок/строк, UTC, атомарная запись через temp→os.replace). Pandera-схемы для всех таблиц, валидация перед записью. Логирование только через UnifiedLogger, API через UnifiedAPIClient с retry/backoff/rate limit. Трёхслойный паттерн: ABC→Default factory→Impl. Именование: модули snake_case, классы PascalCase с суффиксами (Factory, Client, Impl, Config), функции с префиксами (get_, fetch_, iter_, create_). Docs: kebab-case с NN- префиксом. Тесты: coverage ≥85%, golden-тесты, без сети в unit-тестах. Секреты только через env/secret manager. Pipelines: src/bioetl/pipelines/<provider>/<entity>/<stage>.py.
- Refactoring constraint: ЛЮБОЕ ДОБАВЛЕНИЕ КЛАССА (кроме ABC) должно сопровождаться исключением другого класса. Общее кол-во классов (кроме ABC) не может увеличиваться без прямого приказа пользователя.
---
description: Always apply core project invariants (determinism, schemas, logging, CI discipline)
globs:
alwaysApply: true
---

# Core principles

## Purpose

Enforce non-negotiable invariants across the whole repo so the agent does not guess.

## Principles (mandatory)

- Deterministic I/O: identical inputs+config produce bit-identical outputs. Use stable row/column order, UTC timestamps, canonical JSON, atomic writes.
- Validate-before-write: every table is validated against a Pandera schema with fixed column order. No writes on validation failure.
- Structured logging only via UnifiedLogger; no print(); include run context and mandatory fields.
- Tests: no network in unit tests; golden tests for critical outputs; property-based tests for transformations; coverage ≥ 85% in CI.
- API access only through UnifiedAPIClient with retry/backoff, rate limiting, circuit breaker and strict timeouts.
- One source → one public pipeline; use unified components (Logger, Writer, Client, Schema); follow extract→transform→validate→export.
- Secrets in env/secret manager only; typed configs via Pydantic; profiles for shared defaults; CI secret scanning enabled.
- Python style: ruff/black, isort, mypy --strict; no wildcard imports, no global mutable state, no magic numbers.

## When to use

Always. Treat as global constraints for planning, codegen, edits and refactors.

## Do

- Refuse to emit write code without prior schema validation and deterministic sorting.
- Bind run context once, log with structured key-value.
- Fail fast on missing config or secret.
- Prefer composition over inheritance in components.

## Don't

- Don't emit print(), ad-hoc logging, local time, non-atomic writes, or unordered CSV/JSON.
- Don't call external APIs outside UnifiedAPIClient or without throttling/retry policy.
- Don't bypass tests or lower coverage thresholds.

## Reference

See [docs/INDEX.md](../../docs/INDEX.md) for overview and [docs/styleguide/](../../docs/styleguide/) for detailed style guides.
---
description: USE WHEN writing or modifying documentation files or file names; enforce lowercase-hyphen names and NN- sequencing
globs: ["docs/**/*.md", "**/INDEX.md", "**/README.md"]
alwaysApply: false
---

# GOAL

Keep doc navigation predictable.

# RULES

- Filenames in English, lowercase, words separated by hyphens.
- Sequenced docs use two-digit prefix `NN-` (e.g., `01-overview.md`).
- Pipeline docs format: `NN-<entity>-<provider>-<topic>.md`.
- Landing-page naming details live in `docs-landing-pages-index-readme.mdc`.
- Canonical identifiers: code/configs use `snake_case`, docs filenames use `kebab-case`.

# EXAMPLES

Valid:
- `docs/application/pipelines/00-pipeline-base.md`
- `docs/application/pipelines/chembl/activity/01-activity-chembl-extract.md`

Invalid:
- `Docs/Overview.MD`
- `etlOverview.md`
- `01_overview.md`

# REFERENCE

See `docs/FILE_POLICY.md` and `docs/project/00-rules-summary.md`.
---
description: Правила проекта BioETL — именование, архитектура, документация, детерминизм, тестирование
alwaysApply: true
tags: [naming, architecture, documentation, styleguide, determinism, testing]
version: "2.0.0"
---

# Правила проекта BioETL

## 0. Формат ответов

- Отвечайте кратко
- Избегайте ненужных повторений и лишних слов
- Все ответы на русском

## 1. Именование документации

- **Файлы документации**: kebab-case, двузначный префикс `NN-`
- **Pipeline docs**: формат `NN-<entity>-<provider>-<topic>.md`
- **Язык**: английский, lowercase, разделители `-` (не `_`)
- **H1 заголовок**: дублирует имя файла в Title Case
- **Автогенерация**: секции помечаются `<!-- generated -->`
- **Канонические идентификаторы**: в коде/configs используется `snake_case`, в docs filenames — `kebab-case`

## 2. Политика создания ABC/Default/Impl

### Трёхслойный паттерн (обязателен)

- **Contract/Protocol/ABC**: `src/bioetl/clients/<domain>/contracts.py` или `base/contracts.py`
- **Default factory**: `src/bioetl/clients/<domain>/factories.py`, функция `default_<domain>_<entity>()`
- **Impl**: `src/bioetl/clients/<domain>/impl/`, классы с суффиксом `Impl`

### Обязательные реестры

- `src/bioetl/clients/base/abc_registry.yaml` — машинный реестр ABC
- `src/bioetl/clients/base/abc_impls.yaml` — мэппинг Default/Impl
- `docs/ABC_INDEX.md` — человекочитаемый каталог

### Правила создания

- При создании ABC **обязательно** создать Default (может быть stub)
- Default может быть stub с `NotImplementedError` если нет реальных Impl
- Добавление Impl не требует нового Default
- ABC **обязан** иметь структурированный докстринг (краткое описание, публичный интерфейс, локализация, указатели на Default/Impl)

## 3. Именование сущностей

### Базовые правила

- **Модули**: `^[a-z0-9_]+$` (snake_case)
- **Классы**: PascalCase, `^[A-Z][A-Za-z0-9]+$`
- **Функции**: snake_case, `^[a-z_][a-z0-9_]*$`
- **Константы**: UPPER_SNAKE_CASE, `^[A-Z][A-Z0-9_]*$`
- **Приватные**: ведущий `_`

### Суффиксы классов (роли)

- `Factory` — общие фабрики
- `ClientFactory` — фабрики клиентов
- `DataClient` — реализации контрактов
- `Client` — общие клиенты
- `Facade` — фасады верхнего уровня
- `Registry` — реестры
- `Adapter`/`Transport` — низкоуровневые адаптеры/транспорты
- `Protocol`/`ABC` — контракты
- `Config`/`Model`/`Params` — конфигурационные/модельные типы
- `Error` — исключения
- `Impl` — реализации (например, `ChemblDataClientHTTPImpl`)

### Префиксы функций

- `get_` — дешёвые локальные чтения
- `fetch_` — сетевые/IO операции
- `iter_` — ленивые генераторы/итераторы
- `create_`/`build_`/`make_`/`default_` — создание объектов/фабрики
- `register_` — регистрация в реестрах
- `resolve_`/`ensure_` — нормализация/подготовка
- `validate_`/`parse_`/`serialize_` — валидация/парсинг/сериализация
- `on_` — callback/обработчики
- `is_`/`has_`/`can_` — булевы проверки

### Pipelines

- Путь: `src/bioetl/pipelines/<provider>/<entity>/<stage>.py`
- Provider: `^[a-z0-9_]+$`
- Entity: `^[a-z0-9_]+$`
- Stage: `extract`, `transform`, `validate`, `normalize`, `write`, `run`, `errors`, `descriptor`, `metrics`, `backfill`, `cleanup`

### Тесты

- Unit: `tests/bioetl/.../test_<module>.py`
- Pipeline: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py`
- Integration: `tests/integration/` или суффикс `_integration.py`
- Golden: `tests/golden/test_<area>_golden.py`

### Конфиги

- Файлы: `^[a-z0-9_]+.ya?ml$` в `configs/`
- Pipelines: `configs/pipelines/<provider>/<entity>.yaml`
- Ключи внутри YAML: lower_snake_case

## 4. Стандарты документации

- **Синхронизация**: документация **обязательно** синхронизируется с кодом и схемами
- **Автогенерация**: секции помечаются `<!-- generated -->`, не редактируются вручную
- **При добавлении сущности**: обновлять `docs/02-pipelines/<provider>/<entity>/NN-<entity>-<provider>-<topic>.md`, `docs/ABC_INDEX.md`, реестры
- **Breaking changes**: фиксируются в `CHANGELOG.md`

## 5. Python Code Style

- Следование PEP 8
- Публичные функции и датаклассы имеют аннотации типов
- `mypy` обязателен для публичных API
- Чистые функции там, где возможно
- Форматирование и сортировка импортов единообразны
- `from x import *` запрещен
- Одна ответственность на файл
- Приватные модули начинаются с `_`
- Публичные символы экспортируются через `__all__` в `__init__.py`

## 6. CI и enforcement

- Naming linter проверяет соответствие regex-паттернам
- CI блокирует PR при MUST-нарушениях
- Исключения регистрируются в `configs/naming_exceptions.yaml` с полями: `path`, `rule_id`, `reason`, `owner`, `expiry`
- Pre-commit hook рекомендуется для локальной проверки

## 7. Детерминизм и стабильность

- Фиксированный порядок колонок/строк
- UTC-время
- Каноническая сериализация
- Атомарная запись (temp → os.replace) для файлов с данными/артефактами
- НЕЛЬЗЯ вносить silent-изменения публичных API/CLI/схем
- Любой breaking change сопровождается миграционной заметкой и изменением версий
- Однозначность и проверяемость: все преобразования и эвристики описаны явно и покрыты тестами
- Идемпотентность шагов и воспроизводимость артефактов, включая метаданные (`meta.yaml`)

### Пример атомарной записи

```python
tmp = path.with_suffix(".tmp")
tmp.write_text(payload, encoding="utf-8")
os.replace(tmp, path)
```

## 8. Нормализация данных

- **Стандартные типы**: `int`, `float`, `string`, `datetime`, `boolean` — явные приведения, политика `NA/NULL`, trimming, локали и десятичный разделитель
- **Специальные идентификаторы**: DOI, ChEMBL ID, UniProt Accession, IUPHAR ID, PubChem CID, SMILES, InChI — валидация форматов и нормализация до записи
- **Стабильные ключи сортировки** и хеш-столбцы (`hash_row`, `hash_business_key`)

## 9. Схемы и валидация

- Pandera-схемы обязательны для всех итоговых таблиц
- Диапазоны, категории и regex-ограничения заданы явно
- Несовпадения типов/колонок с `column_order` — ошибка сборки
- Источники истины: конфиги YAML и Pandera-схемы. Код обязан им соответствовать

## 10. Клиенты внешних API

- Таймауты, ретраи с backoff, ограничение QPS, кэш/TTL, корректный User-Agent
- Правильная обработка пагинации и частичных сбоев
- Контракт‑тесты

## 11. Тестирование и CI

- Юнит‑, интеграционные, golden‑тесты на критические трансформы
- Property‑based тесты уместно
- Минимальный порог покрытия кода — определяется в проектных правилах
- CI блокирует PR при нарушении покрытия

## 12. Экспорт, QC и метаданные

- Перед экспортом: явная сортировка по ключам и проверка соответствия `column_order`
- Обязательные QC‑сайдкары: `quality_report_table.csv`, `correlation_report_table.csv`
- `meta.yaml` содержит `pipeline_version`, `chembl_release`, `row_count`, checksums

## 13. Коммиты и PR

- Атомарные изменения, информативные сообщения коммитов с ссылкой на задачу
- Чеклист PR: стиль, тесты, схемы, конфиги, docs, детерминизм, CI зелёный

## 14. Безопасность и секреты

- Секреты только через переменные окружения/секрет‑менеджер
- Запрет хардкода
- Скан утечек в CI
- Политика ротации/ревокации ключей

## 15. Производительность

- Бюджеты по памяти/времени
- Батчи/стриминг, промежуточные сохранения
- Профилирование горячих путей и фикс‑регрессий

## 16. Ограничения количества классов

- **Zero-sum class count**: ЛЮБОЕ ДОБАВЛЕНИЕ КЛАССА (кроме ABC) должно сопровождаться исключением другого класса.
- **Исключение**: Общее кол-во классов (кроме ABC) не может увеличиваться без прямого приказа пользователя.

## Источники истины

- `docs/00-styleguide/00-naming-conventions.md` — именование документации
- `docs/00-styleguide/01-new-entity-implementation-policy.md` — политика ABC/Default/Impl
- `docs/00-styleguide/02-new-entity-naming-policy.md` — полная политика именования
- `docs/00-styleguide/03-python-code-style.md` — стиль Python кода
- `docs/00-styleguide/10-documentation-standards.md` — стандарты документации