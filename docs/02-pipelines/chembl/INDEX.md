# ChEMBL Pipelines Documentation

Документация по пайплайнам обработки данных из ChEMBL.

## Обзор

Все ChEMBL-пайплайны наследуются от `PipelineBase` и используют общую инфраструктуру для работы с данными ChEMBL.

## Пайплайны

### Activity

- [00 Activity ChEMBL Overview](../activity/00-activity-chembl-overview.md) — основной пайплайн для обработки данных биоактивности
- [01 Activity ChEMBL Extraction](../activity/01-activity-chembl-extraction.md) — стадия извлечения данных
- [02 Activity ChEMBL Transformation](../activity/02-activity-chembl-transformation.md) — стадия трансформации данных
- [03 Activity ChEMBL IO](../activity/03-activity-chembl-io.md) — стадия записи результатов
- [INDEX](../activity/INDEX.md) — полный индекс документации по Activity

### Assay

- [00 Assay ChEMBL Overview](assay/00-assay-chembl-overview.md) — пайплайн для выгрузки данных об биоактивности типа "assay"
- [INDEX](assay/INDEX.md) — полный индекс документации по Assay

### Target

- [00 Target ChEMBL Overview](target/00-target-chembl-overview.md) — пайплайн для сущности "target" с обогащением данными UniProt/IUPHAR
- [01 Target ChEMBL Normalizer](target/01-target-chembl-normalizer.md) — нормализатор данных target

### Document

- [00 Document ChEMBL Overview](document/00-document-chembl-overview.md) — пайплайн для сущности "document" с обогащением из внешних источников
- [01 Document ChEMBL Methods](document/01-document-chembl-methods.md) — приватные методы пайплайна

### TestItem

- [00 TestItem ChEMBL Overview](testitem/00-testitem-chembl-overview.md) — пайплайн для тестовых веществ с обогащением данными PubChem
- [INDEX](testitem/INDEX.md) — полный индекс документации по TestItem

## Common компоненты (Shared)

Документация по общим компонентам находится в `docs/02-pipelines/chembl/common/`:

- [00 Base ChEMBL Normalizer](common/00-base-chembl-normalizer.md) — базовый нормализатор
- [01 ChEMBL Client](common/01-chembl-client.md) — REST-клиент
- [02 ChEMBL Request Builder](common/02-chembl-request-builder.md) — построитель запросов
- [03 ChEMBL Requests Backend](common/03-chembl-requests-backend.md) — транспортный бэкенд
- [04 ChEMBL Write Service](common/04-chembl-write-service.md) — сервис записи
- [05 ChEMBL Base Pipeline](common/05-chembl-base-pipeline.md) — базовый класс пайплайнов
- [06 ChEMBL Extraction Service](common/06-chembl-extraction-service.md) — сервис извлечения
- [07 ChEMBL Descriptor Factory](common/07-chembl-descriptor-factory.md) — фабрика дескрипторов
- [08 ChEMBL Extraction Service Descriptor](common/08-chembl-extraction-service-descriptor.md) — дескриптор извлечения через сервис
- [09 ChEMBL Extraction Strategy Factory](common/09-chembl-extraction-strategy-factory.md) — фабрика стратегий извлечения
- [10 ChEMBL Service Extraction Strategy](common/10-chembl-service-extraction-strategy.md) — стратегия извлечения через сервис
- [11 ChEMBL Dataclass Extraction Strategy](common/11-chembl-dataclass-extraction-strategy.md) — стратегия извлечения через dataclass
- [12 ChEMBL Extraction Descriptor](common/12-chembl-extraction-descriptor.md) — dataclass-дескриптор извлечения
- [13 ChEMBL Config Validation Error](common/13-chembl-config-validation-error.md) — исключение валидации конфигурации
- [14 ChEMBL Context Facade](common/14-chembl-context-facade.md) — фасад контекста ChEMBL

## Связанная документация

- [Pipeline Base](../../00-pipeline-base.md) — базовый класс пайплайнов
- [Base External Data Client](../../01-base-external-data-client.md) — базовый клиент внешних API
- [Unified Output Writer](../../04-unified-output-writer.md) — унифицированный writer для записи
- [Schema Registry](../../05-schema-registry.md) — реестр схем для валидации
- [Data Flow](../../../architecture/data-flow.md) — E2E описание потока данных
