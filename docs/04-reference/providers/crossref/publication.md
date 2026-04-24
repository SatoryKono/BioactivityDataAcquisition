---
Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-30'
---

# Пайплайн: CrossRef Publication

**Имя пайплайна:** `crossref_publication`
**Провайдер:** `crossref`
**Сущность:** `publication` (CrossRef API использует термин `work`, но `entity_type` в конфигурации — `publication`, унифицирован с другими провайдерами)
**Версия схемы:** 1.2.0

----------------------------------------------------------------------

## 1. Описание

Пайплайн обогащает записи публикаций метаданными из CrossRef API через DOI-резолюцию. Используется для получения информации о цитировании, авторах, журналах и других библиографических данных по известным DOI.

### Основные сценарии использования

1. **Обогащение документов ChEMBL** — добавление цитирований к публикациям из ChEMBL Documents
1. **Обогащение PubMed публикаций** — дополнительные метаданные (citations_received, citations_made)
1. **Резолюция DOI** — получение полных метаданных по списку DOI

----------------------------------------------------------------------

## 2. Ключевые поля

### Идентификаторы

| Поле  | Тип   | Описание                                                         |
| ----- | ----- | ---------------------------------------------------------------- |
| `doi` | `str` | Digital Object Identifier (нормализованный: lowercase, stripped) |

### Метаданные публикации

| Поле        | Тип           | Описание                                |
| ----------- | ------------- | --------------------------------------- |
| `title`     | `str \| None` | Название публикации                     |
| `abstract`  | `str \| None` | Аннотация (HTML-теги удалены)           |
| `authors`   | `list[str]`   | Список авторов в формате "given family" |
| `journal`   | `str \| None` | Название журнала (container-title)      |
| `publisher` | `str \| None` | Издатель                                |

### Библиографические данные

| Поле               | Тип           | Описание                       |
| ------------------ | ------------- | ------------------------------ |
| `volume`           | `str \| None` | Том                            |
| `issue`            | `str \| None` | Выпуск                         |
| `page_first`       | `str \| None` | Первая страница                |
| `page_last`        | `str \| None` | Последняя страница             |
| `publication_year` | `int \| None` | Год публикации                 |
| `published_print`  | `str \| None` | Дата печатной публикации (ISO) |
| `published_online` | `str \| None` | Дата онлайн-публикации (ISO)   |

### Метрики цитирования

| Поле              | Тип           | Описание                                        |
| ----------------- | ------------- | ----------------------------------------------- |
| `citations_received` | `int \| None` | Количество цитирований (is-referenced-by-count) |
| `citations_made`     | `int \| None` | Количество ссылок в публикации                  |

### Классификация

| Поле          | Тип           | Описание                                    |
| ------------- | ------------- | ------------------------------------------- |
| `publication_type`    | `str`         | Тип документа: `PUBLICATION` или `PREPRINT` |
| `issn`        | `list[str]`   | Список ISSN журнала                         |
| `language`    | `str \| None` | Код языка публикации                        |
| `license_url` | `str \| None` | URL лицензии                                |
| `subjects`    | `list[str]`   | Предметные области                          |

----------------------------------------------------------------------

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/crossref/transformer.py`

### Нормализация DOI

```python
# DOI нормализуется в lowercase и stripped
doi = normalize_doi("10.1234/ABC.DEF")  # → "10.1234/abc.def"
```

### Маппинг типов документов

| CrossRef type         | Internal type |
| --------------------- | ------------- |
| `journal-article`     | `PUBLICATION` |
| `posted-content`      | `PREPRINT`    |
| `proceedings-article` | `PUBLICATION` |
| `book-chapter`        | `PUBLICATION` |
| `dissertation`        | `PUBLICATION` |

> **Note**: Internal type mapping is part of [Internal/Extended Material](#internalextended-material)

### Entity ID

```python
# Формат entity_id
entity_id = f"crossref:{normalized_doi}"
```

### Content Hash

Вычисляется по бизнес-полям публикации для дедупликации:

- Исключаются occurrence-scoped provenance anchors (`_run_id`, `_run_type`,
  `_source_batch_id`, `_ingestion_ts` и др.)
- Эти anchors могут фигурировать в config/hash-policy inventories, но не входят
  в persisted Silver/Gold row contract и публикуются через sidecar/control-plane
  artifacts
- None-значения исключаются из хэша

----------------------------------------------------------------------

## 4. Особенности

### Rate Limiting

CrossRef API предоставляет "polite pool" с повышенными лимитами:

| Режим             | Лимит      | Условие                   |
| ----------------- | ---------- | ------------------------- |
| Без идентификации | 50 req/sec | Базовый доступ            |
| С `mailto`        | 50 req/sec | Указан email в User-Agent |

### Batch DOI Resolution

Пайплайн поддерживает пакетную резолюцию DOI:

- До 100 DOI в одном запросе через `filter=doi:doi1,doi2,...`
- Значительно эффективнее индивидуальных запросов

### Fallback by Title

При получении 404 для DOI:

1. Если в `fallback_mapping` есть заголовок для DOI
1. Выполняется поиск по заголовку: `title:"Publication Title"`
1. Проверяется релевантность найденного результата

### Конфигурация Input Filter

```yaml
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 50
  fallback_column: "title"  # Поиск по заголовку при 404
```

----------------------------------------------------------------------

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run --pipeline crossref_publication

# С ограничением количества записей
bioetl run --pipeline crossref_publication --limit 100

# Проверка конфигурации без выполнения
bioetl run --pipeline crossref_publication --dry-run

# Полная перезагрузка
bioetl run --pipeline crossref_publication --run-type rebuild
```

### Подготовка входных данных

Создайте CSV-файл `data/input/dois.csv`:

```csv
doi,title
10.1038/nature12373,Crystal structure of rhodopsin
10.1016/j.cell.2019.03.025,Structure of the human receptor
```

----------------------------------------------------------------------

## 6. Health Check

CrossRef adapter реализует health check через `/works?rows=1`:

| Статус      | Условие                  |
| ----------- | ------------------------ |
| `HEALTHY`   | Ответ 200 за < 5 сек     |
| `DEGRADED`  | Ответ 200 за > 5 сек     |
| `UNHEALTHY` | Ошибка или не-200 статус |

----------------------------------------------------------------------

## 7. Error Handling

### Recoverable Errors

| Код        | Поведение                          |
| ---------- | ---------------------------------- |
| 429        | Rate limit — retry с backoff       |
| 502/504    | Timeout — retry (max 3)            |
| Batch fail | Fallback на индивидуальные запросы |

### Critical Errors

| Код     | Поведение                       |
| ------- | ------------------------------- |
| 401/403 | Auth failure — fail immediately |

### Data Quality

| Условие            | Поведение                 |
| ------------------ | ------------------------- |
| Missing DOI        | Skip record (log warning) |
| Invalid DOI format | Skip record               |

----------------------------------------------------------------------

## 8. Gold Filters

```yaml
gold_filters:
  required_fields:
    - doi
    - title
  ranges:
    publication_year:
      min: 1500
      max: 2100
```

----------------------------------------------------------------------

## 9. Связанные файлы

| Компонент              | Путь                                                       |
| ---------------------- | ---------------------------------------------------------- |
| Конфигурация пайплайна | `configs/entities/crossref/publication.yaml`              |
| Конфигурация источника | `configs/providers/crossref.yaml`                            |
| Трансформер            | `src/bioetl/application/pipelines/crossref/transformer.py` |
| Адаптер                | `src/bioetl/infrastructure/adapters/crossref/client.py`    |
| Batch Processor        | `src/bioetl/infrastructure/adapters/crossref/batch.py`     |
| Fallback Handler       | `src/bioetl/infrastructure/adapters/crossref/fallback.py`  |
| Domain Entity          | `src/bioetl/domain/entities/crossref.py`                   |

----------------------------------------------------------------------

## 10. Примеры данных

### Bronze Record (API Response)

```json
{
  "DOI": "10.1038/nature12373",
  "title": ["Crystal structure of rhodopsin"],
  "author": [
    {"given": "John", "family": "Doe"},
    {"given": "Jane", "family": "Smith"}
  ],
  "container-title": ["Nature"],
  "publisher": "Springer Nature",
  "published-print": {"date-parts": [[2013, 7, 25]]},
  "is-referenced-by-count": 1500,
  "type": "journal-article"
}
```

### Silver Record (Transformed)

```json
{
  "doi": "10.1038/nature12373",
  "title": "Crystal structure of rhodopsin",
  "authors": ["John Doe", "Jane Smith"],
  "journal": "Nature",
  "publisher": "Springer Nature",
  "publication_year": 2013,
  "published_print": "2013-07-25",
  "citations_received": 1500,
  "publication_type": "PUBLICATION",
  "source": "crossref",
  "content_hash": "sha256:..."
}
```

Occurrence-scoped provenance anchors публикуются через sidecar metadata,
lineage fragments, run manifest и run ledger, а не через persisted Silver/Gold
rows.

----------------------------------------------------------------------

## Contract References

| Артефакт | Ссылка |
| --- | --- |
| Gold contract export | [crossref_publication_v1.0.json](../../contracts/gold/crossref_publication_v1.0.json) |
| Gold schemas index | [gold-schemas.md](../../contracts/gold-schemas.md) |
| Versioning policy | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

----------------------------------------------------------------------

## Compliance

| Контроль | Статус | Evidence |
| --- | --- | --- |
| Metadata | Pass | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Runtime alignment | Pass | Активный config/runtime surface задокументирован в разделах `Конфигурация`, `Трансформация`, `Связанные файлы` |
| Contract linkage | Pass | [crossref_publication_v1.0.json](../../contracts/gold/crossref_publication_v1.0.json) |
| API governance | Pass | См. [API Compliance](#api-compliance) |

----------------------------------------------------------------------

## API Compliance

### Rate limits & retries

Crossref documents three pools for the REST API: public `5 requests/second` with `1 concurrent request`, polite `10 requests/second` with `3 concurrent requests`, and `Plus` `150 requests/second` with no concurrency limit. Clients SHOULD send a descriptive `User-Agent`, SHOULD include `mailto`, and SHOULD back off exponentially if response times rise or blocks occur.

### 429 handling policy

Crossref explicitly documents HTTP `429 Too Many Requests`: wait briefly, reduce request rate or concurrency, then retry. If usage has been manually blocked, the API may return `403`, and the client SHOULD back off for several minutes before retrying.

### Authentication model

Public REST endpoints do not require authentication. Polite access identifies the client via `mailto` and `User-Agent`; Metadata Plus uses a token-based `Crossref-Plus-API-Token` header.

### ToS URL

- [неуточнено]

### Data license

Crossref-generated metadata values are provided as CC0 facts/identifiers; bibliographic facts are generally not copyrightable. Abstracts and linked full-text targets may remain subject to third-party rights.

### Personal data notes

Crossref asks clients to send a contact email for troubleshooting; that address is kept only as long as needed and then deleted after three months. Crossref also logs request metadata such as IP address, browser type, OS, date/time, and accessed resources.

### Official sources

- [Crossref REST API overview](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [Crossref access and authentication](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
- [Crossref API tips](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)
- [Crossref privacy notice](https://www.crossref.org/privacy/)

*Последнее обновление: 2026-03-30*
