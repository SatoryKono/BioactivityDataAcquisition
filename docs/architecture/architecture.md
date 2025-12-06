
# Архитектура проекта BioETL

## 1. Общий обзор

Репозиторий структурирован по уровневой архитектуре: `domain`, `application`, `infrastructure`, `interfaces`.  
Каждый слой изолирует ответственность и взаимодействует только через четко определенные контракты.

## 2. Слой domain

Содержит:
- протоколы (`DataClientProtocol`, `PipelineProtocol`);
- ошибки (`DomainError`, `SchemaValidationError`, `ExternalAPIError`, `RetryExhaustedError`);
- модели и схемы (каркасные модули).

Основная задача — описать доменные контракты, не зависящие от реализации.

## 3. Слой infrastructure

Содержит:
- HTTP‑клиент `UnifiedAPIClient`;
- клиент ChEMBL `ChemblDataClientHTTPImpl`;
- файловое хранилище `FileStorageImpl`;
- логирование.

Этот слой реализует внешние зависимости, определенные протоколами из domain.

## 4. Слой application

Содержит:
- конкретные пайплайны (extract, transform, validate, export);
- сервисы orchestration (`PipelineRunner`);
- реестр пайплайнов (`PipelineRegistry`).

Этот слой реализует бизнес‑логику ETL.

## 5. Слой interfaces

CLI‑интерфейс на базе `typer`, обеспечивающий точку входа для запуска пайплайнов.

## 6. Документация и конфиги

- YAML‑конфиг пайплайна;
- Markdown‑документация в `docs/`.

