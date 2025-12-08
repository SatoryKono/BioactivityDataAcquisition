# Architecture

## 1. Общий обзор

Слои: `interfaces`, `application`, `domain`, `infrastructure`.  
Все взаимодействия проходят через контракты, гарантируя детерминизм (фиксированный порядок, UTC, атомарная запись) и валидацию данных перед записью (Pandera-схемы).

## 2. Слой domain

Назначение: контракты и бизнес-инварианты без привязки к инфраструктуре.

Состав:

- контракты клиентов и пайплайнов (`domain.clients.*`, `domain.pipelines.contracts`, `domain.transform.contracts`);
- реестр провайдеров (`domain.provider_registry`, `domain.providers`);
- ошибки (`domain.errors`);
- схемы (Pandera) и реестр схем (`domain.schemas.*`, `domain.schemas.registry`);
- сервисы: валидация (`domain.validation.service`), нормализация (`domain.transform.contracts.NormalizationServiceABC` + реализации в `infrastructure.transform.impl`), хеширование (порт `HashServiceABC` + реализация `infrastructure.transform.impl.hash_service_impl`), трансформеры/нормалайзеры (`domain.transform.*`);
- контракты пайплайнов и схем (`domain.schemas.pipeline_contracts`).

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

- оркестратор пайплайнов (`application.orchestrator.PipelineOrchestrator`), который по `PipelineConfig` и имени пайплайна собирает экземпляр `PipelineBase`;
- DI контейнер (`application.container.PipelineContainer`) — создаёт `ValidationService`, `UnifiedOutputWriter`, `HashService`, NormalizationService, record sources (`ApiRecordSource`, `CsvRecordSourceImpl`, `IdListRecordSourceImpl`) и подключает `ProviderRegistryABC`/`ChemblProviderComponentsFactory`;
- реестр пайплайнов (`application.pipelines.registry`) — переименованные ID вида `<entity>_<provider>` → класс пайплайна (для ChEMBL: все `*_chembl` → `ChemblPipelineBase`);
- базовый пайплайн (Template Method: extract → transform → validate → write) `application.pipelines.base.PipelineBase`, использующий `StageRuntimeManagerImpl` для хуков, политики ошибок и подсчёта статистик стадий;
- ChEMBL базовый пайплайн (`application.pipelines.chembl.base.ChemblPipelineBase`) и stage-компоненты (`chembl/extractor.py`, `chembl/transformer.py`), переиспользуемые всеми сущностями (activity, assay, document, target, molecule);
- конфиг пайплайна (`PipelineConfig` из `domain.configs` + YAML `configs/pipelines/*`), пост‑трансформеры по умолчанию (`default_post_transformer` — хеши, индексы, версии, даты).

Контейнер регистрирует провайдеров, создает логгер, хук/политику ошибок, сервисы валидации/нормализации/хеширования, источники данных (API/CSV/ID-only), writer и post-transformer chain.

## 5. Слой interfaces

Точки входа:

- CLI (`interfaces.cli.app`, Typer);
- REST сервер (`interfaces.rest.server`);
- MQ listener/handler (`interfaces.mq.*`).

## 6. Документация и конфиги

- YAML-конфиги провайдеров/пайплайнов (`configs/`);
- архитектурные схемы в `docs/architecture/diagrams/*` (class/sequence/flow/component по политике `diagrams/00-diagramming-policy.md`);
- правила детерминизма, схем и именования — в общих правилах проекта (`docs/00-styleguide/*`);
- архитектурные решения фиксируются в ADR каталоге `docs/architecture/decisions/0000-adr-index.md`.

 
