# ChEMBL Activity Pipeline Documentation

Документация по пайплайну обработки данных биоактивности из ChEMBL.

## Overview

- [00 Activity ChEMBL Overview](00-activity-chembl-overview.md) — обзор пайплайна, архитектура, основные методы, дескриптор извлечения и план батчирования

## Pipeline Stages

- [01 Activity ChEMBL Extraction](01-activity-chembl-extraction.md) — стадия извлечения данных из ChEMBL API, парсинг ответов и маппинг колонок
- [02 Activity ChEMBL Transformation](02-activity-chembl-transformation.md) — стадия трансформации, нормализации данных и спецификации колонок
- [03 Activity ChEMBL IO](03-activity-chembl-io.md) — стадия записи результатов, генерации артефактов и планирование артефактов

## Schema

- [12 Activity ChEMBL Schema](12-activity-chembl-schema.md) — Pandera-схема для валидации данных

## Related Documentation

- [Base External Data Client](../../01-base-external-data-client.md) — базовый клиент внешних API
- [ChEMBL Client](../common/01-chembl-client.md) — REST-клиент для ChEMBL API
- [ChEMBL Request Builder](../common/02-chembl-request-builder.md) — построитель запросов ChEMBL
- [ChEMBL Requests Backend](../common/03-chembl-requests-backend.md) — HTTP-бэкенд на основе requests
- [Base ChEMBL Normalizer](../common/00-base-chembl-normalizer.md) — общий нормализатор для всех ChEMBL-пайплайнов
- [Unified Output Writer](../../04-unified-output-writer.md) — унифицированный writer для записи
- [Schema Registry](../../05-schema-registry.md) — реестр схем для валидации
- [Validation Service](../../06-validation-service.md) — сервис валидации данных
