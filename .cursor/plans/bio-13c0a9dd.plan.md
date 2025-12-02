<!-- 13c0a9dd-a93c-4eb4-9006-c0d9d9123227 c787bcbd-f9d8-4340-8b56-3adcb9c17538 -->
# Документация проекта BioETL

## Структура документации

Создать полную иерархию `docs/` согласно README.md:

### 1. Overview (обзорные документы)

- `docs/overview/index.md` - введение в проект, ключевые концепции
- `docs/overview/getting-started.md` - установка и первый запуск
- `docs/overview/architecture-overview.md` - высокоуровневая архитектура (слои, ABC-модель)
- `docs/overview/glossary.md` - словарь терминов (Assay, Activity, Target, TestItem, Pipeline и др.)

### 2. Guides (практические руководства)

- `docs/guides/running-pipelines.md` - запуск пайплайнов через CLI
- `docs/guides/configuration.md` - работа с конфигурациями и профилями
- `docs/guides/adding-new-pipeline.md` - создание нового пайплайна
- `docs/guides/adding-new-abc.md` - добавление нового ABC/Default/Impl
- `docs/guides/troubleshooting.md` - решение типичных проблем

### 3. Reference/ABC (ABC-интерфейсы)

- `docs/reference/abc/index.md` - каталог всех ABC (StageABC, PipelineHookABC, SourceClientABC, TransformerABC, ValidatorABC, WriterABC и др.)

### 4. Reference/Core (ядро)

- `docs/reference/core/00-pipeline-base.md` - PipelineBase и производные (ChemblPipelineBase, ChemblCommonPipeline)
- `docs/reference/core/03-unified-api-client.md` - унифицированный API-клиент
- `docs/reference/core/04-unified-output-writer.md` - унифицированный writer
- `docs/reference/core/05-schema-registry.md` - реестр схем
- `docs/reference/core/06-validation-service.md` - сервис валидации

### 5. Reference/Infrastructure

- `docs/reference/infrastructure/http/index.md` - HTTP: cache, rate limiter, retry, circuit breaker, pagination
- `docs/reference/infrastructure/config/index.md` - ConfigResolver, SecretProvider
- `docs/reference/infrastructure/logging/index.md` - структурированное логирование

### 6. Pipelines (ChEMBL)

- `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md` - ChemblBasePipeline и common components
- `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md` - Activity pipeline
- `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md` - Assay pipeline
- `docs/02-pipelines/chembl/target/00-target-chembl-overview.md` - Target pipeline
- `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md` - TestItem pipeline
- `docs/02-pipelines/chembl/document/00-document-chembl-overview.md` - Document pipeline с обогащением

### 7. Reference/Clients

- `docs/reference/clients/06-clients-overview.md` - обзор клиентского слоя (ChemblClient, RequestBuilder, ResponseParser, Paginator)

### 8. Reference/Schemas

- `docs/reference/schemas/05-schemas-registry-overview.md` - обзор Pandera-схем

### 9. Reference/QC

- `docs/reference/qc/00-qc-artifacts-overview.md` - артефакты контроля качества

### 10. Reference/CLI

- `docs/reference/cli/cli-overview.md` - архитектура CLI
- `docs/reference/cli/commands.md` - список команд
- `docs/reference/cli/validate-config.md` - валидация конфигураций

### 11. Architecture

- `docs/architecture/index.md` - архитектурные решения
- `docs/architecture/00-duplication-reduction-roadmap.md` - снижение дублирования
- `docs/architecture/data-flow.md` - поток данных extract→transform→validate→write

### 12. Project

- `docs/project/00-rules-summary.md` - сводка правил проекта
- `docs/project/04-architecture-and-duplication-reduction.md` - принципы архитектуры

## Источники контента

| Раздел | Источник |
|--------|----------|
| Доменные ABC (Assay, Activity, Target, TestItem) | Секции 2.1-2.5 текста |
| Слои архитектуры | Секция 3 текста |
| PipelineBase | Секция 4 + PipelineBase.pdf |
| ABC-интерфейсы | Секция 5 + ABC2.pdf |
| ChEMBL клиенты | Секция 6 текста |
| Схемы и валидация | Секция 7 текста |
| ChEMBL-пайплайны | Секции 8.1-8.6 текста |
| Интеграция источников | Секция 9 текста |
| Конфигурация и CLI | Секция 10 текста |
| Тестирование | Секция 11 текста |

## Ключевые файлы для редактирования

- Создать ~35 markdown-файлов в `docs/`
- Обновить ссылки в README.md при необходимости

### To-dos

- [ ] Создать docs/overview/ (index, getting-started, architecture-overview, glossary)
- [ ] Создать docs/guides/ (running-pipelines, configuration, adding-new-pipeline, adding-new-abc, troubleshooting)
- [ ] Создать docs/reference/abc/index.md - каталог ABC-интерфейсов
- [ ] Создать docs/reference/core/ (pipeline-base, unified-api-client, unified-output-writer, schema-registry, validation-service)
- [ ] Создать docs/reference/infrastructure/ (http, config, logging)
- [ ] Создать docs/02-pipelines/chembl/ (common, activity, assay, target, testitem, document)
- [ ] Создать docs/reference/clients/, schemas/, qc/
- [ ] Создать docs/reference/cli/ (cli-overview, commands, validate-config)
- [ ] Создать docs/architecture/ (index, duplication-reduction, data-flow)
- [ ] Создать docs/project/ (rules-summary, architecture-and-duplication-reduction)