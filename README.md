# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации. Актуальная сводка правил: [`docs/project/rules-summary.md`](docs/project/00-rules-summary.md).

## Документация

### Начало работы

- **[Overview](docs/overview/index.md)** — Введение в проект, ключевые концепции
- **[Getting Started](docs/overview/getting-started.md)** — Быстрый старт: установка и первый запуск
- **[Architecture Overview](docs/overview/architecture-overview.md)** — Высокоуровневая архитектура системы
- **[Glossary](docs/overview/glossary.md)** — Словарь терминов

### Практические руководства

- **[Running Pipelines](docs/guides/running-pipelines.md)** — Как запустить пайплайн
- **[Configuration](docs/guides/configuration.md)** — Работа с конфигурациями и профилями
- **[Adding a New Pipeline](docs/guides/adding-new-pipeline.md)** — Создание нового пайплайна
- **[Adding a New ABC](docs/guides/adding-new-abc.md)** — Добавление нового ABC/Default/Impl
- **[Troubleshooting](docs/guides/troubleshooting.md)** — Решение проблем

### Референсная документация

#### ABC (Abstract Base Classes)

- **[ABC Index](docs/reference/abc/index.md)** — Каталог всех абстрактных базовых классов

#### Core Components

- **[Pipeline Base](docs/reference/core/00-pipeline-base.md)** — Базовая архитектура пайплайнов
- **[Unified API Client](docs/reference/core/03-unified-api-client.md)** — Унифицированный API-клиент
- **[Unified Output Writer](docs/reference/core/04-unified-output-writer.md)** — Унифицированный writer
- **[Schema Registry](docs/reference/core/05-schema-registry.md)** — Реестр схем для валидации
- **[Validation Service](docs/reference/core/06-validation-service.md)** — Сервис валидации данных

#### Infrastructure

- **[HTTP Infrastructure](docs/reference/infrastructure/http/)** — HTTP cache, rate limiter, retry policy, circuit breaker, pagination
- **[Configuration](docs/reference/infrastructure/config/)** — Config resolver, secret provider
- **[Logging](docs/reference/infrastructure/logging/)** — Структурированное логирование

#### Pipelines

- **[ChEMBL Pipelines](docs/02-pipelines/chembl/)** — Пайплайны для ChEMBL
  - Activity, Assay, Document, Target, TestItem
  - Common components

#### Clients

- **[Clients Overview](docs/reference/clients/06-clients-overview.md)** — Обзор клиентского слоя
- PubMed, CrossRef, PubChem, Semantic Scholar, UniProt clients

#### Schemas

- **[Schemas Registry](docs/reference/schemas/05-schemas-registry-overview.md)** — Обзор реестра схем Pandera
- Document, TestItem, Target, Assay schemas

#### Quality Control

- **[QC Artifacts](docs/reference/qc/00-qc-artifacts-overview.md)** — Артефакты контроля качества

#### CLI

- **[CLI Overview](docs/reference/cli/cli-overview.md)** — Архитектура CLI
- **[CLI Commands](docs/reference/cli/commands.md)** — Список команд
- **[Validate Config](docs/reference/cli/validate-config.md)** — Валидация конфигураций

### Архитектура

- **[Architecture Decisions](docs/architecture/)** — Архитектурные решения и дорожные карты
- **[Duplication Reduction](docs/architecture/00-duplication-reduction-roadmap.md)** — Снижение дублирования

### Правила проекта

- **[Rules Summary](docs/project/00-rules-summary.md)** — Краткая сводка всех правил
- **[Architecture Patterns](docs/project/04-architecture-and-duplication-reduction.md)** — Принципы снижения дублирования

### Конфигурация

- **[Configuration Architecture](configs/README.md)** — Архитектура конфигураций и профилей
