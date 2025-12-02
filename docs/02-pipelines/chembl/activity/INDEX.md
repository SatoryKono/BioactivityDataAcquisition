# ChEMBL Activity Pipeline Documentation

Документация по пайплайну обработки данных биоактивности из ChEMBL.

## Обзор

- [00 Activity ChEMBL Overview](00-activity-chembl-overview.md) — обзор пайплайна, архитектура, основные методы

## Стадии пайплайна

- [01 Activity ChEMBL Extraction](01-activity-chembl-extraction.md) — стадия извлечения данных из ChEMBL API
- [02 Activity ChEMBL Transformation](02-activity-chembl-transformation.md) — стадия трансформации и нормализации данных
- [03 Activity ChEMBL IO](03-activity-chembl-io.md) — стадия записи результатов и генерации артефактов

## Компоненты обработки данных

- [04 Activity ChEMBL Parser](04-activity-chembl-parser.md) — парсер ответов ChEMBL API
- [05 Activity ChEMBL Normalizer](05-activity-chembl-normalizer.md) — нормализатор данных активности
- [07 Activity ChEMBL Descriptor](07-activity-chembl-descriptor.md) — дескриптор параметров извлечения
- [08 Base ChEMBL Normalizer](08-base-chembl-normalizer.md) — базовый нормализатор для ChEMBL
- [09 Activity ChEMBL Batch Plan](09-activity-chembl-batch-plan.md) — план батчирования запросов
- [10 Activity ChEMBL Column Spec](10-activity-chembl-column-spec.md) — спецификация нормализации колонок
- [11 Activity ChEMBL Column Mapping](11-activity-chembl-column-mapping.md) — маппинг полей JSON на колонки
- [12 Activity ChEMBL Schema](12-activity-chembl-schema.md) — Pandera-схема для валидации данных
- [13 Activity ChEMBL Artifacts](13-activity-chembl-artifacts.md) — планировщик и сервис артефактов

## Связанная документация

- [Base External Data Client](../../01-base-external-data-client.md) — базовый клиент внешних API
- [ChEMBL Client](../14-chembl-client.md) — REST-клиент для ChEMBL API
- [ChEMBL Request Builder](../15-chembl-request-builder.md) — построитель запросов ChEMBL
- [Requests Backend](../16-requests-backend.md) — HTTP-бэкенд на основе requests
- [Unified Output Writer](../../04-unified-output-writer.md) — унифицированный writer для записи
- [Schema Registry](../../05-schema-registry.md) — реестр схем для валидации
- [Validation Service](../../06-validation-service.md) — сервис валидации данных

