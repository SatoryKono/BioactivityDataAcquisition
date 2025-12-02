# REST API Sources Integration

План интеграции внешних источников данных.

## Текущий статус

| Источник | Статус | Сущности | Описание |
|----------|--------|----------|----------|
| **ChEMBL** | ✅ Production | Activity, Assay, Target, TestItem, Document | Основной источник данных биоактивности. |
| **Semantic Scholar** | ✅ Enrichment | Document (Abstracts) | Обогащение публикаций аннотациями. |
| **PubMed** | ✅ Enrichment | Document (Metadata) | Метаданные статей (MeSH terms). |
| **CrossRef** | ✅ Enrichment | Document (DOI) | Разрешение DOI, получение библиографии. |

## Планируемые интеграции

### 1. PubChem
- **Сущности**: TestItem (Compounds).
- **Цель**: Получение физико-химических свойств, кросс-ссылок.
- **Метод**: PUG REST API.

### 2. UniProt
- **Сущности**: Target (Proteins).
- **Цель**: Получение последовательностей, функций белков, GO-терминов.
- **Метод**: UniProt REST API.

### 3. IUPHAR Guide to Pharmacology
- **Сущности**: Target, Interaction.
- **Цель**: Данные о рецепторах и каналах.
- **Метод**: GtoP Web Services.

### 4. OpenAlex
- **Сущности**: Document.
- **Цель**: Построение графа цитирований, альтернатива Semantic Scholar.
- **Метод**: OpenAlex API.

## Архитектура интеграции

Для каждого нового источника необходимо создать:
1. **Client**: Наследник `BaseClient` с реализацией `_build_request` и `_parse_response`.
2. **Schema**: Pandera-схема для валидации ответа.
3. **Pipeline**: Наследник `PipelineBase`, использующий этот клиент.

Все источники интегрируются через единый интерфейс `PipelineBase`, что позволяет унифицировать запуск, логирование и обработку ошибок.

