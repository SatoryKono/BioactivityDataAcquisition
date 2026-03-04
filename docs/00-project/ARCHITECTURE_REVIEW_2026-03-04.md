# BioETL Architecture Review & Refactoring Plan

**Дата:** 2026-03-04
**Версия проекта:** 6.0.0
**Масштаб:** 699 файлов Python, ~134K строк кода (src/), 726 тестов

---

## 1. Числовая оценка по 10 категориям

### 1.1 Сводная таблица

| # | Категория | Описание | Вес | Оценка (1–10) | Взвешенный балл |
|---|-----------|----------|-----|:-------------:|:--------------:|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal/Ports&Adapters, изоляция domain/application/infrastructure/composition/interfaces | 0.15 | **9.0** | 1.35 |
| 2 | **Модульность и связность** | Cohesion модулей, coupling между ними, отсутствие god objects | 0.12 | **7.0** | 0.84 |
| 3 | **Качество доменной модели** | DDD-паттерны (Entities, Value Objects, Aggregates, Ports), чистота domain | 0.12 | **8.5** | 1.02 |
| 4 | **Тестирование** | Покрытие, архитектурные тесты, VCR, типы тестов (unit/integration/e2e/contract) | 0.12 | **9.0** | 1.08 |
| 5 | **Обработка ошибок** | Иерархия исключений, классификация, восстановимость, error boundaries | 0.08 | **8.5** | 0.68 |
| 6 | **Логирование и наблюдаемость** | Structured logging, метрики (Prometheus), трейсинг (OpenTelemetry), health checks | 0.08 | **8.0** | 0.64 |
| 7 | **Производительность** | Async I/O, batching, connection pooling, circuit breaker, retry | 0.08 | **7.5** | 0.60 |
| 8 | **Безопасность** | PII hashing, secret management, input validation, dependency audit | 0.07 | **8.0** | 0.56 |
| 9 | **Качество документации** | ADR, README, CHANGELOG, docstrings, guides, governance | 0.08 | **8.5** | 0.68 |
| 10 | **Технический долг и сопровождаемость** | Naming conventions, type safety, linting, CI/CD, maintainability | 0.10 | **7.5** | 0.75 |
| | | | **1.00** | | **8.20** |

### 1.2 Интерпретация общего балла

| Диапазон | Интерпретация |
|----------|---------------|
| 0.0 – 4.9 | Критическое состояние — требуется переписывание |
| 5.0 – 7.9 | Удовлетворительно — значительный рефакторинг необходим |
| **8.0 – 10.0** | **Хорошее состояние — точечные улучшения** |

**Общий балл: 8.20 / 10.0** — проект находится в хорошем архитектурном состоянии. Основные принципы Hexagonal Architecture, DDD и Clean Architecture соблюдаются. Слоистость строго контролируется import-linter и 634 архитектурными тестами. Основные области для улучшения — модульность крупных компонентов и управление техническим долгом.

---

## 2. Детальная оценка по категориям

### 2.1 Архитектура слоёв — 9.0/10

**Что оценивается:** Соблюдение 5-слойной архитектуры (domain → application → infrastructure → composition → interfaces), направление зависимостей, изоляция слоёв.

**Сильные стороны:**
- **Ноль нарушений импорта** между слоями — подтверждено grep-сканированием и `.importlinter` конфигурацией с 5 контрактами
- Чёткая структура: `domain/` (211 файлов, 41K LOC), `application/` (171, 37K), `infrastructure/` (205, 38K), `composition/` (77, 13K), `interfaces/` (33, 5K)
- 52 Port-протокола в `domain/ports/`, 51 из которых `@runtime_checkable`
- Все порты импортируются через фасад `bioetl.domain.ports` (242 импорта), **ни одного** прямого импорта из внутренних модулей
- `composition/` корректно изолирует factory/assembly логику
- Delta Lake используется для Silver слоя (нет raw parquet нарушений)

**Недостатки:**
- 1 класс без стандартного суффикса: `LockManager` в application (minor)
- Некоторые файлы в infrastructure/adapters не имеют явного `health_check()` (health_check_mixin существует, но не все клиенты его используют)

### 2.2 Модульность и связность — 7.0/10

**Что оценивается:** Размер модулей, количество ответственностей в классе, coupling между компонентами.

**Сильные стороны:**
- Активное использование Mixin-паттерна для декомпозиции (bronze_writer → 4 mixin, silver_writer → 5 mixin, gold_writer → 3 mixin)
- Чёткое разделение extractors (отдельные модули по provider)
- Хорошая декомпозиция composition на factories, providers, bootstrap

**Проблемы:**
- **32 файла > 500 строк**, крупнейшие:
  - `debt_scorecard_validation.py` (952 строк) — потенциальный god object
  - `metadata.py` (862 строк) — модель с большим количеством полей
  - `gold/chembl.py` (833 строк) — контракт с множеством правил
- **data_normalization_service.py** (36 методов, 473 строки) — god service, слишком много ответственностей (DOI, PMID, authors, dates, HTML, OA status)
- **pipeline_run.py** (32 метода, 585 строк) — aggregate с множеством состояний
- 6 transformer файлов с потенциально дублирующейся логикой (crossref, openalex, pubchem, pubmed, semanticscholar, uniprot)

### 2.3 Качество доменной модели — 8.5/10

**Что оценивается:** Применение DDD-паттернов, чистота domain, выразительность модели.

**Сильные стороны:**
- Чётко выделены `entities/`, `value_objects/`, `aggregates/`, `services/`, `ports/`, `exceptions/`
- Развитая система value objects: `chemical.py` (599 LOC), `dq_report.py` (603 LOC), `activity_values.py`
- Агрегаты: `pipeline_run.py`, `batch.py`, `quarantine_entry.py` — бизнес-инварианты защищены
- Domain services: нормализация данных, identity, unit conversion, DQ metrics — бизнес-логика без I/O
- Развитая система contracts в `domain/contracts/gold/` — валидационные правила для Gold слоя
- Schemas организованы по провайдерам: chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot
- 52 Port-протокола покрывают все интеграционные точки

**Недостатки:**
- `domain/mapping/generated/` содержит сгенерированные данные (570 строк в publication_type_classification_data.py) — лучше в конфигурации
- Некоторые value objects чрезмерно велики (chemical.py — 31 метод)
- Pydantic BaseModel используется в `domain/models/metadata.py` (862 LOC) — тяжёлая внешняя зависимость в domain layer

### 2.4 Тестирование — 9.0/10

**Что оценивается:** Покрытие, типы тестов, тестовая инфраструктура.

**Сильные стороны:**
- **726 тестовых файлов**: 504 unit, 56 integration, 88 architecture, 26 e2e
- **634 архитектурных теста** — проверка import boundaries, naming, antipatterns, formatting, security
- **178 VCR cassettes** для всех 7 провайдеров (chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot)
- Contract tests для silver/gold schemas с snapshot-тестированием (syrupy)
- Benchmark tests, property-based testing (Hypothesis)
- 9 conftest файлов — хорошо структурированные фикстуры
- Import-linter (5 контрактов) + mypy strict + ruff — тройная проверка
- 25+ CI workflows (architecture, contract-tests, mutation-testing, security, type-checking, и др.)

**Недостатки:**
- Отсутствие явного порога coverage в конфигурации (в RULES.md упоминается 85%, но `--cov-fail-under` не виден в pyproject.toml)
- Mutation testing настроен, но неизвестна текущая метрика mutation score

### 2.5 Обработка ошибок — 8.5/10

**Что оценивается:** Иерархия исключений, error classification, recovery patterns.

**Сильные стороны:**
- Развитая иерархия: `base.py` → `RecoverableError` / `CriticalError` → конкретные ошибки
- 6 модулей исключений: base, network, internal, data_quality, infrastructure, validation
- `ErrorClassifier` — автоматическая классификация ошибок
- Отдельные network-ошибки: `NetworkError`, `TimeoutError`, `RateLimitError`, `CircuitBreakerOpenError`, `RetryExhaustedError`
- Internal errors: `InvalidStateError`, `PolicyViolationError`, `LockLostError`, `CheckpointConflictError`
- Error handling adapter (592 строки) — централизованная обработка ошибок

**Недостатки:**
- `infrastructure.py` в domain/exceptions/ (589 строк) — infrastructure-специфичные исключения в domain (семантическое несоответствие, хотя технически допустимо)
- Некоторая избыточность: `RateLimitError` и `RateLimitExceededError` — два класса для похожих ситуаций

### 2.6 Логирование и наблюдаемость — 8.0/10

**Что оценивается:** Structured logging, метрики, трейсинг, health checks.

**Сильные стороны:**
- **LoggerPort** в domain — абстракция над structlog, ноль прямых import structlog в application/interfaces
- **Prometheus метрики** (prometheus-client) — Histogram, Counter, Gauge
- **OpenTelemetry трейсинг** (опциональный: opentelemetry-api/sdk/exporter-otlp)
- `infrastructure/observability/` — полный observability stack (logging, metrics, tracing, anomaly detection)
- `application/observability/` — observer pattern, span helpers
- Health check mixin для адаптеров
- `HealthCheckPort`, `HealthStatePort`, `HealthMonitorPort` — 3 порта для health checking
- NoOp logger implementation (Null Object Pattern)

**Недостатки:**
- Не все HTTP-адаптеры реализуют health_check (только через mixin)
- Anomaly detection — в infrastructure/observability/anomaly/ — потенциально incomplete

### 2.7 Производительность — 7.5/10

**Что оценивается:** Async patterns, batching, resilience patterns.

**Сильные стороны:**
- **189 файлов** с async/await — полноценный async I/O
- Batch processing — 142 файла с batching логикой
- Circuit breaker implementation (`infrastructure/adapters/decorators/circuit_breaker.py`)
- Retry с exponential backoff (`infrastructure/adapters/decorators/retry.py`)
- Delta Lake для Silver (ACID операции)
- orjson для быстрой JSON сериализации
- Benchmark тесты для performance regression detection

**Недостатки:**
- Memory monitoring (`system/memory_monitor.py`) — есть, но неизвестна степень интеграции
- Отсутствие явного connection pooling для HTTP (httpx имеет встроенный, но нет explicit config)
- Нет явного механизма backpressure при больших объёмах данных

### 2.8 Безопасность — 8.0/10

**Что оценивается:** Secret management, PII handling, input validation, dependency scanning.

**Сильные стороны:**
- **PII hashing** через `PiiHasherPort` + `infrastructure/security/pii_hasher.py`
- **Zero hardcoded secrets** в production code
- **Zero print statements** в production code
- Security CI workflow с osv-scanner + pip-audit
- detect-secrets в dev dependencies
- VCR cassettes санитизация (before_record callbacks)
- Input validation через pandera schemas

**Недостатки:**
- `infrastructure/security/` содержит только `pii_hasher.py` — минимальный security слой
- Отсутствие SAST (Static Application Security Testing) в CI помимо detect-secrets

### 2.9 Качество документации — 8.5/10

**Что оценивается:** ADR, guides, reference docs, docstrings, governance.

**Сильные стороны:**
- **45 ADR** (Architecture Decision Records) — одна из лучших практик
- Структурированная документация: `00-project/`, `01-requirements/`, `02-architecture/`, `03-guides/`, `04-reference/`
- CHANGELOG.md — 57K строк, детальная история изменений
- README.md — 403 строк
- Mermaid-диаграммы + diagram descriptions
- Governance документация
- Skills-файлы для Claude Code — автоматизация workflow

**Недостатки:**
- Некоторые docs могут быть не синхронизированы с кодом (drift risk)
- Нет автоматической проверки docstring coverage

### 2.10 Технический долг и сопровождаемость — 7.5/10

**Что оценивается:** Naming conventions, type safety, CI/CD maturity, code smells.

**Сильные стороны:**
- **mypy --strict** — максимально строгая типизация
- 25+ CI/CD workflows — mutation testing, import linter, type checking, security
- Consistent naming conventions (проверяется архитектурными тестами)
- py.typed marker — типизация для потребителей пакета
- ruff для форматирования (заменяет black + isort)

**Недостатки:**
- **385 использований `Any`** — при строгой типизации это заметный debt
- **32 файла > 500 строк** — large file smell
- `data_normalization_service.py` (36 методов) — явный кандидат на декомпозицию
- Потенциальное дублирование логики в 6 transformer-файлах по провайдерам
- `debt_scorecard_validation.py` (952 строки) — самый крупный файл, сложно поддерживать

---

## 3. Архитектурная оценка

### 3.1 Соблюдение слоистой структуры

**Статус: ОТЛИЧНО (9/10)**

```
interfaces (33 файла, 5K LOC)
    ↓ depends on
composition (77 файлов, 13K LOC)
    ↓ depends on
application (171 файл, 37K LOC) + infrastructure (205 файлов, 38K LOC)
    ↓ depends on                   ↓ depends on
domain (211 файлов, 41K LOC) ←←←←←←←←←←←←←←←←←↙
```

- Import-linter с 5 контрактами гарантирует направление зависимостей
- **Ноль runtime-нарушений** — проект проходит все boundary checks
- Composition Root корректно изолирует assembly от business logic
- Interfaces содержат CLI (Click), HTTP, orchestration — всё в правильном слое

### 3.2 Ports & Adapters (Hexagonal Architecture)

**Статус: ОТЛИЧНО (9/10)**

- **52 Port-протокола** покрывают: data sources, storage, locking, health check, observability, serialization, filtering, checkpoint, resilience, PII, validation, config loading, shutdown, и др.
- **51 из 52** портов `@runtime_checkable` — boundary validation на уровне типов
- Adapters в `infrastructure/adapters/` по 7 провайдерам + common + http + decorators
- Storage adapters: bronze/silver/gold writers через Delta Lake
- Чёткое разделение: Port (domain) → Adapter (infrastructure) → Factory (composition)

### 3.3 DDD Implementation

**Статус: ХОРОШО (8.5/10)**

| DDD-паттерн | Реализация | Качество |
|-------------|------------|----------|
| Entities | `domain/entities/` по провайдерам | Хорошо |
| Value Objects | `domain/value_objects/` — chemical, activity, DQ report | Хорошо |
| Aggregates | `pipeline_run`, `batch`, `quarantine_entry` | Хорошо |
| Domain Services | normalization, identity, DQ metrics, unit converter | Средне (god service) |
| Ports (Interfaces) | 52 Protocol-порта | Отлично |
| Domain Events | `PipelineCompleted`, `BatchCreated`, `BatchSealed`, `BatchWritten`, `RecordQuarantined` и др. — 11 событий в `aggregates/events.py` | Отлично |
| Specifications | `domain/contracts/gold/` — валидационные правила | Хорошо |
| Repository | Через StoragePort/DeltaReaderPort | Хорошо |

### 3.4 Границы модулей и зависимости

**Статус: ХОРОШО (8/10)**

- Чёткие границы между providers (chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot)
- Каждый provider имеет: client (infra) + transformer (app) + entities (domain) + schemas (domain)
- Composition factories организованы по ответственностям: pipeline, storage, DQ, services, transformer
- Config schemas в `infrastructure/schemas/` — валидация YAML конфигурации

---

## 4. Основные проблемы

### P-001: God Service — data_normalization_service.py (HIGH)
- **Описание:** 36 методов, 473 строки. Нормализация DOI, PMID, authors, dates, HTML, OA status — всё в одном сервисе
- **Влияние:** Сложность поддержки, сложность тестирования изолированных частей, нарушение SRP

### P-002: Крупные файлы (32 файла > 500 LOC) (MEDIUM)
- **Описание:** Крупнейшие: debt_scorecard_validation (952), metadata (862), gold/chembl (833)
- **Влияние:** Сложность code review, увеличение cognitive load, замедление разработки

### P-003: Высокий Any-budget (385 использований) (MEDIUM)
- **Описание:** При mypy --strict режиме 385 `Any` — значительный type-safety debt
- **Влияние:** Снижение гарантий типов, потенциальные runtime ошибки

### P-004: Потенциальное дублирование в transformers (MEDIUM)
- **Описание:** 6 transformer файлов по провайдерам с похожими паттернами (общий суммарный объём ~2,300 строк)
- **Влияние:** Изменение общей логики требует правок в 6 местах

### P-005: Pydantic в Domain Layer (LOW)
- **Описание:** `domain/models/metadata.py` (862 LOC) использует Pydantic BaseModel — тяжёлая внешняя зависимость в чистом domain
- **Влияние:** Ослабляет domain purity, затрудняет замену Pydantic

### P-006: Infrastructure exceptions в domain (LOW)
- **Описание:** `domain/exceptions/infrastructure.py` (589 строк) — семантическое несоответствие
- **Влияние:** Confusing naming, хотя технически допустимо

### P-007: Неполный health_check coverage (LOW)
- **Описание:** Не все HTTP-клиенты реализуют health_check напрямую
- **Влияние:** Неполный мониторинг здоровья внешних сервисов

### P-008: Сгенерированные данные в domain (LOW)
- **Описание:** `domain/mapping/generated/` содержит classification data (570 строк)
- **Влияние:** Данные в коде вместо конфигурации, усложняет обновление

---

## 5. План рефакторинга

### RF-001: Декомпозиция DataNormalizationService (HIGH PRIORITY)

**Цель:** Разбить god service (36 методов) на специализированные сервисы по SRP.

**Конкретные правки:**
| Новый сервис | Методы | Файл |
|-------------|--------|------|
| `DoiNormalizationService` | `normalize_doi`, `_strip_doi_prefix` | `domain/services/doi_normalization.py` |
| `PmidNormalizationService` | `normalize_pmid`, `_pmid_to_string`, `_validate_pmid_string` | `domain/services/pmid_normalization.py` |
| `AuthorNormalizationService` | `normalize_authors`, `parse_authors_to_list`, `_parse_*` (8 методов) | Уже существует `author_normalization_service.py` — мигрировать |
| `DateNormalizationService` | `normalize_year`, `normalize_partial_date` | `domain/services/date_normalization.py` |
| `TextNormalizationService` | `strip_html_tags`, `normalize_string`, `normalize_to_string`, `normalize_oa_status` | `domain/services/text_normalization.py` |

**Оставить** в `DataNormalizationService` только фасад, делегирующий вызовы специализированным сервисам.

**Риски:** Множество мест использования → регрессия в transformer-ах.
**Минимизация:**
- Сохранить фасад с backward-compatible API
- Baseline тесты перед рефакторингом
- Инъекция новых сервисов через `DataNormalizationPort`

**Критерии готовности:**
- [ ] Каждый новый сервис ≤ 100 строк
- [ ] Все тесты проходят
- [ ] Фасад делегирует, не содержит логики
- [ ] mypy --strict проходит

---

### RF-002: Уменьшение Any-budget (MEDIUM PRIORITY)

**Цель:** Снизить 385 использований `Any` до < 200, повысив type safety.

**Конкретные правки:**
1. **Аудит** — классифицировать все 385 вхождений:
   - `Any` из-за внешних API (JSON) → заменить на `dict[str, object]` или `JsonDict`
   - `Any` из-за отсутствия типов → добавить корректные типы
   - `Any` оправданный (external untyped) → оставить с комментарием
2. **Ввести type alias** `JsonDict = dict[str, Any]` в `domain/types.py` для уменьшения визуального долга
3. **Приоритизировать** domain (41K LOC) → application (37K LOC) → infrastructure

**Риски:** Breaking changes при изменении сигнатур.
**Минимизация:** Изменять поэтапно по модулям, каждый этап с mypy check.

**Критерии готовности:**
- [ ] Any usage < 200
- [ ] Каждый оставшийся Any имеет комментарий
- [ ] mypy --strict проходит

---

### RF-003: Декомпозиция крупных файлов (MEDIUM PRIORITY)

**Цель:** Разбить файлы > 700 строк на логические модули.

**Приоритетный список:**

| Файл | LOC | Стратегия |
|------|-----|-----------|
| `debt_scorecard_validation.py` | 952 | Выделить validators по категориям (naming, arch, types) |
| `metadata.py` | 862 | Выделить MetadataBuilder, MetadataSerializer |
| `gold/chembl.py` | 833 | Разделить по entity type (compound, activity, mechanism, target) |
| `chembl/models.py` | 711 | Разделить по entity type |
| `debt_scorecard.py` | 704 | Выделить отдельные scorecard sections |
| `entities/chembl.py` | 696 | Разделить compound/activity/mechanism/target entities |

**Риски:** Множество импортов нужно обновить.
**Минимизация:** Re-export из __init__.py для backward compatibility.

**Критерии готовности:**
- [ ] Ни один файл не превышает 600 строк
- [ ] Все тесты проходят
- [ ] Import linter проходит

---

### RF-004: Унификация Transformer-логики (MEDIUM PRIORITY)

**Цель:** Вынести общие паттерны из 6 provider-transformers в base_transformer.

**Конкретные правки:**
1. **Провести аудит** 6 transformers (crossref, openalex, pubchem, pubmed, semanticscholar, uniprot) на общие паттерны
2. **Вынести** общие методы в `base_transformer.py` (уже 634 строки — использовать mixin-подход)
3. **Создать** Transformer mixins по категориям:
   - `AuthorTransformMixin` — нормализация авторов
   - `DateTransformMixin` — парсинг дат
   - `IdentifierTransformMixin` — DOI/PMID/etc.

**Риски:** Каждый transformer специфичен к API провайдера.
**Минимизация:** Только общие паттерны; provider-specific логика остаётся.

**Критерии готовности:**
- [ ] Повторяющийся код сокращён на > 30%
- [ ] Все contract/snapshot тесты проходят
- [ ] base_transformer не увеличился > 400 строк

---

### RF-005: Реорганизация domain/exceptions (LOW PRIORITY)

**Цель:** Устранить семантическое несоответствие `infrastructure.py` в domain exceptions.

**Конкретные правки:**
1. Переименовать `domain/exceptions/infrastructure.py` → `domain/exceptions/external_service.py`
2. Перегруппировать исключения:
   - `network.py` — сетевые ошибки (оставить)
   - `external_service.py` — ошибки внешних сервисов
   - `internal.py` — внутренние ошибки (оставить)
   - `data_quality.py` — ошибки качества данных (оставить)
   - `validation.py` — ошибки валидации (оставить)
3. Устранить дублирование: `RateLimitError` vs `RateLimitExceededError`

**Риски:** Множество ссылок на эти классы по кодовой базе.
**Минимизация:** Re-export старых имён из __init__.py с DeprecationWarning.

**Критерии готовности:**
- [ ] Нет файлов с naming confusion
- [ ] Все тесты проходят
- [ ] Устранено дублирование exception классов

---

### RF-006: Расширение @runtime_checkable (NICE TO HAVE)

**Цель:** Расширить применение `@runtime_checkable` для критичных портов (TYPE-004).

**Текущее состояние:** 51/52 портов имеют `@runtime_checkable`, но некоторые критичные порты (StoragePort, CheckpointPort) могут быть дополнительно проверены в runtime при boundary validation.

**Конкретные правки:**
1. Аудит всех портов — определить, какие используются в `isinstance()` проверках
2. Добавить `@runtime_checkable` для отсутствующего порта
3. Добавить boundary validation в composition factories: `assert isinstance(adapter, DataSourcePort)`

**Риски:** Минимальные — добавление декоратора не ломает существующий код.
**Минимизация:** Только декоратор + assert в factories.

**Критерии готовности:**
- [ ] 52/52 портов имеют `@runtime_checkable`
- [ ] Boundary assertions в 5+ factory методов
- [ ] Тесты покрывают boundary validation

---

### RF-007: Health Check Coverage (LOW PRIORITY)

**Цель:** Обеспечить health_check для всех HTTP-адаптеров.

**Конкретные правки:**
1. Применить `HealthCheckMixin` ко всем client.py файлам:
   - `chembl/client.py`
   - `crossref/client.py`
   - `openalex/client.py`
   - `pubchem/client.py`
   - `pubmed/pubmed_client.py`
   - `semanticscholar/client.py` (если есть)
   - `uniprot/client.py`
2. Добавить health_check endpoint в CLI (`bioetl health`)

**Риски:** Минимальные.
**Минимизация:** Mixin уже существует, нужна только интеграция.

**Критерии готовности:**
- [ ] Все 7 provider clients реализуют health_check
- [ ] CLI команда `bioetl health` доступна
- [ ] Integration тесты для health checks

---

### RF-008: Вынос сгенерированных данных из domain (NICE TO HAVE)

**Цель:** Перенести classification data из `domain/mapping/generated/` в конфигурацию.

**Конкретные правки:**
1. Вынести `publication_type_classification_data.py` (570 строк) в YAML-конфиг `configs/entities/`
2. Создать loader в infrastructure для загрузки classification data
3. Инжектировать через Port в domain services

**Риски:** Изменение точки загрузки данных.
**Минимизация:** Fallback на embedded data при отсутствии конфига.

**Критерии готовности:**
- [ ] Данные в YAML-конфиге
- [ ] Domain не содержит generated data > 100 строк
- [ ] Тесты проходят

---

## 6. Приоритизированная дорожная карта

| Фаза | Шаги | Ожидаемое влияние на балл |
|------|-------|--------------------------|
| **Фаза 1** (Quick wins) | RF-001 (god service), RF-007 (health checks) | Модульность +0.5, Наблюдаемость +0.3 |
| **Фаза 2** (Type safety) | RF-002 (Any-budget) | Тех.долг +0.5 |
| **Фаза 3** (Code structure) | RF-003 (large files), RF-004 (transformer unification) | Модульность +0.8, Тех.долг +0.3 |
| **Фаза 4** (Polish) | RF-005 (exceptions), RF-008 (generated data) | Домен +0.2, Модульность +0.2 |
| **Фаза 5** (Polish) | RF-006 (runtime_checkable) | Домен +0.1, Архитектура +0.1 |

### Прогнозируемое изменение балла

| Категория | Текущий | После Фазы 1–2 | После Фазы 3–4 | После Фазы 5 |
|-----------|:-------:|:---------------:|:---------------:|:------------:|
| Архитектура слоёв | 9.0 | 9.0 | 9.0 | 9.1 |
| Модульность | 7.0 | 7.5 | 8.5 | 8.5 |
| Доменная модель | 8.5 | 8.5 | 8.7 | 8.8 |
| Тестирование | 9.0 | 9.0 | 9.0 | 9.0 |
| Обработка ошибок | 8.5 | 8.5 | 8.7 | 8.7 |
| Наблюдаемость | 8.0 | 8.3 | 8.3 | 8.3 |
| Производительность | 7.5 | 7.5 | 7.5 | 7.5 |
| Безопасность | 8.0 | 8.0 | 8.0 | 8.0 |
| Документация | 8.5 | 8.5 | 8.5 | 8.5 |
| Тех.долг | 7.5 | 8.0 | 8.5 | 8.5 |
| **Итого** | **8.20** | **8.43** | **8.72** | **8.77** |

---

## 7. Метрики и тесты для контроля качества

### 7.1 Рекомендуемые метрики

| Метрика | Текущее значение | Целевое | Связь с категориями |
|---------|:----------------:|:-------:|:-------------------:|
| Import violations (import-linter) | 0 | 0 | Архитектура |
| Architecture test count | 634 | 650+ | Архитектура, Тестирование |
| Files > 500 LOC | 32 | < 15 | Модульность |
| Max methods per class | 36 | < 20 | Модульность |
| Any usage count | 385 | < 200 | Тех.долг |
| Port count (runtime_checkable) | 51/52 | 52/52 | Доменная модель |
| VCR cassettes | 178 | 200+ | Тестирование |
| Exception hierarchy depth | 3 | 3 | Обработка ошибок |
| Health check coverage | ~60% | 100% | Наблюдаемость |
| Hardcoded secrets | 0 | 0 | Безопасность |
| CI workflow count | 25 | 25+ | Тех.долг |
| ADR count | 45 | 45+ | Документация |

### 7.2 Новые тесты для добавления

1. **test_max_file_size.py** — ни один .py файл не превышает 600 строк (после RF-003)
2. **test_max_methods_per_class.py** — ни один класс не имеет > 20 публичных методов
3. **test_any_budget.py** — если уже существует, обновить порог до < 200
4. **test_health_check_coverage.py** — все HTTP-client классы реализуют health_check
5. **test_coverage_threshold.py** — coverage ≥ 85% (добавить `--cov-fail-under=85` в CI)
6. **test_exception_uniqueness.py** — нет дублирующихся exception классов
7. **test_domain_no_generated_data.py** — domain/mapping/generated/ не превышает порог

### 7.3 Связь метрик с интегральным баллом

Формула автоматического пересчёта:

```
score = Σ(weight_i × category_score_i)

where category_score_i = max(1, 10 - deductions_i)
  deductions_i = Σ(severity_j × count_j)
```

| Метрика | При нарушении | Влияние на категорию | Вес |
|---------|:-------------:|:--------------------:|:---:|
| Import violation | -2.0 per violation | Архитектура | 0.15 |
| File > 500 LOC | -0.1 per file | Модульность | 0.12 |
| Class > 20 methods | -0.3 per class | Модульность | 0.12 |
| Any > 200 | -0.01 per excess Any | Тех.долг | 0.10 |
| Missing health_check | -0.5 per adapter | Наблюдаемость | 0.08 |
| Coverage < 85% | -1.0 per 5% below | Тестирование | 0.12 |

---

## 8. Заключение

BioETL v6.0.0 — зрелый проект с **отличной архитектурной дисциплиной** (интегральный балл 8.20/10). Ключевые достижения:

- **Безупречная слоистость** — ноль import-нарушений, 5 import-linter контрактов
- **Развитая система портов** — 52 протокола, 51 runtime-checkable
- **Впечатляющее тестирование** — 634 архитектурных теста, 178 VCR cassettes, mutation testing
- **Строгая типизация** — mypy --strict, 25+ CI workflows

Основные зоны роста — **модульность** (декомпозиция god objects, уменьшение размера файлов) и **type safety** (снижение Any-бюджета). Реализация Фаз 1–3 плана рефакторинга поднимет интегральный балл до **~8.72/10**.
