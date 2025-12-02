# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации:

- **Основные правила**: `.cursorrules` — правила для AI-ассистента и разработчиков
- **Краткая сводка**: `docs/00-styleguide/00-rules-quick-reference.md` — быстрый справочник
- **Memories**: `docs/00-styleguide/00-memories.md` — ключевые правила для запоминания

## Документация

Полная документация по стилю и правилам находится в `docs/00-styleguide/`:

- `00-naming-conventions.md` — именование документации
- `01-new-entity-implementation-policy.md` — политика создания ABC/Default/Impl
- `02-new-entity-naming-policy.md` — полная политика именования
- `10-documentation-standards.md` — стандарты документации

### Архитектурные планы (бинарные вложения)

- `docs/30-architecture-plan-project.{docx,pdf}` — high-level architecture plan for the BioETL project.
- `docs/31-architecture-plan-etl-scientific-rest-apis.{docx,pdf}` — architecture plan for the ETL project integrating data from scientific REST APIs.

### Пайплайны и core компоненты

Документация по пайплайнам и базовым компонентам находится в `docs/02-pipelines/`:

- `00-pipeline-base.md` — базовая архитектура пайплайнов
- `01-base-external-data-client.md` — базовый клиент внешних API
- `02-logging-and-configuration.md` — логирование и конфигурация
- `03-unified-api-client.md` — унифицированный API-клиент и HTTP-адаптеры
- `04-unified-output-writer.md` — унифицированный writer для записи результатов
- `05-schema-registry.md` — реестр схем для валидации данных

#### ChEMBL Activity Pipeline

Документация по пайплайну ChEMBL Activity находится в `docs/02-pipelines/chembl/activity/`:

- `00-activity-chembl-overview.md` — обзор пайплайна ChEMBL Activity
- `01-activity-chembl-extract.md` — стадия извлечения данных
- `02-activity-chembl-transform.md` — стадия трансформации данных
- `03-activity-chembl-write.md` — стадия записи результатов
- `04-activity-chembl-parser.md` — парсер ответов ChEMBL API
- `05-activity-chembl-normalizer.md` — нормализатор данных активности
- `07-activity-chembl-descriptor.md` — дескриптор параметров извлечения
- `08-base-chembl-normalizer.md` — базовый нормализатор для ChEMBL
- `09-activity-chembl-batch-plan.md` — план батчирования запросов
- `10-activity-chembl-column-spec.md` — спецификация нормализации колонок
- `11-activity-chembl-column-mapping.md` — маппинг полей JSON на колонки
- `12-activity-chembl-schema.md` — Pandera-схема для валидации данных
- `13-activity-chembl-artifacts.md` — планировщик и сервис артефактов

#### ChEMBL Client Components

Документация по компонентам клиента ChEMBL находится в `docs/02-pipelines/chembl/`:

- `14-chembl-client.md` — REST-клиент для ChEMBL API
- `15-chembl-request-builder.md` — построитель запросов ChEMBL
- `16-requests-backend.md` — HTTP-бэкенд на основе requests
- `17-chembl-write-service.md` — сервис записи для ChEMBL-пайплайнов

#### ChEMBL Common Components

Документация по общим компонентам ChEMBL находится в `docs/02-pipelines/chembl/common/`:

- `18-chembl-common-pipeline.md` — базовый класс для ChEMBL-пайплайнов
- `19-chembl-pipeline-base.md` — базовый пайплайн для ChEMBL
- `20-chembl-extraction-service.md` — сервис извлечения данных ChEMBL
- `21-chembl-descriptor-factory.md` — фабрика дескрипторов ChEMBL
- `22-chembl-extraction-service-descriptor.md` — дескриптор извлечения через сервис
- `23-extraction-strategy-factory.md` — фабрика стратегий извлечения
- `24-service-extraction-strategy.md` — стратегия извлечения через сервис
- `25-dataclass-extraction-strategy.md` — стратегия извлечения через dataclass
- `26-chembl-extraction-descriptor.md` — dataclass-дескриптор извлечения
- `27-config-validation-error.md` — исключение валидации конфигурации

Полный индекс ChEMBL-пайплайнов: `docs/02-pipelines/chembl/INDEX.md`

#### Другие ChEMBL пайплайны

- `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md` — пайплайн для assay
- `docs/02-pipelines/chembl/assay/INDEX.md` — полный индекс документации по Assay
- `docs/02-pipelines/chembl/target/00-target-chembl-overview.md` — пайплайн для target
- `docs/02-pipelines/chembl/target/01-target-normalizer.md` — нормализатор данных target
- `docs/02-pipelines/chembl/document/00-document-chembl-overview.md` — пайплайн для document
- `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md` — пайплайн для testitem
- `docs/02-pipelines/chembl/testitem/INDEX.md` — полный индекс документации по TestItem

#### Клиенты внешних API

Документация по клиентам внешних API находится в `docs/02-pipelines/clients/`:

- `18-pubmed-client.md` — клиент для API PubMed
- `19-crossref-client.md` — клиент для API CrossRef
- `20-pubchem-client.md` — клиент для PubChem
- `21-configured-http-client.md` — базовая реализация настроенного HTTP-клиента
- `22-semantic-scholar-client.md` — клиент для API Semantic Scholar
- `23-uniprot-client.md` — клиент для REST API UniProt

#### HTTP компоненты

Документация по HTTP компонентам находится в `docs/02-pipelines/http/`:

- `23-http-cache.md` — кэш HTTP-ответов с TTL
- `24-rate-limiter.md` — лимитер частоты запросов
- `25-retry-policy.md` — политика повторных попыток
- `26-circuit-breaker.md` — Circuit Breaker для устойчивости
- `27-pagination-strategy.md` — стратегия пагинации

#### Конфигурация

Документация по компонентам конфигурации находится в `docs/02-pipelines/config/`:

- `28-config-resolver.md` — резолвер конфигурации из YAML
- `29-secret-provider.md` — провайдер секретов из переменных окружения

#### Core компоненты

Документация по core компонентам находится в `docs/02-pipelines/core/`:

- `25-pipeline-output-service.md` — сервис вывода результатов пайплайна

#### Схемы данных

Документация по схемам данных находится в `docs/schemas/` и `docs/02-pipelines/schemas/`:

- `00-schemas-registry-overview.md` — обзор реестра схем Pandera
- `27-testitem-schema.md` — схема для отдельного тестового элемента
- `28-testitems-schema.md` — схема для полного набора тестовых элементов
- `26-document-schema.md` — схема данных документов ChEMBL (см. `docs/02-pipelines/schemas/26-document-schema.md`)

#### ChEMBL Document Pipeline

Документация по пайплайну ChEMBL Document находится в `docs/02-pipelines/chembl/document/`:

- `00-document-chembl-overview.md` — обзор пайплайна ChEMBL Document
- `01-document-chembl-methods.md` — приватные методы пайплайна

### CLI и запуск пайплайнов

Документация по использованию CLI находится в `docs/cli/`:

- `INDEX.md` — индекс документации CLI
- `00-cli-overview.md` — обзор CLI и архитектуры
- `01-run-chembl-pipelines.md` — запуск ChEMBL-пайплайнов
- `02-validate-config.md` — валидация конфигурации
- `03-config-precedence-and-profiles.md` — приоритеты конфигурации и профили

### Клиенты внешних источников

Документация по клиентскому слою находится в `docs/clients/`:

- `INDEX.md` — индекс документации клиентов
- `00-clients-overview.md` — обзор архитектуры клиентского слоя
- `02-rest-yaml-migration.md` — миграция REST-клиентов на YAML-конфигурации
- `19-clients-diagrams.md` — генерация диаграмм объектов

### Quality Control (QC)

Документация по артефактам контроля качества находится в `docs/qc/`:

- `INDEX.md` — индекс документации QC
- `00-qc-artifacts-overview.md` — обзор QC-артефактов (meta.yaml, quality reports, JSON QC files)

### Схемы данных

Документация по схемам данных находится в `docs/schemas/`:

- `INDEX.md` — индекс документации схем
- `00-schemas-registry-overview.md` — обзор реестра схем Pandera