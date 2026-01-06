# Пайплайн: OpenAlex Publication

**Имя пайплайна:** `openalex_publication`
**Провайдер:** `openalex`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн выполняет batch-резолюцию DOI через OpenAlex Works API с fallback на поиск по названию. Обогащает публикации метаданными из каталога OpenAlex (130M+ работ).

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `openalex_id` | `str` | Уникальный OpenAlex ID (формат: W1234567890) |
| `doi` | `str` | Digital Object Identifier (нормализованный) |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название публикации |
| `abstract` | `str` | Аннотация (реконструированная из inverted index) |
| `authors` | `list[str]` | Список авторов (с PII-хэшированием) |
| `journal` | `str` | Название журнала |
| `issn` | `str` | ISSN журнала |
| `publisher` | `str` | Издатель |
| `year` | `int` | Год публикации |
| `publication_date` | `str` | Дата публикации (ISO 8601) |
| `doc_type` | `str` | Тип документа (PUBLICATION, REVIEW, etc.) |

### Метрики

| Поле | Тип | Описание |
|------|-----|----------|
| `cited_by_count` | `int` | Количество цитирований |

### Open Access

| Поле | Тип | Описание |
|------|-----|----------|
| `is_oa` | `bool` | Открытый доступ |
| `oa_status` | `str` | Статус OA (gold, green, bronze, etc.) |

### Концепты

| Поле | Тип | Описание |
|------|-----|----------|
| `concepts` | `list[dict]` | Связанные концепты OpenAlex |
| `language` | `str` | Язык публикации |

### Lookup-метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `_lookup_method` | `str` | Метод поиска: `doi`, `title_fallback`, `title_only` |
| `_original_doi` | `str` | Оригинальный DOI (для fallback-записей) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py`

### Entity ID

```python
entity_id = f"openalex:{openalex_id}"
```

### Реконструкция аннотации

OpenAlex хранит аннотации в формате inverted index. Трансформер реконструирует текст:

```python
abstract = reconstruct_abstract(abstract_inverted_index)
```

### PII-хэширование авторов

Имена авторов хэшируются согласно RULES.md S5.4:

```python
hashed_authors = pii_hasher.hash_list(raw_authors)
```

---

## 4. Валидация

### DQ-правила

1. **`openalex_id`** — обязательное (primary key)
2. **`title`** — обязательное

### Gold-фильтры

- Обязательные поля: `openalex_id`, `title`
- Диапазон `year`: 1900-2100

---

## 5. Использование CLI

```bash
# Batch-резолюция DOI из файла
bioetl run openalex_publication --input-filter data/input/dois.csv

# С ограничением
bioetl run openalex_publication --limit 1000
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

## 7. Конфигурация

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BIOETL_OPENALEX_EMAIL` | Email для "polite pool" (требуется OpenAlex) |

---

## 8. Партиционирование

Silver и Gold таблицы партиционируются по полю `year`.

---

## 9. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/openalex/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/openalex/transformer.py` |
| Экстракторы | `src/bioetl/application/pipelines/openalex/extractors.py` |

---

*Последнее обновление: 2026-01-06*
