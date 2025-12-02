# Pipelines Documentation

Документация по ETL-пайплайнам и базовым компонентам BioETL.

## Core компоненты

Базовые компоненты, используемые всеми пайплайнами:

- [00 Pipeline Base](00-pipeline-base.md) — абстрактный базовый класс пайплайнов
- [01 Base External Data Client](01-base-external-data-client.md) — базовый клиент внешних API
- [02 Logging And Configuration](02-logging-and-configuration.md) — логирование и конфигурация
- [03 Unified API Client](03-unified-api-client.md) — унифицированный API-клиент
- [04 Unified Output Writer](04-unified-output-writer.md) — унифицированный writer для записи
- [05 Schema Registry](05-schema-registry.md) — реестр схем для валидации
- [06 Validation Service](06-validation-service.md) — сервис валидации данных
- [07 Client Architecture](07-client-architecture.md) — архитектура клиентского слоя

## Пайплайны по провайдерам

### ChEMBL

Полная документация: [chembl/INDEX.md](chembl/INDEX.md)

- [Activity Pipeline](chembl/activity/INDEX.md) — пайплайн биоактивности
- [Assay Pipeline](chembl/assay/INDEX.md) — пайплайн ассаев
- [Target Pipeline](chembl/target/00-target-chembl-overview.md) — пайплайн таргетов
- [Document Pipeline](chembl/document/00-document-chembl-overview.md) — пайплайн документов
- [TestItem Pipeline](chembl/testitem/INDEX.md) — пайплайн тестовых элементов

### Общие компоненты ChEMBL

Документация: [chembl/common/](chembl/common/)

## Клиенты внешних API

Документация: [clients/](clients/)

- [00 PubMed Client](clients/00-pubmed-client.md)
- [01 Crossref Client](clients/01-crossref-client.md)
- [02 PubChem Client](clients/02-pubchem-client.md)
- [03 Configured HTTP Client](clients/03-configured-http-client.md)
- [04 Semantic Scholar Client](clients/04-semantic-scholar-client.md)
- [05 UniProt Client](clients/05-uniprot-client.md)

## HTTP-инфраструктура

Документация: [http/](http/)

- [00 HTTP Cache](http/00-http-cache.md) — кэширование HTTP-ответов
- [01 Rate Limiter](http/01-rate-limiter.md) — ограничение частоты запросов
- [02 Retry Policy](http/02-retry-policy.md) — политика повторных попыток
- [03 Circuit Breaker](http/03-circuit-breaker.md) — защита от сбоев
- [04 Pagination Strategy](http/04-pagination-strategy.md) — стратегия пагинации

## Конфигурация

Документация: [config/](config/)

- [00 Config Resolver](config/00-config-resolver.md) — резолвер конфигурации
- [01 Secret Provider](config/01-secret-provider.md) — провайдер секретов

## Схемы данных

Документация: [schemas/](schemas/)

- [00 Document Schema](schemas/00-document-schema.md)
- [01 TestItem Schema](schemas/01-testitem-schema.md)
- [02 Testitems Schema](schemas/02-testitems-schema.md)
- [03 Target Schema](schemas/03-target-schema.md)
- [04 Assay Schema](schemas/04-assay-schema.md)

## Core-сервисы

Документация: [core/](core/)

- [00 Pipeline Output Service](core/00-pipeline-output-service.md) — сервис вывода результатов
- [01 Write Artifacts](core/01-write-artifacts.md) — артефакты записи
- [02 Client Factory Registry](core/02-client-factory-registry.md) — реестр фабрик клиентов

## Связанная документация

- [ABC Index](../01-ABC/INDEX.md) — каталог абстрактных базовых классов
- [CLI](../cli/INDEX.md) — командная строка
- [QC](../qc/INDEX.md) — контроль качества
- [Clients Overview](../clients/INDEX.md) — обзор клиентского слоя

