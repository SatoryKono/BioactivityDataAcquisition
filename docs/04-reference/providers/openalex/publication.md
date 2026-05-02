______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-28'

______________________________________________________________________

# Пайплайн: OpenAlex Publication

**Имя пайплайна:** `openalex_publication`
**Провайдер:** `openalex`
**Сущность:** `publication` (API-термин: `work`)
**Версия схемы:** 1.2.0

______________________________________________________________________

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

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле          | Тип           | Описание                                              |
| ------------- | ------------- | ----------------------------------------------------- |
| `openalex_id` | `str`         | OpenAlex Work ID (e.g., W2148763428) — первичный ключ |
| `doi`         | `str \| None` | Digital Object Identifier (нормализованный)           |

### Метаданные публикации

| Поле        | Тип           | Описание                                         |
| ----------- | ------------- | ------------------------------------------------ |
| `title`     | `str \| None` | Название публикации                              |
| `abstract`  | `str \| None` | Аннотация (реконструированная из inverted index) |
| `authors`   | `str \| None` | JSON-массив авторов (опционально хэшируются как PII) |
| `journal`   | `str \| None` | Название журнала/источника                       |
| `issn`      | `str \| None` | ISSN-L журнала                                   |
| `publisher` | `str \| None` | Название издателя                                |

### Даты и тип

| Поле               | Тип           | Описание                                                             |
| ------------------ | ------------- | -------------------------------------------------------------------- |
| `publication_year` | `int \| None` | Год публикации (валидируется: 1500-2100)                             |
| `publication_date` | `str \| None` | Дата публикации (YYYY-MM-DD)                                         |
| `publication_type` | `str \| None` | Нормализованный тип OpenAlex (`journal-article`, `preprint`, и т.д.) |

### Open Access

| Поле        | Тип            | Описание                                                 |
| ----------- | -------------- | -------------------------------------------------------- |
| `is_oa`     | `bool \| None` | Публикация в открытом доступе                            |
| `oa_status` | `str \| None`  | Статус OA: `gold`, `green`, `hybrid`, `bronze`, `closed` |

### Авторы и идентификаторы

| Поле                  | Тип           | Описание                                                      |
| --------------------- | ------------- | ------------------------------------------------------------- |
| `author_keys`         | `str \| None` | Нормализованные ключи авторов (`Surname-F`), разделённые `\|` |
| `author_openalex_ids` | `str \| None` | JSON-массив OpenAlex author IDs                               |
| `author_orcids`       | `str \| None` | JSON-массив ORCID идентификаторов                             |
| `affiliation_list`    | `str \| None` | JSON-массив аффилиаций                                        |

### Метрики и классификация

| Поле                       | Тип           | Описание                                                           |
| -------------------------- | ------------- | ------------------------------------------------------------------ |
| `citations_received`       | `int \| None` | Количество цитирований                                             |
| `publication_class`        | `str`         | Класс публикации: EXP, REV, PEER                                   |
| `publication_type`         | `str \| None` | Сырой тип OpenAlex (article, book, и т.д.)                         |
| `publication_type_unified` | `str`         | Унифицированный тип: `PUBLICATION`, `PREPRINT`, `DATASET`, `OTHER` |
| `subject_topics`           | `str \| None` | JSON-массив тем (4-уровневая иерархия)                             |
| `primary_topic`            | `str \| None` | Основная тема                                                      |
| `language`                 | `str \| None` | Код языка публикации                                               |

### Метаданные резолюции

| Поле             | Тип           | Описание                                                |
| ---------------- | ------------- | ------------------------------------------------------- |
| `_lookup_method` | `str`         | Метод резолюции: `doi`, `title_fallback`, `title_only`  |
| `_original_id`   | `str \| None` | Оригинальный DOI из входного CSV (для fallback записей) |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py`

### Извлечение полей

Трансформер делегирует извлечение полей в `extractors.py`:

| Функция                      | Назначение                                                |
| ---------------------------- | --------------------------------------------------------- |
| `extract_openalex_id()`      | Извлечение ID из URL (https://openalex.org/W... → W...)   |
| `extract_doi()`              | Нормализация DOI (удаление https://doi.org/)              |
| `reconstruct_abstract()`     | Реконструкция абстракта из inverted index                 |
| `extract_authors()`          | Извлечение display_name из authorships                    |
| `extract_topics()`           | Иерархическая классификация (domain/field/subfield/topic) |
| `extract_primary_topic()`    | Основная тема для быстрой категоризации                   |
| `extract_journal_info()`     | Журнал, ISSN-L, издатель из primary_location              |
| `extract_open_access_info()` | is_oa и oa_status из open_access                          |

### Маппинг типов документов

| OpenAlex type                | Internal type |
| ---------------------------- | ------------- |
| `article`, `journal-article` | `PUBLICATION` |
| `book-chapter`, `book`       | `PUBLICATION` |
| `proceedings-article`        | `PUBLICATION` |
| `preprint`, `posted-content` | `PREPRINT`    |
| `dataset`                    | `DATASET`     |
| `other`                      | `OTHER`       |

> **Note**: Internal type mapping is part of [Internal/Extended Material](#internalextended-material)

### Entity ID

```python
# Формат entity_id
entity_id = f"openalex:{openalex_id}"
```

### Content Hash

Вычисляется по бизнес-полям публикации для дедупликации:

- Исключаются lookup-метаданные (`_lookup_method`, `_original_id`)
- Исключаются occurrence-scoped provenance anchors (`_run_id`, `_run_type`,
  `_source_batch_id`, `_ingestion_ts` и др.)
- Эти anchors могут фигурировать в config/hash-policy inventories, но не входят
  в persisted Silver/Gold row contract и публикуются через sidecar/control-plane
  artifacts
- None-значения исключаются из хэша

______________________________________________________________________

## 4. Особенности

### Rate Limiting

OpenAlex использует API key и credit-based rate limiting. `mailto` больше не
является основным механизмом доступа и сохраняется в BioETL только как
дополнительный contact/attribution параметр.

| Режим                     | Лимит BioETL | Условие                                           |
| ------------------------- | ------------ | ------------------------------------------------- |
| Production/API key        | 10 req/sec   | `BIOETL_OPENALEX_API_KEY` задан                   |
| Contact attribution only  | Not supported as production boundary | `BIOETL_OPENALEX_EMAIL` задан без API key |

**Важно:** Для production-подобных запусков требуется
`BIOETL_OPENALEX_API_KEY`. Переменная `BIOETL_OPENALEX_EMAIL` опциональна и не
заменяет API key.

### Funding Fields

OpenAlex удалил legacy поле `grants` из Work object. BioETL сохраняет
каноническое выходное поле `grants`, но наполняет его из текущих OpenAlex
`awards` и `funders`; legacy `grants` используется только как fallback для
старых кассет/снапшотов.

### Batch DOI Resolution

Пайплайн поддерживает пакетную резолюцию DOI:

- До 50 DOI в одном запросе через `filter=doi:doi1|doi2|...`
- Значительно эффективнее индивидуальных запросов
- Pipe (`|`) используется как разделитель DOI

### Fallback by Title

При неудачной резолюции DOI:

1. Если в `fallback_mapping` есть заголовок для DOI
1. Выполняется поиск по заголовку: `title.search:Publication+Title`
1. Специальные символы экранируются: `:`, `|`, `,` удаляются, пробелы → `+`
1. Возвращается запись с `_lookup_method = "title_fallback"` или `"title_only"`

### Title-Only Lookup

Когда DOI пустой во входном CSV:

- Поиск выполняется только по заголовку
- `_lookup_method = "title_only"`
- `_original_id` остаётся пустым

### Abstract Reconstruction

OpenAlex API возвращает абстракты в формате inverted index:

```json
{
  "abstract_inverted_index": {
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
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 50
  fallback_column: "title"  # Поиск по заголовку при неудаче DOI
```

______________________________________________________________________

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run --pipeline openalex_publication

# С ограничением количества записей
bioetl run --pipeline openalex_publication --limit 100

# Проверка конфигурации без выполнения
bioetl run --pipeline openalex_publication --dry-run

# Полная перезагрузка
bioetl run --pipeline openalex_publication --run-type rebuild
```

### Подготовка входных данных

Создайте CSV-файл `data/input/dois.csv`:

```csv
doi,title
10.1038/s41586-020-2012-7,A pneumonia outbreak associated with a new coronavirus
10.1016/j.cell.2020.02.052,Structure of SARS-CoV-2 spike protein
,COVID-19 vaccine development
```

**Примечание:** Пустой DOI допустим при наличии заголовка для title_only lookup.

### Переменные окружения

| Переменная                 | Описание                                   | Обязательна |
| -------------------------- | ------------------------------------------ | ----------- |
| `BIOETL_OPENALEX_API_KEY`  | OpenAlex API key for production-like runs  | Да          |
| `BIOETL_OPENALEX_EMAIL`    | Optional contact attribution metadata      | Нет         |

______________________________________________________________________

## 6. Health Check

OpenAlex adapter реализует health check через `/works?per-page=1`:

| Статус      | Условие                  |
| ----------- | ------------------------ |
| `HEALTHY`   | Ответ 200 за < 5 сек     |
| `DEGRADED`  | Ответ 200 за > 5 сек     |
| `UNHEALTHY` | Ошибка или не-200 статус |

______________________________________________________________________

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

| Условие                 | Поведение                   |
| ----------------------- | --------------------------- |
| Missing openalex_id     | Skip record (log warning)   |
| Invalid year range      | Set publication_year = None |
| Empty title in fallback | Skip title search           |

______________________________________________________________________

## 8. Gold Filters

```yaml
gold_filters:
  required_fields:
    - openalex_id
    - title
  ranges:
    publication_year:
      min: 1950
      max: 2050
```

______________________________________________________________________

## 9. Связанные файлы

| Компонент              | Путь                                                       |
| ---------------------- | ---------------------------------------------------------- |
| Конфигурация пайплайна | `configs/entities/openalex/publication.yaml`               |
| Конфигурация источника | `configs/providers/openalex.yaml`                          |
| Трансформер            | `src/bioetl/application/pipelines/openalex/transformer.py` |
| Экстракторы            | `src/bioetl/application/pipelines/openalex/extractors.py`  |
| Адаптер                | `src/bioetl/infrastructure/adapters/openalex/client.py`    |
| Fallback Handler       | `src/bioetl/infrastructure/adapters/openalex/fallback.py`  |
| Domain Entity          | `src/bioetl/domain/entities/openalex.py`                   |
| Gold Schema            | `src/bioetl/domain/schemas/openalex/publication.py`        |

______________________________________________________________________

## 10. Примеры данных

### Bronze Record (API Response)

```json
{
  "id": "https://openalex.org/W2148763428",
  "doi": "https://doi.org/10.1038/s41586-020-2012-7",
  "title": "A pneumonia outbreak associated with a new coronavirus of probable bat origin",
  "abstract_inverted_index": {
    "A": [0], "pneumonia": [1], "outbreak": [2], "...": [3]
  },
  "authorships": [
    {"author": {"display_name": "Peng Zhou"}},
    {"author": {"display_name": "Xing-Lou Yang"}}
  ],
  "primary_location": {
    "source": {
      "display_name": "Nature",
      "issn_l": "0028-0836",
      "host_organization_name": "Springer Nature"
    }
  },
  "publication_year": 2020,
  "publication_date": "2020-02-03",
  "type": "journal-article",
  "open_access": {
    "is_oa": true,
    "oa_status": "gold"
  },
  "cited_by_count": 15000,
  "concepts": [
    {"display_name": "Coronavirus", "score": 0.95},
    {"display_name": "Virology", "score": 0.88}
  ],
  "language": "en"
}
```

### Silver Record (Transformed)

```json
{
  "entity_id": "openalex:W2148763428",
  "openalex_id": "W2148763428",
  "doi": "10.1038/s41586-020-2012-7",
  "pmid": "32015507",
  "pmc_id": null,
  "mag_id": "3004922785",
  "title": "A pneumonia outbreak associated with a new coronavirus of probable bat origin",
  "abstract": "A pneumonia outbreak...",
  "authors": "[\"Peng Zhou\", \"Xing-Lou Yang\"]",
  "author_keys": "zhou_p|yang_xl",
  "author_openalex_ids": "[\"A5074809391\", \"A5015691179\"]",
  "author_orcids": "[\"0000-0002-1234-5678\", null]",
  "affiliation_list": "[\"Wuhan Institute of Virology\"]",
  "journal": "Nature",
  "issn": "0028-0836",
  "publisher": "Springer Nature",
  "publication_year": 2020,
  "publication_date": "2020-02-03",
  "publication_type": "journal-article",
  "publication_type_unified": "PUBLICATION",
  "publication_class": "PEER",
  "is_oa": true,
  "oa_status": "gold",
  "citations_received": 15000,
  "citations_made": 55,
  "subject_topics": "[{\"id\": \"https://openalex.org/T123\", \"display_name\": \"Coronavirus\", \"score\": 0.95}]",
  "primary_topic": "{\"id\": \"https://openalex.org/T123\", \"display_name\": \"Coronavirus\"}",
  "language": "en",
  "_lookup_method": "doi",
  "_original_id": null,
  "_source": "openalex",
  "content_hash": "sha256:abc123..."
}
```

Occurrence-scoped provenance anchors публикуются через sidecar metadata,
lineage fragments, run manifest и run ledger, а не через persisted Silver/Gold
rows.

### Fallback Record Example

```json
{
  "entity_id": "openalex:W3045876123",
  "openalex_id": "W3045876123",
  "doi": "10.1016/j.example.2020.001",
  "title": "Example Publication Title",
  "_lookup_method": "title_fallback",
  "_original_id": "10.1016/j.example.2020.001",
  "...": "..."
}
```

______________________________________________________________________

## 11. Тестирование

### Unit Tests

| Файл                                                            | Покрытие                           |
| --------------------------------------------------------------- | ---------------------------------- |
| `tests/unit/infrastructure/adapters/openalex/test_adapter.py`   | Adapter methods, DOI normalization |
| `tests/unit/infrastructure/adapters/openalex/test_fallback.py`  | Fallback logic                     |
| `tests/unit/application/pipelines/openalex/test_extractors.py`  | All extractors                     |
| `tests/unit/application/pipelines/openalex/test_transformer.py` | Transformation flow                |

### Integration Tests

| Файл                                                   | Покрытие                |
| ------------------------------------------------------ | ----------------------- |
| `tests/integration/adapters/openalex/test_adapter.py`  | HTTP interactions (VCR) |
| `tests/integration/adapters/openalex/test_pipeline.py` | Transformer extractors  |

**VCR Configuration** (для test_adapter.py):

```python
{
    "cassette_library_dir": "tests/fixtures/vcr/openalex",
    "record_mode": "none",
    "match_on": ["method", "scheme", "host", "port", "path", "query"],
    "filter_query_parameters": ["mailto"],
}
```

______________________________________________________________________

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
Input CSV → OpenAlexAdapter.fetch_filtered_with_fallback()
    ├─ Batch DOI lookup (filter=doi:doi1|doi2|...)
    ├─ Title fallback for missing DOIs
    └─ Yield raw records with _lookup_method

Raw Records → OpenAlexPublicationTransformer._transform_impl()
    ├─ Extract business data (extractors.py)
    ├─ Validate required fields
    ├─ Compute entity_id and content_hash
    └─ Create OpenAlexPublicationEntity

Entity → SilverWriter (Delta Lake)
    └─ Upsert by content_hash

Silver → GoldWriter (validated)
    └─ Apply gold_filters, export CSV
```

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [openalex_publication_v1.0.json](../../contracts/gold/openalex_publication_v1.0.json)    |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                             |
| ----------------- | ------ | ---------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`             |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Описание`, `Трансформация`, `Data Flow` |
| Contract linkage  | Pass   | [openalex_publication_v1.0.json](../../contracts/gold/openalex_publication_v1.0.json)                |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                |

______________________________________________________________________

## API Compliance

### Rate limits & retries

Официальные источники OpenAlex конфликтуют. Current Developers docs state that the REST API requires an API key and the LLM quick reference documents HTTP `429` with exponential backoff. At the same time, the Help Center pricing page says the free tier is `100k/day` and `max 10/second`. До официального снятия противоречия клиент SHOULD использовать консервативный лимит `10 requests/second`, MUST honor HTTP `429`, and SHOULD применять exponential backoff.

### 429 handling policy

OpenAlex documents HTTP `429` for excess usage and shows exponential backoff as the expected retry pattern. The concrete `Retry-After` contract is not documented in the accessible references.

### Authentication model

Current technical documentation states that the REST API requires an API key; without a key only a very small free budget is available. Production clients MUST send the API key on every request.

### ToS URL

- https://openalex.org/OpenAlex_termsofservice.pdf

### Data license

OpenAlex data are published under CC0.

### Personal data notes

OpenAlex records include person-centric scholarly metadata such as author names, affiliations, and external identifiers (for example, ORCID when available). API/account-specific personal-data handling beyond those scholarly metadata fields is [неуточнено] in the accessible technical docs.

### Official sources

- [OpenAlex Developers overview](https://developers.openalex.org/)
- [OpenAlex API guide for LLMs](https://developers.openalex.org/api-guide-for-llms)
- [OpenAlex Pricing](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing)
- [OpenAlex About us](https://help.openalex.org/hc/en-us/articles/24396686889751-About-us)
- [OpenAlex Terms of Service](https://openalex.org/OpenAlex_termsofservice.pdf)

*Последнее обновление: 2026-04-28*
