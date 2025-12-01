# BioactivityDataAcquisition

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## Правила проекта

Проект следует строгим правилам именования, архитектуры и документации:

- **Основные правила**: `.cursorrules` — правила для AI-ассистента и разработчиков
- **Краткая сводка**: `docs/00-styleguide/RULES_QUICK_REFERENCE.md` — быстрый справочник
- **Memories**: `docs/00-styleguide/MEMORIES.md` — ключевые правила для запоминания

## Документация

Полная документация по стилю и правилам находится в `docs/00-styleguide/`:

- `00-naming-conventions.md` — именование документации
- `01-new-entity-implementation-policy.md` — политика создания ABC/Default/Impl
- `02-new-entity-naming-policy.md` — полная политика именования
- `10-documentation-standards.md` — стандарты документации

### Пайплайны и core компоненты

Документация по пайплайнам и базовым компонентам находится в `docs/02-pipelines/`:

- `00-pipeline-base.md` — базовая архитектура пайплайнов
- `01-base-external-data-client.md` — базовый клиент внешних API
- `02-logging-and-configuration.md` — логирование и конфигурация
- `03-unified-api-client.md` — унифицированный API-клиент и HTTP-адаптеры
- `04-unified-output-writer.md` — унифицированный writer для записи результатов
- `05-schema-registry.md` — реестр схем для валидации данных

#### ChEMBL Activity Pipeline

Документация по пайплайну ChEMBL Activity находится в `docs/02-pipelines/chembl/activity/`:

- `00-activity-chembl-overview.md` — обзор пайплайна ChEMBL Activity
- `01-activity-chembl-extract.md` — стадия извлечения данных
- `02-activity-chembl-transform.md` — стадия трансформации данных
- `03-activity-chembl-write.md` — стадия записи результатов
- `04-activity-chembl-parser.md` — парсер ответов ChEMBL API
- `05-activity-chembl-normalizer.md` — нормализатор данных активности
- `07-activity-chembl-descriptor.md` — дескриптор параметров извлечения
- `08-base-chembl-normalizer.md` — базовый нормализатор для ChEMBL
- `09-activity-chembl-batch-plan.md` — план батчирования запросов
- `10-activity-chembl-column-spec.md` — спецификация нормализации колонок
- `11-activity-chembl-column-mapping.md` — маппинг полей JSON на колонки
- `12-activity-chembl-schema.md` — Pandera-схема для валидации данных
- `13-activity-chembl-artifacts.md` — планировщик и сервис артефактов

#### ChEMBL Client Components

Документация по компонентам клиента ChEMBL находится в `docs/02-pipelines/chembl/`:

- `14-chembl-client.md` — REST-клиент для ChEMBL API
- `15-chembl-request-builder.md` — построитель запросов ChEMBL
- `16-requests-backend.md` — HTTP-бэкенд на основе requests
- `17-chembl-write-service.md` — сервис записи для ChEMBL-пайплайнов

#### Другие ChEMBL пайплайны

- `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md` — пайплайн для assay
- `docs/02-pipelines/chembl/target/00-target-chembl-overview.md` — пайплайн для target
- `docs/02-pipelines/chembl/document/00-document-chembl-overview.md` — пайплайн для document
- `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md` — пайплайн для testitem

#### Клиенты внешних API

Документация по клиентам внешних API находится в `docs/02-pipelines/clients/`:

- `18-pubmed-client.md` — клиент для API PubMed
- `19-crossref-client.md` — клиент для API CrossRef
- `20-pubchem-client.md` — клиент для PubChem
- `21-configured-http-client.md` — базовая реализация настроенного HTTP-клиента
- `22-semantic-scholar-client.md` — клиент для API Semantic Scholar

#### HTTP компоненты

Документация по HTTP компонентам находится в `docs/02-pipelines/http/`:

- `23-http-cache.md` — кэш HTTP-ответов с TTL
- `24-rate-limiter.md` — лимитер частоты запросов
- `25-retry-policy.md` — политика повторных попыток
- `26-circuit-breaker.md` — Circuit Breaker для устойчивости
- `27-pagination-strategy.md` — стратегия пагинации

#### Конфигурация

Документация по компонентам конфигурации находится в `docs/02-pipelines/config/`:

- `28-config-resolver.md` — резолвер конфигурации из YAML
- `29-secret-provider.md` — провайдер секретов из переменных окружения

### CLI и запуск пайплайнов

Документация по использованию CLI находится в `docs/03-cli/`:

- `00-cli-overview.md` — обзор CLI и архитектуры
- `01-cli-commands.md` — описание команд и примеры использования