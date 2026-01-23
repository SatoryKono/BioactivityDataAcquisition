# Пайплайн: OpenAlex Publication

**Имя пайплайна:** `openalex_publication`
**Провайдер:** `openalex`
**Сущность:** `publication` (API-термин: `work`)
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн выполняет пакетную резолюцию DOI через OpenAlex Works API с поддержкой поиска по заголовку при отсутствии DOI или его невалидности. Используется для обогащения публикаций метаданными об открытом доступе, цитированиях и концептах.

### Основные сценарии использования

1. **Резолюция DOI** — получение полных метаданных публикаций по списку DOI
2. **Обогащение документов ChEMBL** — добавление Open Access статуса и метрик цитирования
3. **Fallback по заголовку** — поиск публикаций, когда DOI недоступен или не найден

### Терминология

- **Publication** — внутренний термин BioETL (Ubiquitous Language)
- **Work** — термин OpenAlex API
- Оба термина обозначают одну сущность — научную публикацию

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `openalex_id` | `str` | OpenAlex Work ID (e.g., W2148763428) — первичный ключ |
| `doi` | `str \| None` | Digital Object Identifier (нормализованный) |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str \| None` | Название публикации |
| `abstract` | `str \| None` | Аннотация (реконструированная из inverted index) |
| `authors` | `list[str]` | Список авторов (опционально хэшируются как PII) |
| `journal` | `str \| None` | Название журнала/источника |
| `issn` | `str \| None` | ISSN-L журнала |
| `publisher` | `str \| None` | Название издателя |

### Даты и тип

| Поле | Тип | Описание |
|------|-----|----------|
| `year` | `int \| None` | Год публикации (валидируется: 1900-2100) |
| `publication_date` | `str \| None` | Дата публикации (YYYY-MM-DD) |
| `doc_type` | `str` | Тип документа: `PUBLICATION`, `PREPRINT`, `DATASET`, `OTHER` |

### Open Access

| Поле | Тип | Описание |
|------|-----|----------|
| `is_oa` | `bool \| None` | Публикация в открытом доступе |
| `oa_status` | `str \| None` | Статус OA: `gold`, `green`, `hybrid`, `bronze`, `closed` |

### Метрики и классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `cited_by_count` | `int \| None` | Количество цитирований |
| `concepts` | `list[str]` | Топ-10 концептов OpenAlex |
| `language` | `str \| None` | Код языка публикации |

### Метаданные резолюции

| Поле | Тип | Описание |
|------|-----|----------|
| `_lookup_method` | `str` | Метод резолюции: `doi`, `title_fallback`, `title_only` |
| `_original_doi` | `str \| None` | Оригинальный DOI из входного CSV (для fallback записей) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py`

### Извлечение полей

Трансформер делегирует извлечение полей в `extractors.py`:

| Функция | Назначение |
|---------|------------|
| `extract_openalex_id()` | Извлечение ID из URL (https://openalex.org/W... → W...) |
| `extract_doi()` | Нормализация DOI (удаление https://doi.org/) |
| `reconstruct_abstract()` | Реконструкция абстракта из inverted index |
| `extract_authors()` | Извлечение display_name из authorships |
| `extract_concepts()` | Топ-10 концептов по score |
| `extract_journal_info()` | Журнал, ISSN-L, издатель из primary_location |
| `extract_open_access_info()` | is_oa и oa_status из open_access |

### Маппинг типов документов

| OpenAlex type | Internal type |
|---------------|---------------|
| `article`, `journal-article` | `PUBLICATION` |
| `book-chapter`, `book` | `PUBLICATION` |
| `proceedings-article` | `PUBLICATION` |
| `preprint`, `posted-content` | `PREPRINT` |
| `dataset` | `DATASET` |
| `other` | `OTHER` |

### Entity ID

```python
# Формат entity_id
entity_id = f"openalex:{openalex_id}"
```

### Content Hash

Вычисляется по бизнес-полям публикации для дедупликации:
- Исключаются lookup-метаданные (`_lookup_method`, `_original_doi`)
- Исключаются lineage-поля (`_run_id`, `_ingestion_ts`, etc.)
- None-значения исключаются из хэша

---

## 4. Особенности

### Rate Limiting

OpenAlex предоставляет "polite pool" с повышенными лимитами:

| Режим | Лимит | Условие |
|-------|-------|---------|
| Без идентификации | ~5 req/sec | Базовый доступ |
| С `mailto` | 10 req/sec | Указан email в User-Agent и параметрах |

**Важно:** Переменная окружения `BIOETL_OPENALEX_EMAIL` обязательна для production.

### Batch DOI Resolution

Пайплайн поддерживает пакетную резолюцию DOI:
- До 50 DOI в одном запросе через `filter=doi:doi1|doi2|...`
- Значительно эффективнее индивидуальных запросов
- Pipe (`|`) используется как разделитель DOI

### Fallback by Title

При неудачной резолюции DOI:

1. Если в `fallback_mapping` есть заголовок для DOI
2. Выполняется поиск по заголовку: `title.search:Publication+Title`
3. Специальные символы экранируются: `:`, `|`, `,` удаляются, пробелы → `+`
4. Возвращается запись с `_lookup_method = "title_fallback"` или `"title_only"`

### Title-Only Lookup

Когда DOI пустой во входном CSV:
- Поиск выполняется только по заголовку
- `_lookup_method = "title_only"`
- `_original_doi` остаётся пустым

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

---

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

| Переменная | Описание | Обязательна |
|------------|----------|-------------|
| `BIOETL_OPENALEX_EMAIL` | Email для polite pool | Да |

---

## 6. Health Check

OpenAlex adapter реализует health check через `/works?per-page=1`:

| Статус | Условие |
|--------|---------|
| `HEALTHY` | Ответ 200 за < 5 сек |
| `DEGRADED` | Ответ 200 за > 5 сек |
| `UNHEALTHY` | Ошибка или не-200 статус |

---

## 7. Error Handling

### Recoverable Errors

| Код | Поведение |
|-----|-----------|
| 429 | Rate limit — retry с exponential backoff |
| 502/504 | Timeout — retry (max 3) |
| Batch fail | Fallback на индивидуальные запросы |

### Critical Errors

| Код | Поведение |
|-----|-----------|
| 401/403 | Auth failure — fail immediately |

### Data Quality

| Условие | Поведение |
|---------|-----------|
| Missing openalex_id | Skip record (log warning) |
| Invalid year range | Set year = None |
| Empty title in fallback | Skip title search |

---

## 8. Gold Filters

```yaml
gold_filters:
  required_fields:
    - openalex_id
    - title
  ranges:
    year:
      min: 1900
      max: 2100
```

---

## 9. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация пайплайна | `configs/pipelines/openalex/publication.yaml` |
| Конфигурация источника | `configs/sources/openalex.yaml` |
| Трансформер | `src/bioetl/application/pipelines/openalex/transformer.py` |
| Экстракторы | `src/bioetl/application/pipelines/openalex/extractors.py` |
| Адаптер | `src/bioetl/infrastructure/adapters/openalex/client.py` |
| Fallback Handler | `src/bioetl/infrastructure/adapters/openalex/fallback.py` |
| Domain Entity | `src/bioetl/domain/entities/openalex.py` |
| Gold Schema | `src/bioetl/infrastructure/schemas/gold.py` |

---

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
  "title": "A pneumonia outbreak associated with a new coronavirus of probable bat origin",
  "abstract": "A pneumonia outbreak...",
  "authors": ["Peng Zhou", "Xing-Lou Yang"],
  "journal": "Nature",
  "issn": "0028-0836",
  "publisher": "Springer Nature",
  "year": 2020,
  "publication_date": "2020-02-03",
  "doc_type": "PUBLICATION",
  "is_oa": true,
  "oa_status": "gold",
  "cited_by_count": 15000,
  "concepts": ["Coronavirus", "Virology"],
  "language": "en",
  "_lookup_method": "doi",
  "_original_doi": null,
  "source": "openalex",
  "content_hash": "sha256:abc123...",
  "_run_id": "run-2026-01-06-001",
  "_run_type": "incremental",
  "_ingestion_ts": "2026-01-06T12:00:00Z"
}
```

### Fallback Record Example

```json
{
  "entity_id": "openalex:W3045876123",
  "openalex_id": "W3045876123",
  "doi": "10.1016/j.example.2020.001",
  "title": "Example Publication Title",
  "_lookup_method": "title_fallback",
  "_original_doi": "10.1016/j.example.2020.001",
  "...": "..."
}
```

---

## 11. Тестирование

### Unit Tests

| Файл | Покрытие |
|------|----------|
| `tests/unit/infrastructure/adapters/openalex/test_adapter.py` | Adapter methods, DOI normalization |
| `tests/unit/infrastructure/adapters/openalex/test_fallback.py` | Fallback logic |
| `tests/unit/application/pipelines/openalex/test_extractors.py` | All extractors |
| `tests/unit/application/pipelines/openalex/test_transformer.py` | Transformation flow |

### Integration Tests

| Файл | Покрытие |
|------|----------|
| `tests/integration/adapters/openalex/test_adapter.py` | HTTP interactions (VCR) |
| `tests/integration/adapters/openalex/test_pipeline.py` | Transformer extractors |

**VCR Configuration** (для test_adapter.py):
```python
{
    "cassette_library_dir": "tests/fixtures/vcr/openalex",
    "record_mode": "none",
    "match_on": ["method", "scheme", "host", "port", "path", "query"],
    "filter_query_parameters": ["mailto"],
}
```

---

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

---

*Последнее обновление: 2026-01-06*
