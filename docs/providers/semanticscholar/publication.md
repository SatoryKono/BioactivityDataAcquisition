# Пайплайн: Semantic Scholar Publication

**Имя пайплайна:** `semanticscholar_publication`
**Провайдер:** `semanticscholar`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн выполняет batch-резолюцию DOI через Semantic Scholar API с fallback на поиск по названию. Обогащает публикации метаданными из каталога S2 (200M+ работ), включая AI-генерированные саммари (TLDR).

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `paper_id` | `str` | Уникальный S2 Paper ID (40-символьный hex) |
| `doi` | `str` | Digital Object Identifier |
| `pmid` | `str` | PubMed ID |
| `pmcid` | `str` | PubMed Central ID |
| `arxiv_id` | `str` | arXiv ID |
| `corpus_id` | `int` | Semantic Scholar Corpus ID |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название публикации |
| `abstract` | `str` | Аннотация |
| `tldr` | `str` | AI-генерированное краткое содержание |
| `authors` | `list[str]` | Список авторов (JSON, с PII-хэшированием) |
| `journal` | `str` | Название журнала |
| `volume` | `str` | Том журнала |
| `pages` | `str` | Страницы |
| `venue` | `str` | Площадка публикации |
| `year` | `int` | Год публикации |
| `publication_date` | `str` | Дата публикации (ISO 8601) |

### Метрики

| Поле | Тип | Описание |
|------|-----|----------|
| `citation_count` | `int` | Количество цитирований |
| `reference_count` | `int` | Количество ссылок |

### Open Access

| Поле | Тип | Описание |
|------|-----|----------|
| `is_open_access` | `bool` | Открытый доступ |
| `open_access_url` | `str` | URL открытого PDF |
| `open_access_status` | `str` | Статус OA |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `fields_of_study` | `list[str]` | Области исследования (JSON) |
| `publication_types` | `list[str]` | Типы публикации (JSON) |

### Lookup-метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `_lookup_method` | `str` | Метод поиска: `doi`, `title_fallback`, `title_only` |
| `_original_doi` | `str` | Оригинальный DOI (для fallback-записей) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/semanticscholar/transformer.py`

### Entity ID

```python
entity_id = f"semanticscholar:{paper_id}"
```

### Извлечение внешних идентификаторов

```python
external_ids = extract_external_ids(record.get("externalIds"))
# Returns: {doi, pmid, pmcid, arxiv, corpus_id}
```

### PII-хэширование авторов

Имена авторов хэшируются согласно RULES.md S5.4:

```python
hashed_authors = pii_hasher.hash_list(raw_authors)
```

### TLDR (AI-саммари)

```python
tldr = extract_tldr(record.get("tldr"))  # tldr.text field
```

---

## 4. Валидация

### DQ-правила

1. **`paper_id`** — обязательное (primary key)
2. **`title`** — обязательное

### Gold-фильтры

- Обязательные поля: `paper_id`, `title`
- Диапазон `year`: 1900-2100

---

## 5. Использование CLI

```bash
# Batch-резолюция DOI из файла
bioetl run semanticscholar_publication --input-filter data/input/dois.csv

# С ограничением
bioetl run semanticscholar_publication --limit 1000
```

### Формат входного файла

CSV с колонками:
- `doi` — DOI для резолюции (опционально)
- `title` — название для fallback-поиска (опционально)

---

## 6. Fallback-стратегия

При отсутствии DOI или неудачной резолюции:

1. **DOI resolution** — первичный метод
2. **Title fallback** — поиск по названию, если DOI не найден
3. **Title only** — поиск только по названию, если DOI пустой

Метод сохраняется в `_lookup_method` для аудита.

---

## 7. Особенности Semantic Scholar

### TLDR

AI-генерированное краткое содержание (1-2 предложения). Доступно не для всех публикаций.

### Fields of Study

Иерархическая классификация по областям исследования:
- Computer Science
- Medicine
- Biology
- Physics
- Chemistry
- и другие

### Publication Types

Типы публикации:
- `JournalArticle`
- `Conference`
- `Review`
- `Book`
- `Dataset`

---

## 8. Партиционирование

Silver и Gold таблицы партиционируются по полю `year`.

---

## 9. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/semanticscholar/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/semanticscholar/transformer.py` |
| Экстракторы | `src/bioetl/application/pipelines/semanticscholar/extractors.py` |

---

*Последнее обновление: 2026-01-06*
