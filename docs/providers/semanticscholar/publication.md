# Пайплайн: Semantic Scholar Publication

**Имя пайплайна:** `semanticscholar_publication`
**Провайдер:** `semanticscholar`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн обогащает записи публикаций метаданными из Semantic Scholar Academic Graph API. Поддерживает пакетную резолюцию DOI с автоматическим fallback на поиск по заголовку, когда DOI не найден или отсутствует.

### Основные сценарии использования

1. **Обогащение документов ChEMBL** — добавление цитирований и метаданных к публикациям из ChEMBL Documents
2. **Обогащение PubMed публикаций** — получение citation_count, TLDR, fields_of_study
3. **Резолюция DOI** — получение полных метаданных по списку DOI
4. **Поиск по заголовку** — когда DOI отсутствует или не найден в базе S2

### Особенности Semantic Scholar

- **Paper ID** — уникальный 40-символьный hex-идентификатор S2
- **TLDR** — AI-сгенерированное краткое описание статьи
- **Fields of Study** — автоматическая классификация по научным областям
- **Citation Metrics** — актуальные данные о цитированиях

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `paper_id` | `str` | Semantic Scholar Paper ID (40-char hex) |
| `doi` | `str \| None` | Digital Object Identifier |
| `pmid` | `str \| None` | PubMed ID |
| `pmcid` | `str \| None` | PubMed Central ID |
| `arxiv_id` | `str \| None` | ArXiv ID |
| `corpus_id` | `int \| None` | S2 Corpus ID |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str \| None` | Название публикации |
| `abstract` | `str \| None` | Аннотация |
| `tldr` | `str \| None` | AI-сгенерированное краткое описание |
| `authors` | `str` | JSON-массив авторов (опционально хэшированных) |
| `venue` | `str \| None` | Место публикации (конференция/журнал) |

### Библиографические данные

| Поле | Тип | Описание |
|------|-----|----------|
| `journal` | `str \| None` | Название журнала |
| `volume` | `str \| None` | Том |
| `pages` | `str \| None` | Страницы |
| `year` | `int \| None` | Год публикации (1500-2100) |
| `publication_date` | `str \| None` | Дата публикации (YYYY-MM-DD) |

### Метрики цитирования

| Поле | Тип | Описание |
|------|-----|----------|
| `citation_count` | `int \| None` | Количество цитирований |
| `reference_count` | `int \| None` | Количество ссылок в публикации |

### Open Access

| Поле | Тип | Описание |
|------|-----|----------|
| `is_open_access` | `bool \| None` | Доступна ли публикация бесплатно |
| `open_access_url` | `str \| None` | Прямая ссылка на PDF |
| `open_access_status` | `str \| None` | Статус OA: GREEN, GOLD, HYBRID, BRONZE |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `fields_of_study` | `str` | JSON-массив научных областей |
| `publication_types` | `str` | JSON-массив типов публикации |

### Lookup Metadata

| Поле | Тип | Описание |
|------|-----|----------|
| `_lookup_method` | `str` | Метод резолюции: `doi`, `title_fallback`, `title_only` |
| `_original_doi` | `str \| None` | Исходный DOI для fallback записей |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/semanticscholar/transformer.py`

### Extractors

| Функция | Назначение |
|---------|------------|
| `extract_external_ids()` | DOI, PMID, PMCID, ArXiv, CorpusId из externalIds |
| `extract_authors()` | Список авторов из authors array |
| `extract_journal_info()` | Журнал, том, страницы из journal/venue |
| `extract_open_access_info()` | OA статус и URL из isOpenAccess/openAccessPdf |
| `extract_tldr()` | AI-сгенерированное описание из tldr.text |
| `extract_fields_of_study()` | Научные области из fieldsOfStudy |
| `validate_year()` | Валидация года (1500-2100) |

### Entity ID

```python
# Формат entity_id на базе paper_id
entity_id = f"semanticscholar:{paper_id}"
```

### Content Hash

Вычисляется по бизнес-полям для дедупликации:
- Исключаются lineage поля (`_run_id`, `_ingestion_ts`, etc.)
- Исключаются lookup metadata поля (`_lookup_method`, `_original_doi`)
- None-значения исключаются из хэша

---

## 4. Особенности

### Rate Limiting

Semantic Scholar API предоставляет различные лимиты:

| Режим | Лимит | Стабильность |
|-------|-------|--------------|
| Без API key | 1000 req/sec (shared pool) | Нестабильно |
| С API key | 1 req/sec (guaranteed) | Стабильно |

**Рекомендация:** Всегда используйте API key для production.

### Batch DOI Resolution

Пайплайн использует POST `/paper/batch` для пакетной резолюции:
- До 500 DOI в одном запросе (используем 100 для безопасности)
- Ответ возвращает `null` для ненайденных DOI в том же порядке
- Значительно эффективнее индивидуальных запросов

### Fallback by Title

При получении `null` для DOI:
1. Если в `fallback_mapping` есть заголовок для DOI
2. Выполняется поиск по заголовку: GET `/paper/search?query=...`
3. Возвращается первый результат с `_lookup_method: title_fallback`

### Title-Only Lookup

Для записей без DOI (пустая строка в input CSV):
1. Сразу выполняется поиск по заголовку
2. Возвращается с `_lookup_method: title_only`

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

---

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run semanticscholar_publication

# С ограничением количества записей
bioetl run semanticscholar_publication --limit 100

# Проверка конфигурации без выполнения
bioetl run semanticscholar_publication --dry-run

# Полная перезагрузка
bioetl run semanticscholar_publication --run-type rebuild
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

---

## 6. Health Check

Semantic Scholar adapter реализует health check через `/paper/search`:

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

### Critical Errors

| Код | Поведение |
|-----|-----------|
| 401/403 | Auth failure — fail immediately |

### Data Quality

| Условие | Поведение |
|---------|-----------|
| Missing paper_id | Skip record (log warning) |
| Invalid year | Set to None |
| Empty title | Record kept (title nullable) |

---

## 8. Gold Filters

```yaml
gold_filters:
  required_fields:
    - paper_id
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
| Конфигурация пайплайна | `configs/pipelines/semanticscholar/publication.yaml` |
| Конфигурация источника | `configs/sources/semanticscholar.yaml` |
| Трансформер | `src/bioetl/application/pipelines/semanticscholar/transformer.py` |
| Extractors | `src/bioetl/application/pipelines/semanticscholar/extractors.py` |
| Адаптер | `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py` |
| Pandera Schema | `src/bioetl/domain/schemas/semanticscholar/publication.py` |
| Unit Tests | `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py` |
| Integration Tests | `tests/integration/adapters/test_semanticscholar.py` |
| VCR Cassettes | `tests/fixtures/vcr/semanticscholar/` |

---

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
  "pmcid": null,
  "arxiv_id": null,
  "corpus_id": 4463122,
  "title": "Crystal structure of rhodopsin bound to arrestin",
  "abstract": "G-protein-coupled receptors signal through G proteins or arrestins.",
  "tldr": "The crystal structure provides a basis for understanding GPCR signalling.",
  "authors": "[\"Yanyong Kang\", \"X. Zhou\"]",
  "journal": "Nature",
  "volume": "523",
  "pages": "561-567",
  "venue": "Nature",
  "year": 2015,
  "publication_date": "2015-07-22",
  "citation_count": 892,
  "reference_count": 50,
  "is_open_access": true,
  "open_access_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4536825/pdf/...",
  "open_access_status": "GREEN",
  "fields_of_study": "[\"Biology\", \"Chemistry\"]",
  "publication_types": "[\"JournalArticle\"]",
  "source": "semanticscholar",
  "_lookup_method": "doi",
  "_original_doi": null,
  "_run_id": "...",
  "_run_type": "incremental",
  "_ingestion_ts": "2026-01-06T12:00:00Z",
  "entity_id": "semanticscholar:a88fbdb9b47a8e8aef2b8cabd1fe0adfb96a9f25",
  "content_hash": "sha256:..."
}
```

---

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

---

*Последнее обновление: 2026-01-06*
