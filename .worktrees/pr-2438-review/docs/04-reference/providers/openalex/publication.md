# Пайплайн: OpenAlex Publication

**Имя пайплайна:** `openalex_publication`
**Провайдер:** `openalex`
**Сущность:** `publication` (API-термин: `work`)
**Версия схемы:** 1.2.0

----------------------------------------------------------------------

## 1. Описание

Пайплайн выполняет пакетную резолюцию DOI через OpenAlex Works API с поддержкой поиска по заголовку при отсутствии DOI или его невалидности. Используется для обогащения публикаций метаданными об открытом доступе, цитированиях и концептах.

### Основные сценарии использования

1. **Резолюция DOI** — получение полных метаданных публикаций по списку DOI
1. **Обогащение документов ChEMBL** — добавление Open Access статуса и метрик цитирования
1. **Fallback по заголовку** — поиск публикаций, когда DOI недоступен или не найден

### Терминология

- **Publication** — внутренний термин BioETL (Ubiquitous Language)
- **Work** — термин OpenAlex API
- Оба термина обозначают одну сущность — научную публикацию

----------------------------------------------------------------------

## 2. Ключевые поля

### Идентификаторы

| Поле          | Тип           | Описание                                              |
| ------------- | ------------- | ----------------------------------------------------- |
| `openalex-id` | `str`         | OpenAlex Work ID (e.g., W2148763428) — первичный ключ |
| `doi`         | `str \| None` | Digital Object Identifier (нормализованный)           |

### Метаданные публикации

| Поле        | Тип           | Описание                                         |
| ----------- | ------------- | ------------------------------------------------ |
| `title`     | `str \| None` | Название публикации                              |
| `abstract`  | `str \| None` | Аннотация (реконструированная из inverted index) |
| `authors`   | `list[str]`   | Список авторов (опционально хэшируются как PII)  |
| `journal`   | `str \| None` | Название журнала/источника                       |
| `issn`      | `str \| None` | ISSN-L журнала                                   |
| `publisher` | `str \| None` | Название издателя                                |

### Даты и тип

| Поле               | Тип           | Описание                                                     |
| ------------------ | ------------- | ------------------------------------------------------------ |
| `year`             | `int \| None` | Год публикации (валидируется: 1900-2100)                     |
| `publication-date` | `str \| None` | Дата публикации (YYYY-MM-DD)                                 |
| `doc-type`         | `str`         | Тип документа: `PUBLICATION`, `PREPRINT`, `DATASET`, `OTHER` |

### Open Access

| Поле        | Тип            | Описание                                                 |
| ----------- | -------------- | -------------------------------------------------------- |
| `is-oa`     | `bool \| None` | Публикация в открытом доступе                            |
| `oa-status` | `str \| None`  | Статус OA: `gold`, `green`, `hybrid`, `bronze`, `closed` |

### Авторы и идентификаторы

| Поле                | Тип           | Описание                                                     |
| ------------------- | ------------- | ------------------------------------------------------------ |
| `author-keys`       | `str \| None` | Нормализованные ключи авторов (`Surname-F`), разделённые `\|`|
| `author-openalex-ids` | `str \| None` | JSON-массив OpenAlex author IDs                            |
| `author-orcids`     | `str \| None` | JSON-массив ORCID идентификаторов                            |
| `affiliation-list`  | `str \| None` | JSON-массив аффилиаций                                       |

### Метрики и классификация

| Поле                | Тип           | Описание                                  |
| ------------------- | ------------- | ----------------------------------------- |
| `citations-received`| `int \| None` | Количество цитирований                    |
| `publication-class` | `str`         | Класс публикации: EXP, REV, PEER         |
| `publication-type`  | `str \| None` | Сырой тип OpenAlex (article, book, и т.д.)|
| `subject-topics`    | `str \| None` | JSON-массив тем (4-уровневая иерархия)    |
| `primary-topic`     | `str \| None` | Основная тема                             |
| `language`          | `str \| None` | Код языка публикации                      |

### Метаданные резолюции

| Поле             | Тип           | Описание                                                |
| ---------------- | ------------- | ------------------------------------------------------- |
| `-lookup-method` | `str`         | Метод резолюции: `doi`, `title-fallback`, `title-only`  |
| `-original-doi`  | `str \| None` | Оригинальный DOI из входного CSV (для fallback записей) |

----------------------------------------------------------------------

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py`

### Извлечение полей

Трансформер делегирует извлечение полей в `extractors.py`:

| Функция                      | Назначение                                                |
| ---------------------------- | --------------------------------------------------------- |
| `extract-openalex-id()`      | Извлечение ID из URL (https://openalex.org/W... → W...)   |
| `extract-doi()`              | Нормализация DOI (удаление https://doi.org/)              |
| `reconstruct-abstract()`     | Реконструкция абстракта из inverted index                 |
| `extract-authors()`          | Извлечение display-name из authorships                    |
| `extract-topics()`           | Иерархическая классификация (domain/field/subfield/topic) |
| `extract-primary-topic()`    | Основная тема для быстрой категоризации                   |
| `extract-journal-info()`     | Журнал, ISSN-L, издатель из primary-location              |
| `extract-open-access-info()` | is-oa и oa-status из open-access                          |

### Маппинг типов документов

| OpenAlex type                | Internal type |
| ---------------------------- | ------------- |
| `article`, `journal-article` | `PUBLICATION` |
| `book-chapter`, `book`       | `PUBLICATION` |
| `proceedings-article`        | `PUBLICATION` |
| `preprint`, `posted-content` | `PREPRINT`    |
| `dataset`                    | `DATASET`     |
| `other`                      | `OTHER`       |

### Entity ID

```python
# Формат entity-id
entity-id = f"openalex:{openalex-id}"
```

### Content Hash

Вычисляется по бизнес-полям публикации для дедупликации:

- Исключаются lookup-метаданные (`-lookup-method`, `-original-doi`)
- Исключаются lineage-поля (`-run-id`, `-ingestion-ts`, etc.)
- None-значения исключаются из хэша

----------------------------------------------------------------------

## 4. Особенности

### Rate Limiting

OpenAlex предоставляет "polite pool" с повышенными лимитами:

| Режим             | Лимит      | Условие                                |
| ----------------- | ---------- | -------------------------------------- |
| Без идентификации | 10 req/sec | Базовый доступ                         |
| С `mailto`        | 10 req/sec | Указан email в User-Agent и параметрах |

**Важно:** Переменная окружения `BIOETL-OPENALEX-EMAIL` обязательна для production.

### Batch DOI Resolution

Пайплайн поддерживает пакетную резолюцию DOI:

- До 50 DOI в одном запросе через `filter=doi:doi1|doi2|...`
- Значительно эффективнее индивидуальных запросов
- Pipe (`|`) используется как разделитель DOI

### Fallback by Title

При неудачной резолюции DOI:

1. Если в `fallback-mapping` есть заголовок для DOI
1. Выполняется поиск по заголовку: `title.search:Publication+Title`
1. Специальные символы экранируются: `:`, `|`, `,` удаляются, пробелы → `+`
1. Возвращается запись с `-lookup-method = "title-fallback"` или `"title-only"`

### Title-Only Lookup

Когда DOI пустой во входном CSV:

- Поиск выполняется только по заголовку
- `-lookup-method = "title-only"`
- `-original-doi` остаётся пустым

### Abstract Reconstruction

OpenAlex API возвращает абстракты в формате inverted index:

```json
{
  "abstract-inverted-index": {
    "This": [0],
    "is": [1],
    "an": [2],
    "abstract": [3]
  }
}
```

Трансформер реконструирует полный текст: `"This is an abstract"`.

### Конфигурация Input Filter

```yaml
input-filter:
  enabled: true
  source-path: "data/input/dois.csv"
  column-name: "doi"
  filter-field: "doi"
  batch-size: 50
  fallback-column: "title"  # Поиск по заголовку при неудаче DOI
```

----------------------------------------------------------------------

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run openalex_publication

# С ограничением количества записей
bioetl run openalex_publication --limit 100

# Проверка конфигурации без выполнения
bioetl run openalex_publication --dry-run

# Полная перезагрузка
bioetl run openalex_publication --run-type rebuild
```

### Подготовка входных данных

Создайте CSV-файл `data/input/dois.csv`:

```csv
doi,title
10.1038/s41586-020-2012-7,A pneumonia outbreak associated with a new coronavirus
10.1016/j.cell.2020.02.052,Structure of SARS-CoV-2 spike protein
,COVID-19 vaccine development
```

**Примечание:** Пустой DOI допустим при наличии заголовка для title-only lookup.

### Переменные окружения

| Переменная              | Описание              | Обязательна |
| ----------------------- | --------------------- | ----------- |
| `BIOETL-OPENALEX-EMAIL` | Email для polite pool | Да          |

----------------------------------------------------------------------

## 6. Health Check

OpenAlex adapter реализует health check через `/works?per-page=1`:

| Статус      | Условие                  |
| ----------- | ------------------------ |
| `HEALTHY`   | Ответ 200 за < 5 сек     |
| `DEGRADED`  | Ответ 200 за > 5 сек     |
| `UNHEALTHY` | Ошибка или не-200 статус |

----------------------------------------------------------------------

## 7. Error Handling

### Recoverable Errors

| Код        | Поведение                                |
| ---------- | ---------------------------------------- |
| 429        | Rate limit — retry с exponential backoff |
| 502/504    | Timeout — retry (max 3)                  |
| Batch fail | Fallback на индивидуальные запросы       |

### Critical Errors

| Код     | Поведение                       |
| ------- | ------------------------------- |
| 401/403 | Auth failure — fail immediately |

### Data Quality

| Условие                 | Поведение                 |
| ----------------------- | ------------------------- |
| Missing openalex-id     | Skip record (log warning) |
| Invalid year range      | Set year = None           |
| Empty title in fallback | Skip title search         |

----------------------------------------------------------------------

## 8. Gold Filters

```yaml
gold-filters:
  required-fields:
    - openalex-id
    - title
  ranges:
    year:
      min: 1500
      max: 2100
```

----------------------------------------------------------------------

## 9. Связанные файлы

| Компонент              | Путь                                                       |
| ---------------------- | ---------------------------------------------------------- |
| Конфигурация пайплайна | `configs/entities/openalex/publication.yaml`              |
| Конфигурация источника | `configs/providers/openalex.yaml`                            |
| Трансформер            | `src/bioetl/application/pipelines/openalex/transformer.py` |
| Экстракторы            | `src/bioetl/application/pipelines/openalex/extractors.py`  |
| Адаптер                | `src/bioetl/infrastructure/adapters/openalex/client.py`    |
| Fallback Handler       | `src/bioetl/infrastructure/adapters/openalex/fallback.py`  |
| Domain Entity          | `src/bioetl/domain/entities/openalex.py`                   |
| Gold Schema            | `src/bioetl/infrastructure/schemas/gold.py`                |

----------------------------------------------------------------------

## 10. Примеры данных

### Bronze Record (API Response)

```json
{
  "id": "https://openalex.org/W2148763428",
  "doi": "https://doi.org/10.1038/s41586-020-2012-7",
  "title": "A pneumonia outbreak associated with a new coronavirus of probable bat origin",
  "abstract-inverted-index": {
    "A": [0], "pneumonia": [1], "outbreak": [2], "...": [3]
  },
  "authorships": [
    {"author": {"display-name": "Peng Zhou"}},
    {"author": {"display-name": "Xing-Lou Yang"}}
  ],
  "primary-location": {
    "source": {
      "display-name": "Nature",
      "issn-l": "0028-0836",
      "host-organization-name": "Springer Nature"
    }
  },
  "publication-year": 2020,
  "publication-date": "2020-02-03",
  "type": "journal-article",
  "open-access": {
    "is-oa": true,
    "oa-status": "gold"
  },
  "cited-by-count": 15000,
  "concepts": [
    {"display-name": "Coronavirus", "score": 0.95},
    {"display-name": "Virology", "score": 0.88}
  ],
  "language": "en"
}
```

### Silver Record (Transformed)

```json
{
  "entity-id": "openalex:W2148763428",
  "openalex-id": "W2148763428",
  "doi": "10.1038/s41586-020-2012-7",
  "title": "A pneumonia outbreak associated with a new coronavirus of probable bat origin",
  "abstract": "A pneumonia outbreak...",
  "authors": ["Peng Zhou", "Xing-Lou Yang"],
  "journal": "Nature",
  "issn": "0028-0836",
  "publisher": "Springer Nature",
  "year": 2020,
  "publication-date": "2020-02-03",
  "doc-type": "PUBLICATION",
  "is-oa": true,
  "oa-status": "gold",
  "cited-by-count": 15000,
  "concepts": ["Coronavirus", "Virology"],
  "language": "en",
  "-lookup-method": "doi",
  "-original-doi": null,
  "source": "openalex",
  "content-hash": "sha256:abc123...",
  "-run-id": "run-2026-01-06-001",
  "-run-type": "incremental",
  "-ingestion-ts": "2026-01-06T12:00:00Z"
}
```

### Fallback Record Example

```json
{
  "entity-id": "openalex:W3045876123",
  "openalex-id": "W3045876123",
  "doi": "10.1016/j.example.2020.001",
  "title": "Example Publication Title",
  "-lookup-method": "title-fallback",
  "-original-doi": "10.1016/j.example.2020.001",
  "...": "..."
}
```

----------------------------------------------------------------------

## 11. Тестирование

### Unit Tests

| Файл                                                            | Покрытие                           |
| --------------------------------------------------------------- | ---------------------------------- |
| `tests/unit/infrastructure/adapters/openalex/test-adapter.py`   | Adapter methods, DOI normalization |
| `tests/unit/infrastructure/adapters/openalex/test-fallback.py`  | Fallback logic                     |
| `tests/unit/application/pipelines/openalex/test-extractors.py`  | All extractors                     |
| `tests/unit/application/pipelines/openalex/test-transformer.py` | Transformation flow                |

### Integration Tests

| Файл                                                   | Покрытие                |
| ------------------------------------------------------ | ----------------------- |
| `tests/integration/adapters/openalex/test-adapter.py`  | HTTP interactions (VCR) |
| `tests/integration/adapters/openalex/test-pipeline.py` | Transformer extractors  |

**VCR Configuration** (для test-adapter.py):

```python
{
    "cassette-library-dir": "tests/fixtures/vcr/openalex",
    "record-mode": "none",
    "match-on": ["method", "scheme", "host", "port", "path", "query"],
    "filter-query-parameters": ["mailto"],
}
```

----------------------------------------------------------------------

## 12. Архитектура

### Hexagonal Architecture Compliance

```
┌─────────────────────────────────────────────────────────────┐
│                       DOMAIN                                │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │ OpenAlexPubli-  │    │ DataSourcePort               │   │
│  │ cationEntity    │    │ FilterableDataSourcePort     │   │
│  └─────────────────┘    └──────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     APPLICATION                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ OpenAlexPublicationTransformer                      │   │
│  │   └─ extractors.py (pure functions)                 │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                           │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │ OpenAlexAdapter │    │ UnifiedHTTPClient            │   │
│  │   └─ fallback   │    │   └─ TokenBucket             │   │
│  └─────────────────┘    │   └─ CircuitBreaker          │   │
│                         └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Input CSV → OpenAlexAdapter.fetch-filtered-with-fallback()
    ├─ Batch DOI lookup (filter=doi:doi1|doi2|...)
    ├─ Title fallback for missing DOIs
    └─ Yield raw records with -lookup-method

Raw Records → OpenAlexPublicationTransformer.-transform-impl()
    ├─ Extract business data (extractors.py)
    ├─ Validate required fields
    ├─ Compute entity-id and content-hash
    └─ Create OpenAlexPublicationEntity

Entity → SilverWriter (Delta Lake)
    └─ Upsert by content-hash

Silver → GoldWriter (validated)
    └─ Apply gold-filters, export CSV
```

----------------------------------------------------------------------

*Последнее обновление: 2026-02-16*
