# ChEMBL Pipelines Documentation

Документация по пайплайнам обработки данных из ChEMBL.

## Обзор

Все ChEMBL-пайплайны наследуются от `PipelineBase` и используют общую инфраструктуру для работы с данными ChEMBL.

## Пайплайны

### Activity

- [00 Activity ChEMBL Overview](../activity/00-activity-chembl-overview.md) — основной пайплайн для обработки данных биоактивности
- [01 Activity ChEMBL Extract](../activity/01-activity-chembl-extract.md) — стадия извлечения данных
- [02 Activity ChEMBL Transform](../activity/02-activity-chembl-transform.md) — стадия трансформации данных
- [03 Activity ChEMBL Write](../activity/03-activity-chembl-write.md) — стадия записи результатов
- [INDEX](../activity/INDEX.md) — полный индекс документации по Activity

### Assay

- [00 Assay ChEMBL Overview](assay/00-assay-chembl-overview.md) — пайплайн для выгрузки данных об биоактивности типа "assay"
- [INDEX](assay/INDEX.md) — полный индекс документации по Assay

### Target

- [00 Target ChEMBL Overview](target/00-target-chembl-overview.md) — пайплайн для сущности "target" с обогащением данными UniProt/IUPHAR
- [01 Target Normalizer](target/01-target-normalizer.md) — нормализатор данных target

### Document

- [00 Document ChEMBL Overview](document/00-document-chembl-overview.md) — пайплайн для сущности "document" с обогащением из внешних источников
- [01 Document ChEMBL Methods](document/01-document-chembl-methods.md) — приватные методы пайплайна

### TestItem

- [00 TestItem ChEMBL Overview](testitem/00-testitem-chembl-overview.md) — пайплайн для тестовых веществ с обогащением данными PubChem
- [INDEX](testitem/INDEX.md) — полный индекс документации по TestItem

## Общие компоненты

- [14 ChEMBL Client](14-chembl-client.md) — REST-клиент для ChEMBL API
- [15 ChEMBL Request Builder](15-chembl-request-builder.md) — построитель запросов ChEMBL
- [16 Requests Backend](16-requests-backend.md) — HTTP-бэкенд на основе requests
- [17 ChEMBL Write Service](17-chembl-write-service.md) — сервис записи для ChEMBL-пайплайнов

## Common компоненты

- [18 ChEMBL Common Pipeline](common/18-chembl-common-pipeline.md) — базовый класс для ChEMBL-пайплайнов
- [19 ChEMBL Pipeline Base](common/19-chembl-pipeline-base.md) — базовый пайплайн для ChEMBL
- [20 ChEMBL Extraction Service](common/20-chembl-extraction-service.md) — сервис извлечения данных ChEMBL
- [21 ChEMBL Descriptor Factory](common/21-chembl-descriptor-factory.md) — фабрика дескрипторов ChEMBL
- [22 ChEMBL Extraction Service Descriptor](common/22-chembl-extraction-service-descriptor.md) — дескриптор извлечения через сервис
- [23 Extraction Strategy Factory](common/23-extraction-strategy-factory.md) — фабрика стратегий извлечения
- [24 Service Extraction Strategy](common/24-service-extraction-strategy.md) — стратегия извлечения через сервис
- [25 Dataclass Extraction Strategy](common/25-dataclass-extraction-strategy.md) — стратегия извлечения через dataclass
- [26 ChEMBL Extraction Descriptor](common/26-chembl-extraction-descriptor.md) — dataclass-дескриптор извлечения
- [27 Config Validation Error](common/27-config-validation-error.md) — исключение валидации конфигурации

## Связанная документация

- [Pipeline Base](../../00-pipeline-base.md) — базовый класс пайплайнов
- [Base External Data Client](../../01-base-external-data-client.md) — базовый клиент внешних API
- [Unified Output Writer](../../04-unified-output-writer.md) — унифицированный writer для записи
- [Schema Registry](../../05-schema-registry.md) — реестр схем для валидации

