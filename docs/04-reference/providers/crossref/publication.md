# Пайплайн: CrossRef Publication

**Имя пайплайна:** `crossref-publication`
**Провайдер:** `crossref`
**Сущность:** `publication` (CrossRef API использует термин `work`, но `entity-type` в конфигурации — `publication`, унифицирован с другими провайдерами)
**Версия схемы:** 1.2.0

----------------------------------------------------------------------

## 1. Описание

Пайплайн обогащает записи публикаций метаданными из CrossRef API через DOI-резолюцию. Используется для получения информации о цитировании, авторах, журналах и других библиографических данных по известным DOI.

### Основные сценарии использования

1. **Обогащение документов ChEMBL** — добавление цитирований к публикациям из ChEMBL Documents
1. **Обогащение PubMed публикаций** — дополнительные метаданные (citation-count, reference-count)
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
| `page-first`       | `str \| None` | Первая страница                |
| `page-last`        | `str \| None` | Последняя страница             |
| `publication-year` | `int \| None` | Год публикации                 |
| `published-print`  | `str \| None` | Дата печатной публикации (ISO) |
| `published-online` | `str \| None` | Дата онлайн-публикации (ISO)   |

### Метрики цитирования

| Поле              | Тип           | Описание                                        |
| ----------------- | ------------- | ----------------------------------------------- |
| `citations-received` | `int \| None` | Количество цитирований (is-referenced-by-count) |
| `citations-made`     | `int \| None` | Количество ссылок в публикации                  |

### Классификация

| Поле          | Тип           | Описание                                    |
| ------------- | ------------- | ------------------------------------------- |
| `doc-type`    | `str`         | Тип документа: `PUBLICATION` или `PREPRINT` |
| `issn`        | `list[str]`   | Список ISSN журнала                         |
| `language`    | `str \| None` | Код языка публикации                        |
| `license-url` | `str \| None` | URL лицензии                                |
| `subjects`    | `list[str]`   | Предметные области                          |

----------------------------------------------------------------------

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/crossref/transformer.py`

### Нормализация DOI

```python
# DOI нормализуется в lowercase и stripped
doi = normalize-doi("10.1234/ABC.DEF")  # → "10.1234/abc.def"
```

### Маппинг типов документов

| CrossRef type         | Internal type |
| --------------------- | ------------- |
| `journal-article`     | `PUBLICATION` |
| `posted-content`      | `PREPRINT`    |
| `proceedings-article` | `PUBLICATION` |
| `book-chapter`        | `PUBLICATION` |
| `dissertation`        | `PUBLICATION` |

### Entity ID

```python
# Формат entity-id
entity-id = f"crossref:{normalized-doi}"
```

### Content Hash

Вычисляется по бизнес-полям публикации для дедупликации:

- Исключаются lineage поля (`-run-id`, `-ingestion-ts`, etc.)
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

1. Если в `fallback-mapping` есть заголовок для DOI
1. Выполняется поиск по заголовку: `title:"Publication Title"`
1. Проверяется релевантность найденного результата

### Конфигурация Input Filter

```yaml
input-filter:
  enabled: true
  source-path: "data/input/dois.csv"
  column-name: "doi"
  filter-field: "doi"
  batch-size: 50
  fallback-column: "title"  # Поиск по заголовку при 404
```

----------------------------------------------------------------------

## 5. Использование CLI

```bash
# Базовый запуск с файлом DOI
bioetl run crossref-publication

# С ограничением количества записей
bioetl run crossref-publication --limit 100

# Проверка конфигурации без выполнения
bioetl run crossref-publication --dry-run

# Полная перезагрузка
bioetl run crossref-publication --run-type rebuild
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
gold-filters:
  required-fields:
    - doi
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
  "publication-year": 2013,
  "published-print": "2013-07-25",
  "citations-received": 1500,
  "doc-type": "PUBLICATION",
  "source": "crossref",
  "-run-id": "...",
  "-run-type": "incremental",
  "-ingestion-ts": "2025-01-05T12:00:00Z",
  "content-hash": "sha256:..."
}
```

----------------------------------------------------------------------

*Последнее обновление: 2026-02-15*
