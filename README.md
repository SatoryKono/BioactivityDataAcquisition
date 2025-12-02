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

Краткая структура документации (полные списки поддерживаются в индексах каталогов):

- `docs/01-ABC/INDEX.md` — человекочитаемый каталог ABC, Default и Impl
- `docs/02-pipelines/` — пайплайны и core-компоненты; индекс ChEMBL-компонентов: `docs/02-pipelines/chembl/INDEX.md` (отдельные пайплайны activity, assay, target, document, testitem используют собственные `INDEX.md` в подкаталогах)
- `docs/clients/INDEX.md` — клиентский слой и вспомогательные утилиты
- `docs/cli/INDEX.md` — CLI и запуск пайплайнов
- `docs/qc/INDEX.md` — артефакты контроля качества
- `docs/schemas/INDEX.md` — реестр схем данных

### Пайплайны и core компоненты

Документация по пайплайнам и базовым компонентам находится в `docs/02-pipelines/`. Общие принципы описаны в базовых гайдах (например, `00-pipeline-base.md`, `01-base-external-data-client.md`, `02-logging-and-configuration.md`, `03-unified-api-client.md`, `04-unified-output-writer.md`, `05-schema-registry.md`). Полный список ChEMBL-пайплайнов и общих компонентов поддерживается в `docs/02-pipelines/chembl/INDEX.md`; отдельные пайплайны (activity, assay, target, document, testitem) используют собственные `INDEX.md` в соответствующих подкаталогах.

### CLI и запуск пайплайнов

Полное содержание документации по CLI доступно в `docs/cli/INDEX.md`.

### Клиенты внешних источников

Полный перечень клиентских материалов поддерживается в `docs/clients/INDEX.md`.

### Quality Control (QC)

Список QC-артефактов и описаний поддерживается в `docs/qc/INDEX.md`.

### Схемы данных

Перечень схем и их описания поддерживается в `docs/schemas/INDEX.md`.
