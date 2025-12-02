# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации. Актуальная сводка правил: `docs/00-styleguide/00-rules-summary.md`.

## Документация

### Архитектурные планы

- `docs/30-project-architecture-plan.{docx,pdf}` — общий архитектурный план проекта
- `docs/31-etl-integration-architecture-plan.{docx,pdf}` — архитектурный план ETL-интеграции научных REST API

### Индексы документации

- `docs/01-ABC/INDEX.md` — каталог ABC (абстрактных базовых классов)
- `docs/02-pipelines/chembl/INDEX.md` — индекс ChEMBL-пайплайнов и компонентов
- `docs/clients/INDEX.md` — клиентский слой и вспомогательные утилиты
- `docs/cli/INDEX.md` — CLI и запуск пайплайнов
- `docs/qc/INDEX.md` — артефакты контроля качества
- `docs/schemas/INDEX.md` — реестр схем данных

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
- `01-activity-chembl-extraction.md` — стадия извлечения данных
- `02-activity-chembl-transformation.md` — стадия трансформации данных
- `03-activity-chembl-io.md` — стадия записи результатов
- `04-activity-chembl-parser.md` — парсер ответов ChEMBL API
- `05-activity-chembl-normalizer.md` — нормализатор данных активности
- `07-activity-chembl-descriptor.md` — дескриптор параметров извлечения
- `09-activity-chembl-batch-plan.md` — план батчирования запросов
- `10-activity-chembl-column-spec.md` — спецификация нормализации колонок
- `11-activity-chembl-column-mapping.md` — маппинг полей JSON на колонки
- `12-activity-chembl-schema.md` — Pandera-схема для валидации данных
- `13-activity-chembl-artifacts.md` — планировщик и сервис артефактов

Полный индекс: `docs/02-pipelines/chembl/activity/INDEX.md`

#### ChEMBL Client Components

Документация по компонентам клиента ChEMBL находится в `docs/02-pipelines/chembl/`:

- `01-chembl-client.md` — REST-клиент для ChEMBL API
- `02-chembl-request-builder.md` — построитель запросов ChEMBL
- `03-chembl-requests-backend.md` — HTTP-бэкенд на основе requests
- `04-chembl-write-service.md` — сервис записи для ChEMBL-пайплайнов

#### ChEMBL Common Components

Документация по общим компонентам ChEMBL находится в `docs/02-pipelines/chembl/common/`:

- `00-base-chembl-normalizer.md` — базовый нормализатор для ChEMBL
- `05-chembl-base-pipeline.md` — базовый пайплайн для ChEMBL
- `06-chembl-extraction-service.md` — сервис извлечения данных ChEMBL
- `07-chembl-descriptor-factory.md` — фабрика дескрипторов ChEMBL
- `08-chembl-extraction-service-descriptor.md` — дескриптор сервиса извлечения ChEMBL
- `09-extraction-strategy-factory.md` — фабрика стратегий извлечения данных
- `10-service-extraction-strategy.md` — стратегия извлечения с сервисом
- `11-dataclass-extraction-strategy.md` — стратегия извлечения с dataclass-описанием
- `12-chembl-extraction-descriptor.md` — дескриптор параметров извлечения ChEMBL
- `13-config-validation-error.md` — описание ошибок валидации конфигурации
- `14-chembl-context-facade.md` — фасад контекста ChEMBL

Полный индекс: `docs/02-pipelines/chembl/INDEX.md`

#### Другие ChEMBL пайплайны

- `docs/02-pipelines/chembl/assay/` — пайплайн для assay (INDEX.md)
- `docs/02-pipelines/chembl/target/` — пайплайн для target
- `docs/02-pipelines/chembl/document/` — пайплайн для document
- `docs/02-pipelines/chembl/testitem/` — пайплайн для testitem (INDEX.md)

#### Клиенты внешних API

Документация по клиентам внешних API находится в `docs/02-pipelines/clients/`:

- `00-pubmed-client.md` — клиент для API PubMed
- `01-crossref-client.md` — клиент для API CrossRef
- `02-pubchem-client.md` — клиент для PubChem
- `03-configured-http-client.md` — базовая реализация настроенного HTTP-клиента
- `04-semantic-scholar-client.md` — клиент для API Semantic Scholar
- `05-uniprot-client.md` — клиент для REST API UniProt

Обзор клиентского слоя: `docs/clients/INDEX.md`

### CLI и запуск пайплайнов

Документация по CLI доступна в `docs/cli/INDEX.md`.

### Схемы данных

Документация по схемам данных находится в `docs/schemas/`:

- `INDEX.md` — индекс документации схем
- `00-schemas-registry-overview.md` — обзор реестра схем Pandera

### Quality Control (QC)

Документация по QC-артефактам: `docs/qc/INDEX.md`.
