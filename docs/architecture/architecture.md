
# Архитектура проекта BioETL

## 1. Общий обзор

Слои: `interfaces`, `application`, `domain`, `infrastructure`.  
Все взаимодействия проходят через контракты, гарантируя детерминизм (фиксированный порядок, UTC, атомарная запись) и валидацию данных перед записью (Pandera-схемы).

## 2. Слой domain

Назначение: контракты и бизнес-инварианты без привязки к инфраструктуре.

Состав:
- контракты клиентов и пайплайнов (`domain.contracts`, `domain.clients.*`, `domain.transform.contracts`);
- реестр провайдеров (`domain.provider_registry`, `domain.providers`);
- ошибки (`domain.errors`);
- схемы (Pandera) и реестр схем (`domain.schemas.*`, `domain.schemas.registry`);
- сервисы: валидация (`domain.validation.service`), нормализация (`domain.normalization_service`), хеширование (`domain.transform.hash_service`), трансформеры/нормалайзеры (`domain.transform.*`);
- контракты пайплайнов (`domain.schemas.pipeline_contracts`).

## 3. Слой infrastructure

Назначение: реализации внешних зависимостей и техник I/O.

Состав:
- HTTP клиенты: `infrastructure.clients.base.impl.unified_client` (retry/backoff, rate limit, circuit breaker), ChEMBL HTTP `infrastructure.clients.chembl.impl.http_client` + пагинатор/парсер;
- логирование: `infrastructure.logging.impl.unified_logger` (структурные события);
- вывод: `infrastructure.output.unified_writer` (CSV/Parquet + metadata, атомарная запись, checksums);
- конфиги: резолвер и модели провайдеров (`infrastructure.config.*`);
- файловые утилиты: атомарные записи, checksum, CSV record source (`infrastructure.files.*`).

## 4. Слой application

Назначение: сборка и выполнение пайплайнов.

Состав:
- оркестратор (`application.orchestrator`) + DI контейнер (`application.container`);
- реестр пайплайнов (`application.pipelines.registry`);
- базовый пайплайн (Template Method: extract → transform → validate → write) `application.pipelines.base` + менеджеры стадий/хуков/политики ошибок;
- ChEMBL базовый пайплайн и сущностные пайплайны (`application.pipelines.chembl.*`);
- сервис извлечения ChEMBL (`application.services.chembl_extraction`);
- конфиг пайплайна (`application.config.pipeline_config_schema`, `config_loader`), пост-трансформеры (хеши, индексы, версии, даты).

Контейнер регистрирует провайдеров, создает логгер, хук/политику ошибок, сервисы валидации/нормализации/хеширования, источники данных (API/CSV/ID-only), writer и post-transformer chain.

## 5. Слой interfaces

Точки входа:
- CLI (`interfaces.cli.app`, Typer);
- REST сервер (`interfaces.rest.server`);
- MQ listener/handler (`interfaces.mq.*`).

## 6. Документация и конфиги

- YAML-конфиги провайдеров/пайплайнов (`configs/`);
- архитектурные схемы в `docs/architecture/` (см. компонентную диаграмму `11-component-diagram.md`);
- правила детерминизма, схем и именования — в общих правилах проекта (docs/00-styleguide).

