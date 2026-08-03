______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: Semantic Scholar Publication

**Имя пайплайна:** `semanticscholar_publication`
**Провайдер:** `semanticscholar`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

______________________________________________________________________

## 1. Описание

Пайплайн обогащает записи публикаций метаданными из Semantic Scholar Academic Graph API (200M+ работ). Поддерживает пакетную резолюцию DOI с автоматическим fallback на поиск по заголовку, когда DOI не найден или отсутствует.

### Основные сценарии использования

1. **Обогащение документов ChEMBL** — добавление цитирований и метаданных к публикациям из ChEMBL Documents
1. **Обогащение PubMed публикаций** — получение `citations_received`, TLDR и `subject_fields`
1. **Резолюция DOI** — получение полных метаданных по списку DOI
1. **Поиск по заголовку** — когда DOI отсутствует или не найден в базе S2

### Особенности Semantic Scholar

- **Paper ID** — уникальный 40-символьный hex-идентификатор S2
- **TLDR** — AI-сгенерированное краткое описание статьи
- **Fields of Study** — автоматическая классификация по научным областям
- **Citation Metrics** — актуальные данные о цитированиях

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле        | Тип           | Описание                                |
| ----------- | ------------- | --------------------------------------- |
| `paper_id`  | `str`         | Semantic Scholar Paper ID (40-char hex) |
| `doi`       | `str \| None` | Digital Object Identifier               |
| `pmid`      | `str \| None` | PubMed ID                               |
| `pmc_id`    | `str \| None` | PubMed Central ID                       |
| `arxiv_id`  | `str \| None` | ArXiv ID                                |
| `corpus_id` | `int \| None` | S2 Corpus ID                            |

### Метаданные публикации

| Поле          | Тип           | Описание                                                      |
| ------------- | ------------- | ------------------------------------------------------------- |
| `title`       | `str \| None` | Название публикации                                           |
| `abstract`    | `str \| None` | Аннотация                                                     |
| `tldr`        | `str \| None` | AI-сгенерированное краткое описание                           |
| `authors`     | `str`         | JSON-массив авторов (опционально хэшированных)                |
| `author_keys` | `str \| None` | Нормализованные ключи авторов (`Surname-F`), разделённые `\|` |

### Библиографические данные

| Поле               | Тип           | Описание                        |
| ------------------ | ------------- | ------------------------------- |
| `journal`          | `str \| None` | Название журнала                |
| `volume`           | `str \| None` | Том                             |
| `page_range`       | `str \| None` | Диапазон страниц (`first-last`) |
| `publication_year` | `int \| None` | Год публикации (1500-2100)      |
| `publication_date` | `str \| None` | Дата публикации (YYYY-MM-DD)    |

### Метрики цитирования

| Поле                 | Тип           | Описание                       |
| -------------------- | ------------- | ------------------------------ |
| `citations_received` | `int \| None` | Количество цитирований         |
| `citations_made`     | `int \| None` | Количество ссылок в публикации |

### Open Access

| Поле              | Тип            | Описание                               |
| ----------------- | -------------- | -------------------------------------- |
| `is_oa`           | `bool \| None` | Доступна ли публикация бесплатно       |
| `open_access_url` | `str \| None`  | Прямая ссылка на PDF                   |
| `oa_status`       | `str \| None`  | Статус OA: GREEN, GOLD, HYBRID, BRONZE |

### Классификация

| Поле                | Тип   | Описание                     |
| ------------------- | ----- | ---------------------------- |
| `subject_fields`    | `str` | JSON-массив научных областей |
| `publication_types` | `str` | JSON-массив типов публикации |

`subject_fields` and `publication_types` are set-like canonical JSON fields.
`author_h_indices` and `citation_contexts` remain order-sensitive canonical JSON
fields. Semantic transforms must add `*_raw_json` plus `*_canonical_json`
sidecars before replacing or deriving these provider payloads.

### Lookup Metadata

| Поле             | Тип           | Описание                                               |
| ---------------- | ------------- | ------------------------------------------------------ |
| `_lookup_method` | `str`         | Метод резолюции: `doi`, `title_fallback`, `title_only` |
| `_original_id`   | `str \| None` | Исходный DOI для fallback записей                      |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/semanticscholar/transformer.py`

### Extractors

| Функция                      | Назначение                                       |
| ---------------------------- | ------------------------------------------------ |
| `extract_external_ids()`     | DOI, PMID, PMCID, ArXiv, CorpusId из externalIds |
| `extract_authors()`          | Список авторов из authors array                  |
| `extract_journal_info()`     | Журнал, том, страницы из journal/venue           |
| `extract_open_access_info()` | OA статус и URL из isOpenAccess/openAccessPdf    |
| `extract_tldr()`             | AI-сгенерированное описание из tldr.text         |
| `extract_fields_of_study()`  | Научные области из fieldsOfStudy                 |
| `validate_year()`            | Валидация года (1500-2100)                       |

### Entity ID

```python
# Формат entity_id на базе paper_id
entity_id = f"semanticscholar:{paper_id}"
```

### Content Hash

Вычисляется по бизнес-полям для дедупликации:

- Исключаются occurrence-scoped provenance anchors (`_run_id`, `_run_type`,
  `_source_batch_id`, `_ingestion_ts` и др.)
- Исключаются lookup metadata поля (`_lookup_method`, `_original_id`)
- Эти anchors могут фигурировать в config/hash-policy inventories, но не входят
  в persisted Silver/Gold row contract и публикуются через sidecar/control-plane
  artifacts
- None-значения исключаются из хэша

______________________________________________________________________

## 4. Особенности

### Rate Limiting

Semantic Scholar API предоставляет различные лимиты:

| Режим       | Лимит (API)                | Операционный лимит (конфиг)     | Стабильность |
| ----------- | -------------------------- | ------------------------------- | ------------ |
| Без API key | shared pool (нестабильный) | 0.1 req/sec (1 запрос / 10 сек) | Нестабильно  |
| С API key   | 1 req/sec (guaranteed)     | 1.0 req/sec, burst: 5           | Стабильно    |

**Рекомендация:** Всегда используйте API key для production. Без ключа используется консервативный лимит 0.1 req/sec для избежания 429 ошибок.

### Batch DOI Resolution

Пайплайн использует POST `/paper/batch` для пакетной резолюции:

- До 500 DOI в одном запросе (используем 100 для безопасности)
- Ответ возвращает `null` для ненайденных DOI в том же порядке
- Значительно эффективнее индивидуальных запросов

### Fallback by Title

При получении `null` для DOI:

1. Если в `fallback_mapping` есть заголовок для DOI
1. Выполняется поиск по заголовку: GET `/paper/search?query=...`
1. Возвращается первый результат с `_lookup_method: title_fallback`

### Title-Only Lookup

Для записей без DOI (пустая строка в input CSV):

1. Сразу выполняется поиск по заголовку
1. Возвращается с `_lookup_method: title_only`

### Конфигурация Input Filter

```yaml
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 100
  fallback_column: "title"  # Поиск по заголовку при не найденном DOI
```

______________________________________________________________________

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run --pipeline semanticscholar_publication

# С ограничением количества записей
bioetl run --pipeline semanticscholar_publication --limit 100

# Проверка конфигурации без выполнения
bioetl run --pipeline semanticscholar_publication --dry-run

# Полная перезагрузка
bioetl run --pipeline semanticscholar_publication --run-type rebuild
```

### Подготовка входных данных

Создайте CSV-файл `data/input/dois.csv`:

```csv
doi,title
10.1038/nature12373,Crystal structure of rhodopsin bound to arrestin
10.1016/j.cell.2019.03.025,Structure of the human serotonin receptor
,Machine learning for drug discovery
```

Примечание: Для записей без DOI оставьте поле пустым — будет использован поиск по заголовку.

### Настройка API Key

```bash
export BIOETL_SEMANTICSCHOLAR_API_KEY=your-api-key

# Получить API key: https://www.semanticscholar.org/product/api
```

______________________________________________________________________

## 6. Health Check

Semantic Scholar adapter реализует health check через `/paper/search`:

| Статус      | Условие                  |
| ----------- | ------------------------ |
| `HEALTHY`   | Ответ 200 за < 5 сек     |
| `DEGRADED`  | Ответ 200 за > 5 сек     |
| `UNHEALTHY` | Ошибка или не-200 статус |

______________________________________________________________________

## 7. Error Handling

### Recoverable Errors

| Код     | Поведение                                |
| ------- | ---------------------------------------- |
| 429     | Rate limit — retry с exponential backoff |
| 502/504 | Timeout — retry (max 3)                  |

### Critical Errors

| Код     | Поведение                       |
| ------- | ------------------------------- |
| 401/403 | Auth failure — fail immediately |

### Data Quality

| Условие                  | Поведение                    |
| ------------------------ | ---------------------------- |
| Missing paper_id         | Skip record (log warning)    |
| Invalid publication_year | Set to `None`                |
| Empty title              | Record kept (title nullable) |

______________________________________________________________________

## 8. Gold Filters

```yaml
gold_filters:
  required_fields:
    - paper_id
    - title
  ranges:
    publication_year:
      min: 1950
      max: 2050
```

______________________________________________________________________

## 9. Связанные файлы

| Компонент              | Путь                                                                 |
| ---------------------- | -------------------------------------------------------------------- |
| Конфигурация пайплайна | `configs/entities/semanticscholar/publication.yaml`                  |
| Конфигурация источника | `configs/providers/semanticscholar.yaml`                             |
| Трансформер            | `src/bioetl/application/pipelines/semanticscholar/transformer.py`    |
| Extractors             | `src/bioetl/application/pipelines/semanticscholar/extractors.py`     |
| Адаптер                | `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`      |
| Pandera Schema         | `src/bioetl/domain/schemas/semanticscholar/publication.py`           |
| Unit Tests             | `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py` |
| Integration Tests      | `tests/integration/adapters/test_semanticscholar.py`                 |
| VCR Cassettes          | `tests/fixtures/vcr/semanticscholar/`                                |

______________________________________________________________________

## 10. Примеры данных

### Bronze Record (API Response)

```json
{
  "paperId": "a88fbdb9b47a8e8aef2b8cabd1fe0adfb96a9f25",
  "externalIds": {
    "PubMed": "23868264",
    "DOI": "10.1038/nature12373",
    "CorpusId": 4463122
  },
  "title": "Crystal structure of rhodopsin bound to arrestin",
  "abstract": "G-protein-coupled receptors signal through G proteins or arrestins.",
  "year": 2015,
  "publicationDate": "2015-07-22",
  "venue": "Nature",
  "authors": [
    {"authorId": "4713315", "name": "Yanyong Kang"},
    {"authorId": "6628836", "name": "X. Zhou"}
  ],
  "citationCount": 892,
  "referenceCount": 50,
  "isOpenAccess": true,
  "openAccessPdf": {
    "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4536825/pdf/...",
    "status": "GREEN"
  },
  "tldr": {
    "model": "tldr@v2.0.0",
    "text": "The crystal structure provides a basis for understanding GPCR signalling."
  },
  "fieldsOfStudy": ["Biology", "Chemistry"],
  "publicationTypes": ["JournalArticle"],
  "journal": {
    "name": "Nature",
    "volume": "523",
    "pages": "561-567"
  }
}
```

### Silver Record (Transformed)

```json
{
  "paper_id": "a88fbdb9b47a8e8aef2b8cabd1fe0adfb96a9f25",
  "doi": "10.1038/nature12373",
  "pmid": "23868264",
  "pmc_id": null,
  "dblp_id": null,
  "corpus_id": 4463122,
  "title": "Crystal structure of rhodopsin bound to arrestin",
  "abstract": "G-protein-coupled receptors signal through G proteins or arrestins.",
  "tldr": "The crystal structure provides a basis for understanding GPCR signalling.",
  "authors": "[\"Yanyong Kang\", \"X. Zhou\"]",
  "author_keys": "kang_y|zhou_x",
  "author_s2_ids": "[\"4713315\", \"6628836\"]",
  "author_orcids": null,
  "author_h_indices": null,
  "affiliation_list": null,
  "journal": "Nature",
  "volume": "523",
  "issue": null,
  "page_range": "561-567",
  "page_first": "561",
  "page_last": "567",
  "publication_year": 2015,
  "publication_date": "2015-07-22",
  "citations_received": 892,
  "citations_made": 50,
  "influential_citation_count": 120,
  "is_oa": true,
  "open_access_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4536825/pdf/...",
  "oa_status": "GREEN",
  "subject_fields": "[\"Biology\", \"Chemistry\"]",
  "publication_type": "journal-article",
  "publication_types": "[\"JournalArticle\"]",
  "_source": "semanticscholar",
  "_lookup_method": "doi",
  "_original_id": null,
  "entity_id": "semanticscholar:a88fbdb9b47a8e8aef2b8cabd1fe0adfb96a9f25",
  "content_hash": "sha256:..."
}
```

Occurrence-scoped provenance (`run_id`, `run_type`, `source_batch_id`,
`ingestion_ts`) публикуется через sidecar/control-plane artifacts, а не через
persisted Silver/Gold rows.

______________________________________________________________________

## 11. API Reference

### POST /paper/batch

Пакетная резолюция Paper IDs.

**Request:**

```bash
POST https://api.semanticscholar.org/graph/v1/paper/batch?fields=...
Content-Type: application/json

{"ids": ["DOI:10.1038/nature12373", "DOI:10.1016/j.cell.2019.03.025"]}
```

**Response:** Array в том же порядке, с `null` для ненайденных.

### GET /paper/search

Поиск публикаций.

**Request:**

```bash
GET https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=...&limit=100
```

**Response:** Paged results с `data`, `total`, `offset`, `next`.

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                              |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Gold contract export | [semanticscholar_publication_v1.0.json](../../contracts/gold/semanticscholar_publication_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                  |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)            |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                                 |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`                 |
| Runtime alignment | Pass   | Активный config/runtime surface задокументирован в разделах `Описание`, `Трансформация`, `API Reference` |
| Contract linkage  | Pass   | [semanticscholar_publication_v1.0.json](../../contracts/gold/semanticscholar_publication_v1.0.json)      |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                                    |

______________________________________________________________________

## API Compliance

### Rate limits & retries

Semantic Scholar documents `1000 requests/second` shared across unauthenticated users for most public endpoints, and `1 request/second` as the introductory limit for an API key. Requests may be throttled further during heavy use. Clients SHOULD include an API key on every request and SHOULD retry with bounded exponential backoff.

### 429 handling policy

The overview docs say requests may be throttled further during heavy use, and the API License Agreement allows AI2 to throttle, suspend, or disable access if rate limits are exceeded. A concrete `Retry-After` contract is [неуточнено].

### Authentication model

Most endpoints are public without authentication, but some endpoints require an API key. The official best practice is to include the API key on every request.

### ToS URL

- https://www.semanticscholar.org/product/api/license

### Data license

API and S2 Data use are governed by the Semantic Scholar API License Agreement. The agreement says Response Data / S2 Data may be governed by accompanying licenses such as CC BY-NC or ODC-BY, and third-party content may impose additional terms.

### Personal data notes

The API may expose author and affiliation metadata, and the license agreement allows AI2 to collect Licensee Data, usage data, and aggregate statistics to operate and improve the API.

### Official sources

- [Semantic Scholar API overview](https://www.semanticscholar.org/product/api)
- [Semantic Scholar public API FAQ](https://www.semanticscholar.org/faq/public-api)
- [Semantic Scholar API License Agreement](https://www.semanticscholar.org/product/api/license)
- [AI2 privacy policy](https://allenai.org/privacy-policy/2018-07-30)

*Последнее обновление: 2026-03-30*
