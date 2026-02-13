# Консолидированный план рефакторинга BioETL

**Дата:** 2026-02-13
**Источники:** Верифицированные данные из 4 независимых аудитов (codex branches B1-B4),
консолидированных в двух ветках:
- `claude/code-inventory-duplication-audit-HsTsk` — inventory-report.md
- `claude/code-inventory-audit-eUknn` — consolidated-audit-plan.md, branch-comparison.md

**Статус:** VERIFIED — все находки перепроверены grep-поиском по актуальной кодовой базе

---

## 1. Executive Summary

| Метрика | Значение | Верификация |
|---------|----------|-------------|
| Всего объектов (classes + functions + constants) | 1626 | HIGH (4/4 ветки совпали) |
| Подтверждённые DEAD объекты | **9** | HIGH (grep-verified) |
| Name collisions (одноимённые классы) | **2** | HIGH (verified) |
| True copy-paste duplicates (идентичный код) | **3** места | HIGH (verified) |
| Delegation wrappers (намеренные) | 3 функции | Verified: NOT duplication |
| Schema↔Domain пары (архитектурные) | 5 пар | Verified: NOT duplication |
| Protocol implementations (полиморфизм) | ~264 подписи | NOT duplication |
| Cyclic dependencies | Не проанализированы | Требуется import-linter |

---

## 2. Верифицированные находки

### 2.1 Мёртвый код (9 объектов) — CONFIRMED DEAD

Все 9 объектов перепроверены: **0 ссылок** за пределами строки определения.
Ни один не входит в `__all__` ни одного модуля.

| # | Объект | Тип | Слой | Файл:Строка |
|---|--------|-----|------|-------------|
| 1 | `VALIDATION_API` | tuple const | domain | `domain/validation.py:412` |
| 2 | `compute_subcellular_fraction_entity_id` | function | application | `application/core/entity_id.py:36` |
| 3 | `PARSER_HELPERS` | tuple const | application | `application/pipelines/pubmed/xml_parser.py:79` |
| 4 | `CIRCUIT_BREAKER_HELPERS` | tuple const | infrastructure | `infrastructure/adapters/http/circuit_breaker.py:235` |
| 5 | `METRICS_COLLECTOR` | alias const | infrastructure | `infrastructure/observability/metrics.py:221` |
| 6 | `LOGGING_API` | tuple const | infrastructure | `infrastructure/observability/logging.py:52` |
| 7 | `BOOTSTRAP_LOGGER_EXPORTS` | tuple const | composition | `composition/bootstrap_logger.py:140` |
| 8 | `EXIT_CODE_HELPERS` | tuple const | interfaces | `interfaces/cli/exit_codes.py:120` |
| 9 | `RUN_HEALTH_SERVER` | alias const | interfaces | `interfaces/http/health_server.py:305` |

**Паттерн:** 7 из 9 — это tuple-константы вида `FOO_HELPERS = (func1, func2)`,
созданные для «экспорта» но нигде не используемые. 2 — alias-присвоения (`NAME = Class`).

### 2.2 Name Collisions (2 коллизии) — CONFIRMED

| # | Имя | Файл A | Файл B | Различия | Рекомендация |
|---|-----|--------|--------|----------|--------------|
| 1 | `CleanupResult` | `application/core/cleanup_service.py:47` (Silver/Gold: silver_cleared, gold_cleared) | `application/services/bronze_cleanup_service.py:21` (Bronze: files_removed, bytes_freed) | Разные поля, разная семантика | Rename → `BronzeCleanupResult` |
| 2 | `RateLimitConfig` | `domain/configs/base.py:20` (requests_per_second, burst) | `composition/bootstrap_contexts.py:107` (rate, capacity) | Разные поля, разные слои | Rename → `RateLimitContext` |

### 2.3 Идентичный код (3 места дупликации) — CONFIRMED

| # | RF-ID | Что | Где | LOC | Рекомендация |
|---|-------|-----|-----|-----|--------------|
| 1 | RF-DUP-001 | `_load_yaml()` — байт-в-байт идентичный метод | `BaseConfigLoader` (line 70) и `DQConfigLoader` (line 131) | ~15 | DQConfigLoader наследует от BaseConfigLoader → удалить переопределение |
| 2 | RF-DUP-002 | `__init__()` — идентичный конструктор | `SilverMetadataBuilder` (line 185) и `GoldMetadataBuilder` (line 321) в `metadata_builder.py` | ~7×2 | Извлечь `_MetadataBuilderBase` |
| 3 | RF-DUP-003 | `get_source_metadata()` — идентичная delegation | `FilteredDataSource` (line 353), `PublicationTermDataSource` (line 574), `SubcellularFractionDataSource` (line 289) | ~6×3 | Извлечь mixin `SourceMetadataDelegationMixin` |

### 2.4 Коллизия имён в domain (1 случай) — CONFIRMED

| Имя | Файл A | Файл B | Оценка |
|-----|--------|--------|--------|
| `LineageMetadata` | `domain/composite/lineage.py:34` (frozen dataclass для composite merging) | `domain/models/metadata.py:461` (BaseModel для Medallion layers) | Разные классы, разное назначение. Rename composite версию → `CompositeLineageMetadata` |

### 2.5 Архитектурно обоснованная дупликация (_get_bioetl_version)

| Файл A | Файл B | Отличие |
|--------|--------|---------|
| `infrastructure/storage/metadata_builder.py:27` (try/except → "unknown") | `composition/services/metadata_coordinator.py:59` (пробрасывает исключение) | Разная обработка ошибок |

ARCH-001 запрещает cross-import между infrastructure и composition.
**Рекомендация:** Вынести `get_version() -> str` в `domain/version.py` — оба слоя
могут импортировать из domain.

### 2.6 НЕ дупликация (верифицировано)

| Паттерн | Примеры | Почему не дупликация |
|---------|---------|----------------------|
| Delegation wrappers | `dict_transformers.normalize_string` → `domain.normalization.normalize_string` | REFACTOR-004 backward compat |
| Schema↔Domain pairs | `DQConfig` domain ↔ infrastructure | Hexagonal Architecture boundary |
| Protocol impls | `aclose()`, `fetch()`, `health_check()` в 15+ классах | Полиморфизм (Port conformance) |
| _run_pipeline_async | `run.py` (complex + health server) vs `run_all.py` (simple wrapper) | Разные сигнатуры и назначение |

---

## 3. План рефакторинга по фазам

### Фаза 1: Quick Wins (низкий риск)

| # | ID | Действие | Файлы | Тесты |
|---|-----|----------|-------|-------|
| 1.1 | DEAD-001 | Удалить 9 DEAD объектов | 9 файлов | `pytest tests/ -x` |
| 1.2 | NAME-001 | Rename `CleanupResult` → `BronzeCleanupResult` в bronze_cleanup_service | ~4 файла + тесты | `pytest tests/ -k cleanup` |
| 1.3 | NAME-002 | Rename `RateLimitConfig` → `RateLimitContext` в composition | ~3 файла + тесты | `pytest tests/ -k rate_limit` |
| 1.4 | LINT-001 | `ruff check --select F401` — удалить unused imports | Project-wide | `ruff check src/bioetl/` |

### Фаза 2: Дедупликация кода (средний риск)

| # | ID | Действие | Файлы | Тесты |
|---|-----|----------|-------|-------|
| 2.1 | RF-DUP-001 | Удалить `_load_yaml` из DQConfigLoader (наследуется) | `dq_config_loader.py` | `pytest tests/ -k config_loader` |
| 2.2 | RF-DUP-002 | Извлечь `_MetadataBuilderBase` с общим `__init__` | `metadata_builder.py` | `pytest tests/ -k metadata_builder` |
| 2.3 | RF-DUP-003 | Извлечь mixin для `get_source_metadata` | 3 data_source файла | `pytest tests/ -k data_source` |
| 2.4 | RF-NAME-003 | Rename `LineageMetadata` → `CompositeLineageMetadata` в composite/lineage.py | `lineage.py` + imports | `pytest tests/ -k lineage` |
| 2.5 | RF-CROSS-001 | Вынести `get_version()` в `domain/version.py` | 2 файла + новый | `pytest tests/` |

### Фаза 3: Инфраструктура качества (требует планирования)

| # | ID | Действие | Результат |
|---|-----|----------|-----------|
| 3.1 | CI-001 | Настроить import-linter в CI | Защита ARCH-001 |
| 3.2 | DOC-001 | ADR для schema↔domain pair convention | Документация |
| 3.3 | VERIFY-001 | Проверить orphan module (subcellular_fraction_data_source) | Решение: keep/remove |
| 3.4 | VERIFY-002 | Проверить TEST_ONLY объекты | Baseline |
| 3.5 | ANALYSIS-001 | Cyclic dependency analysis | Архитектурная карта |

### Фаза 4: Исследование (опционально)

| # | ID | Действие | Результат |
|---|-----|----------|-----------|
| 4.1 | RF-INV-001 | Анализ cross-provider extractors | Решение о консолидации |
| 4.2 | RF-INV-002 | Аудит facade `__init__` re-exports | Оптимизация API |

---

## 4. Зависимости между задачами

```
Фаза 1 (параллельно):
  1.1 DEAD-001 ─────────────┐
  1.2 NAME-001 ──────────── ├── Фаза 2 (после успешных тестов Фазы 1)
  1.3 NAME-002 ──────────── │     2.1 RF-DUP-001 (независимо)
  1.4 LINT-001 ─────────────┘     2.2 RF-DUP-002 (независимо)
                                  2.3 RF-DUP-003 (независимо)
                                  2.4 RF-NAME-003 (независимо)
                                  2.5 RF-CROSS-001 (независимо)
                                        │
                                        ├── Фаза 3 (после Фазы 2)
                                        │     3.1 CI-001 (независимо)
                                        │     3.2 DOC-001 (независимо)
                                        │     3.3 VERIFY-001 → решение
                                        │     3.4 VERIFY-002 → решение
                                        │     3.5 ANALYSIS-001 → отчёт
                                        │
                                        └── Фаза 4 (после Фазы 3)
                                              4.1 RF-INV-001
                                              4.2 RF-INV-002
```

---

## 5. Критерии успеха

| Фаза | Критерий |
|-------|----------|
| 1 | `pytest tests/ -x` passes, `ruff check` clean, 0 DEAD objects, 0 name collisions |
| 2 | `pytest tests/ -x` passes, 0 LOC identical duplication, architecture tests pass |
| 3 | `lint-imports` clean, ADR written, all TEST_ONLY/orphan objects classified |
| 4 | Decision doc for each investigation |

---

## 6. Расхождения между отчётами и принятые решения

| Вопрос | Ветка HsTsk | Ветка eUknn | Решение |
|--------|-------------|-------------|---------|
| Количество DEAD | 5 (post-correction) | 9 | **9** — ветка eUknn нашла 4 дополнительных: LOGGING_API, BOOTSTRAP_LOGGER_EXPORTS, EXIT_CODE_HELPERS, RUN_HEALTH_SERVER |
| Confirmed duplicates | 3 (MetadataBuilder, _load_yaml, get_source_metadata) | 0 (true copy-paste) | **3 места идентичного кода** — ветка HsTsk верно идентифицировала |
| `__all__` gaps | 11 модулей | 0 (все false positive) | **0** — ветка eUknn перепроверила и опровергла все claims |
| _run_pipeline_async | Duplication (RF-DUP-010) | Not investigated | **NOT duplication** — разные сигнатуры, подтверждено grep |

---

*Следующий документ: `modification-prompts-consolidated.md` — набор промптов для выполнения каждого действия.*
