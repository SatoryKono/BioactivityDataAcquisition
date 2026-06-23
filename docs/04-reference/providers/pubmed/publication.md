______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# Пайплайн: PubMed Publication

**Имя пайплайна:** `pubmed_publication`
**Провайдер:** `pubmed`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

______________________________________________________________________

## 1. Описание

Пайплайн извлекает метаданные научных публикаций из API PubMed (NCBI E-utilities). Используется для обогащения биоактивных данных ссылками на первоисточники.

______________________________________________________________________

## 2. Ключевые поля

### Идентификаторы

| Поле     | Тип   | Описание                  |
| -------- | ----- | ------------------------- |
| `pmid`   | `str` | PubMed ID (уникальный)    |
| `doi`    | `str` | Digital Object Identifier |
| `pmc_id` | `str` | PubMed Central ID         |

### Метаданные статьи

| Поле               | Тип         | Описание         |
| ------------------ | ----------- | ---------------- |
| `title`            | `str`       | Название статьи  |
| `abstract`         | `str`       | Аннотация        |
| `authors`          | `str \| None` | JSON-массив авторов   |
| `journal`          | `str`       | Название журнала |
| `publication_date` | `str`       | Дата публикации  |
| `volume`           | `str`       | Том журнала      |
| `issue`            | `str`       | Выпуск           |
| `page_range`       | `str`       | Страницы         |

### Авторы и аффилиации

| Поле                        | Тип           | Описание                                                              |
| --------------------------- | ------------- | --------------------------------------------------------------------- |
| `author_keys`               | `str \| None` | Нормализованные ключи авторов в формате `Surname-F`, разделённые `\|` |
| `affiliation_list`          | `str \| None` | JSON-массив уникальных аффилиаций                                     |
| `authors_with_affiliations` | `str \| None` | JSON-массив: автор → аффилиации                                       |
| `affiliation_structured`    | `str \| None` | JSON-массив с ROR/GRID идентификаторами                               |

### Классификация

| Поле                       | Тип           | Описание                               |
| -------------------------- | ------------- | -------------------------------------- |
| `publication_class`        | `str`         | Класс публикации: EXP, REV, PEER       |
| `publication_subclass`     | `str \| None` | Подкласс (L2): ~16 групп               |
| `publication_type_unified` | `str \| None` | Унифицированный тип (L3): 214 значений |
| `subject_mesh`             | `str \| None` | JSON-массив MeSH терминов              |
| `subject_keywords`         | `str \| None` | JSON-массив ключевых слов              |
| `publication_types`        | `str \| None` | JSON-массив типов публикации           |

______________________________________________________________________

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py`

### Парсинг XML

PubMed API возвращает данные в XML формате. Трансформер использует
`xml_parser.py` и extractor-модули из `extractors/` для парсинга и
нормализации полей.

### Entity ID

```python
entity_id = f"pubmed:{pmid}"
```

______________________________________________________________________

## 4. Особенности

### Rate Limiting

PubMed API имеет строгие лимиты:

- Без API key: 3 запроса/сек
- С API key: 10 запросов/сек

### Рекомендации

1. Используйте API key для production
1. Устанавливайте `limit` при тестировании
1. Используйте `--dry-run` для проверки конфигурации

______________________________________________________________________

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline pubmed_publication

# С ограничением
bioetl run --pipeline pubmed_publication --limit 100

# Полная перезагрузка
bioetl run --pipeline pubmed_publication --run-type rebuild
```

______________________________________________________________________

## 6. Связанные файлы

| Компонент    | Путь                                                     |
| ------------ | -------------------------------------------------------- |
| Конфигурация | `configs/entities/pubmed/publication.yaml`               |
| Трансформер  | `src/bioetl/application/pipelines/pubmed/transformer.py` |
| XML Parser   | `src/bioetl/application/pipelines/pubmed/xml_parser.py`  |
| Extractors   | `src/bioetl/application/pipelines/pubmed/extractors/`    |

______________________________________________________________________

## Contract References

| Артефакт             | Ссылка                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Gold contract export | [pubmed_publication_v1.0.json](../../contracts/gold/pubmed_publication_v1.0.json)        |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

______________________________________________________________________

## Compliance

| Контроль          | Статус | Evidence                                                                                           |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------- |
| Metadata          | Pass   | YAML header содержит `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`           |
| Runtime alignment | Pass   | Активный config/runtime surface описан в разделах `Конфигурация`, `Особенности`, `Связанные файлы` |
| Contract linkage  | Pass   | [pubmed_publication_v1.0.json](../../contracts/gold/pubmed_publication_v1.0.json)                  |
| API governance    | Pass   | См. [API Compliance](#api-compliance)                                                              |

______________________________________________________________________

## API Compliance

### Rate limits & retries

NCBI E-utilities usage guidelines publish `3 requests/second` without an API key and `10 requests/second` by default with an API key; higher limits require explicit arrangement with NCBI. Clients SHOULD identify themselves with `tool` and `email`, and SHOULD use batching/history-server workflows instead of high-frequency polling.

### 429 handling policy

NCBI documents over-limit failures via the `API rate limit exceeded` response message. A stable HTTP `429` contract is [неуточнено] in the official E-utilities book chapter, so clients SHOULD back off conservatively on any rate-limit error.

### Authentication model

PubMed E-utilities are publicly accessible. An API key is optional and increases default throughput; the API key is associated with an NCBI account.

### ToS URL

- https://www.ncbi.nlm.nih.gov/home/about/policies/

### Data license

NCBI data and software are generally public-domain U.S. Government works where no copyright is noted, but PubMed abstracts may include publisher-supplied copyrighted material.

### Personal data notes

NCBI asks API clients to register `tool` and `email`; the email is used to contact operators if a tool violates usage policy. NCBI also states that it does not collect PII about general visitors, but does collect visit metadata for analytics and operations.

### Official sources

- [NCBI E-utilities usage guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [NCBI policies and disclaimers](https://www.ncbi.nlm.nih.gov/home/about/policies/)

*Последнее обновление: 2026-03-30*
