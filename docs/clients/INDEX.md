# Clients Documentation

Документация клиентского слоя BioETL для работы с внешними источниками данных.

## Основные документы

- **00-clients-overview.md** — Обзор архитектуры клиентского слоя, структура пакета, основные компоненты и примеры использования
- **02-rest-yaml-migration.md** — Детали миграции REST-клиентов на YAML-конфигурации
- **19-clients-diagrams.md** — Инструкция по генерации диаграмм объектов для пакета clients

## Клиенты конкретных источников

Документация по клиентам внешних API находится в `docs/02-pipelines/clients/`:

- `18-pubmed-client.md` — клиент для API PubMed
- `19-crossref-client.md` — клиент для API CrossRef
- `20-pubchem-client.md` — клиент для PubChem
- `21-configured-http-client.md` — базовая реализация настроенного HTTP-клиента
- `22-semantic-scholar-client.md` — клиент для API Semantic Scholar
- `23-uniprot-client.md` — клиент для REST API UniProt

## Связанная документация

- **Styleguide**: `docs/00-styleguide/00-rules-summary.md` — правила именования и стиля кода
- **ABC Index**: `docs/01-ABC/INDEX.md` — каталог абстрактных базовых классов

## Быстрый старт

Начните с **00-clients-overview.md** для понимания архитектуры и основных компонентов клиентского слоя.
