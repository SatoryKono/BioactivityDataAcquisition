# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации:

- **Основные правила**: `.cursorrules` — правила для AI-ассистента и разработчиков
- **Краткая сводка**: `docs/00-styleguide/RULES_QUICK_REFERENCE.md` — быстрый справочник
- **Memories**: `docs/00-styleguide/MEMORIES.md` — ключевые правила для запоминания

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

- `docs/01-ABC/INDEX.md` — человекочитаемый каталог ABC, Default и Impl
- `docs/02-pipelines/` — пайплайны и core-компоненты; индекс ChEMBL-компонентов: `docs/02-pipelines/chembl/INDEX.md` (отдельные пайплайны activity, assay, target, document, testitem используют собственные `INDEX.md` в подкаталогах)
- `docs/clients/INDEX.md` — клиентский слой и вспомогательные утилиты
- `docs/cli/INDEX.md` — CLI и запуск пайплайнов
- `docs/qc/INDEX.md` — артефакты контроля качества
- `docs/schemas/INDEX.md` — реестр схем данных

### Пайплайны и core компоненты

Документация по пайплайнам и базовым компонентам находится в `docs/02-pipelines/`. Общие принципы описаны в базовых гайдах (например, `00-pipeline-base.md`, `01-base-external-data-client.md`, `02-logging-and-configuration.md`, `03-unified-api-client.md`, `04-unified-output-writer.md`, `05-schema-registry.md`). Полный список ChEMBL-пайплайнов и общих компонентов поддерживается в `docs/02-pipelines/chembl/INDEX.md`; отдельные пайплайны (activity, assay, target, document, testitem) используют собственные `INDEX.md` в соответствующих подкаталогах.

### CLI и запуск пайплайнов

Полное содержание документации по CLI доступно в `docs/cli/INDEX.md`.

### Клиенты внешних источников

Полный перечень клиентских материалов поддерживается в `docs/clients/INDEX.md`.

### Quality Control (QC)

Список QC-артефактов и описаний поддерживается в `docs/qc/INDEX.md`.

### Схемы данных

Документация по схемам данных находится в `docs/schemas/`:

- `INDEX.md` — индекс документации схем
- `00-schemas-registry-overview.md` — обзор реестра схем Pandera

### Архитектурные планы

- `docs/30-project-architecture-plan.docx` / `docs/30-project-architecture-plan.pdf` — общий архитектурный план проекта
- `docs/31-etl-integration-architecture-plan.docx` / `docs/31-etl-integration-architecture-plan.pdf` — архитектурный план ETL-интеграции научных REST API
