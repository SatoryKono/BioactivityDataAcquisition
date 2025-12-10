# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации. Актуальная сводка правил: `docs/project/00-rules-summary.md`.

## Локальные проверки качества

- Установить хуки: `pre-commit install`
- Прогнать форматирование и линтеры: `pre-commit run --all-files` (ruff, black, isort, mypy, import-linter)
- Запустить архитектурный тест: `pytest tests/architecture/test_layer_dependencies.py`
- Полный цикл lint/type-check в CI: ruff → black --check → isort --check-only → mypy → архитектурные тесты → import-linter

## Запуск тестов

Быстрый старт:

```bash
# Unit-тесты (быстрые, без сети)
npm test

# Все тесты с покрытием (минимум 85%)
npm run test:coverage
```

Доступные команды:
- `npm test` / `npm run test:unit` - unit-тесты
- `npm run test:integration` - интеграционные тесты
- `npm run test:golden` - golden-тесты
- `npm run test:all` - все тесты
- `npm run test:coverage` - все тесты с покрытием

Подробнее: [docs/guides/00-running-tests.md](docs/guides/00-running-tests.md)

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

## Representations of ChEMBL data

- Единственный источник правды для сущностей — Pandera-схемы (`ActivityTableSchema`, `AssayTableSchema`, `MoleculeTableSchema` и др.).
- Сырые JSON-ответы ChEMBL сплющиваются утилитой `flatten_chembl_payload` (`src/bioetl/infrastructure/clients/chembl/serializers.py`) с набором bypass-полей для вложенных структур.
- Pydantic Raw* модели удалены; нормализация и валидация работают с dict → DataFrame → Pandera.
- В `ChemblExtractionServiceImpl` flatten включён по умолчанию, при необходимости может быть отключён параметром `flatten_enabled`.

### Core компоненты

Документация по базовым компонентам находится в `docs/02-pipelines/`:

| # | Документ | Описание |
|---|----------|----------|
| 00 | [index](docs/02-pipelines/00-index.md) | Навигация по core-документации пайплайнов |
| 01 | [pipeline-core-normalization](docs/02-pipelines/01-pipeline-core-normalization.md) | Архитектура сервисов нормализации, базовые и ChEMBL-специфичные реализации |
| 02 | [pipeline-core-provider-registry](docs/02-pipelines/02-pipeline-core-provider-registry.md) | Провайдерский реестр, orchestrator-порт загрузчика и фабрики |

### Пайплайны по провайдерам

- [ChEMBL Pipelines](docs/02-pipelines/chembl/00-index.md) — Activity, Assay, Target, Document, Molecule

Детальная документация по конкретным пайплайнам и компонентам доступна через соответствующие INDEX.md файлы.
