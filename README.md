# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации. Актуальная сводка правил: `docs/project/00-rules-summary.md`.

## Локальные проверки качества

- Установить хуки: `pre-commit install`
- Прогнать форматирование и линтеры: `pre-commit run --all-files` (ruff, black, isort, mypy, import-linter)
- Запустить архитектурный тест: `pytest tests/architecture/test_layer_dependencies.py`
- Полный цикл lint/type-check в CI: ruff → black --check → isort --check-only → mypy → архитектурные тесты → import-linter

## Документация

### Структура документации

| Раздел | Путь | Описание |
|--------|------|----------|
| Styleguide | [docs/00-styleguide/](docs/00-styleguide/) | Правила и стайлгайды |
| ABC Index | [docs/01-ABC/INDEX.md](docs/01-ABC/INDEX.md) | Каталог абстрактных базовых классов |
| Pipelines | [docs/02-pipelines/00-index.md](docs/02-pipelines/00-index.md) | Пайплайны и core-компоненты |
| CLI | [docs/cli/INDEX.md](docs/cli/INDEX.md) | Командная строка и запуск пайплайнов |
| Schemas | [docs/schemas/00-index.md](docs/schemas/00-index.md) | Реестр схем данных |
| QC | [docs/qc/INDEX.md](docs/qc/INDEX.md) | Артефакты контроля качества |
| Clients | [docs/clients/INDEX.md](docs/clients/INDEX.md) | Клиентский слой |

### Core компоненты

Документация по базовым компонентам находится в `docs/02-pipelines/`:

| # | Документ | Описание |
|---|----------|----------|
| 00 | [pipeline-base](docs/02-pipelines/00-pipeline-base.md) | Базовая архитектура пайплайнов |
| 01 | [base-external-data-client](docs/02-pipelines/01-base-external-data-client.md) | Базовый клиент внешних API (Legacy) |
| 02 | [logging-and-configuration](docs/02-pipelines/02-logging-and-configuration.md) | Логирование и конфигурация |
| 03 | [unified-api-client](docs/02-pipelines/03-unified-api-client.md) | Унифицированный API-клиент |
| 04 | [unified-output-writer](docs/02-pipelines/04-unified-output-writer.md) | Унифицированный writer для записи |
| 05 | [schema-registry](docs/02-pipelines/05-schema-registry.md) | Реестр схем для валидации |
| 06 | [validation-service](docs/02-pipelines/06-validation-service.md) | Сервис валидации данных |
| 07 | [client-architecture](docs/02-pipelines/07-client-architecture.md) | Архитектура клиентского слоя |

### Пайплайны по провайдерам

- [ChEMBL Pipelines](docs/02-pipelines/chembl/00-index.md) — Activity, Assay, Target, Document, TestItem

Детальная документация по конкретным пайплайнам и компонентам доступна через соответствующие INDEX.md файлы.
