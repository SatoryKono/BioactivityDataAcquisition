# BioETL Documentation Index

*Версия документации: 5.10 (2026-01-07)*

Этот документ — навигационный центр проекта BioETL. Все ключевые ресурсы структурированы по категориям.

---

## Для быстрого старта

| Документ | Описание |
|----------|----------|
| [Quick Reference](quick-reference/rules-summary.md) | Выжимка ключевых правил |
| [Quick Start Guide](03-guides/quick-start.md) | Быстрый старт с BioETL |
| [Getting Started](03-guides/getting-started.md) | Полное руководство по началу работы |
| [Glossary](glossary.md) | Глоссарий терминов (Ubiquitous Language) |

---

## Конституция проекта (SSOT)

| Документ | Описание |
|----------|----------|
| **[RULES.md](RULES.md)** | **Single Source of Truth** — полные правила проекта |
| [REQUIREMENTS.md](REQUIREMENTS.md) | 127 тестируемых требований |

> **Note**: `RULES.md` — канонический источник правил. Все остальные документы являются производными или детализациями.

---

## Архитектура

### Обзор слоёв

| Документ | Описание |
|----------|----------|
| [System Context](02-architecture/system-context.md) | Высокоуровневая диаграмма системы |
| [Container Diagram](02-architecture/container-diagram.md) | Диаграмма контейнеров |
| [Data Flow](02-architecture/data-flow.md) | Потоки данных в системе |
| [Data Layers](02-architecture/data-layers.md) | Medallion Architecture детали |

### Слои приложения

| Слой | Документ | Описание |
|------|----------|----------|
| Domain | [01-domain-layer.md](02-architecture/01-domain-layer.md) | Чистая логика, Protocols (Ports) |
| Application | [02-application-layer.md](02-architecture/02-application-layer.md) | Пайплайны, Use Cases |
| Infrastructure | [03-infrastructure-layer.md](02-architecture/03-infrastructure-layer.md) | Адаптеры, HTTP клиенты |
| Interfaces | [04-interfaces-layer.md](02-architecture/04-interfaces-layer.md) | CLI |
| Composition | [05-composition-layer.md](02-architecture/05-composition-layer.md) | DI-контейнер, Bootstrap |

### Архитектурные решения (ADR)

| ADR | Название | Описание |
|-----|----------|----------|
| [ADR-001](02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | Выбор Delta Lake для ACID |
| [ADR-002](02-architecture/decisions/ADR-002-medallion-architecture.md) | Medallion Architecture | Bronze/Silver/Gold уровни |
| [ADR-003](02-architecture/decisions/ADR-003-in-memory-locking-strategy.md) | In-Memory Locking | MemoryLock для локального запуска |
| [ADR-004](02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md) | Pydantic vs Dataclasses | Dataclasses для domain |
| [ADR-005](02-architecture/decisions/ADR-005-composition-layer-separation.md) | Composition Layer | Отделение DI от бизнес-логики |
| [ADR-007](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker | Защита от каскадных сбоев |
| [ADR-008](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown | Корректное завершение |
| [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md) | Local-Only Deployment | Локальная архитектура |
| [ADR-016](02-architecture/decisions/ADR-016-error-handling-strategy.md) | Error Handling Strategy | Стратегия обработки ошибок |
| [ADR-017](02-architecture/decisions/ADR-017-observability-architecture.md) | Observability Architecture | Архитектура observability |
| [ADR-018](02-architecture/decisions/ADR-018-gold-strict-validation.md) | Gold Strict Validation | Строгая валидация Gold |
| [ADR-020](02-architecture/decisions/ADR-020-basepipeline-decomposition.md) | BasePipeline Decomposition | Декомпозиция BasePipeline |
| [ADR-021](02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md) | DDD Aggregates Adoption | DDD агрегаты |

[Полный список ADR](02-architecture/decisions/README.md)

---

## Руководства (How-To)

| Документ | Описание |
|----------|----------|
| [Добавление нового источника](03-guides/add-new-source.md) | Подключение нового провайдера |
| [Добавление пайплайна](03-guides/add-pipeline-existing-source.md) | Пайплайн для существующего источника |
| [Запуск пайплайнов](03-guides/running-pipelines.md) | CLI команды и опции |
| [Pipeline Lifecycle](03-guides/pipeline-lifecycle.md) | Жизненный цикл пайплайна |
| [Registry Pattern](03-guides/registry-pattern.md) | Паттерн реестра пайплайнов |
| [Local Storage Layout](03-guides/local-storage-layout.md) | Структура локального хранилища |
| [Тестирование](03-guides/testing.md) | Unit, Integration, E2E тесты |
| [Troubleshooting](03-guides/troubleshooting.md) | Решение проблем |
| [Cleanup Policy](03-guides/cleanup-policy.md) | Политика очистки данных |

---

## Провайдеры

### ChEMBL

| Сущность | Документация |
|----------|--------------|
| Activity | [providers/chembl/activity.md](providers/chembl/activity.md) |
| Assay | [providers/chembl/assay.md](providers/chembl/assay.md) |
| Molecule | [providers/chembl/molecule.md](providers/chembl/molecule.md) |
| Target | [providers/chembl/target.md](providers/chembl/target.md) |
| Document | [providers/chembl/document.md](providers/chembl/document.md) |

### Другие провайдеры

| Провайдер | Сущность | Документация |
|-----------|----------|--------------|
| PubChem | Compound | [providers/pubchem/compound.md](providers/pubchem/compound.md) |
| UniProt | Protein | [providers/uniprot/protein.md](providers/uniprot/protein.md) |
| PubMed | Publication | [providers/pubmed/publication.md](providers/pubmed/publication.md) |
| OpenAlex | Publication | [providers/openalex/publication.md](providers/openalex/publication.md) |
| CrossRef | Publication | [providers/crossref/publication.md](providers/crossref/publication.md) |
| Semantic Scholar | Publication | [providers/semanticscholar/publication.md](providers/semanticscholar/publication.md) |

---

## API Reference

| Модуль | Документация |
|--------|--------------|
| Domain | [04-reference/api/domain.md](04-reference/api/domain.md) |
| Application | [04-reference/api/application.md](04-reference/api/application.md) |
| Infrastructure | [04-reference/api/infrastructure.md](04-reference/api/infrastructure.md) |
| Composition | [04-reference/api/composition.md](04-reference/api/composition.md) |
| CLI | [04-reference/cli.md](04-reference/cli.md) |

---

## Контракты данных

| Документ | Описание |
|----------|----------|
| [Observability Contracts](contracts/observability.md) | Контракты метрик и трейсинга |
| Gold Schemas | `docs/contracts/gold/` — JSON Schema для Gold-таблиц |

---

## Операции

| Документ | Описание |
|----------|----------|
| [Operations Guide](05-operations/) | Операционные руководства |

---

## Шаблоны

| Шаблон | Описание |
|--------|----------|
| [Pipeline Review Checklist](templates/pipeline-review-checklist.md) | Чеклист для ревью пайплайнов |

---

## Карта проекта

Для полной карты проекта см. [00-map.md](00-map.md).

---

## IDE-специфичные правила

| IDE | Файл |
|-----|------|
| Cursor | `.cursor/rules/user-rules.md` |
| Claude Code | `CLAUDE.md` |

---

*Последнее обновление: 2026-01-07*
