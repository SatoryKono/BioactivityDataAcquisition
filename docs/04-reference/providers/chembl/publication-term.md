# Пайплайн: ChEMBL Publication Term

**Имя пайплайна:** `chembl_publication_term`
**Провайдер:** `chembl`
**Сущность:** `publication-term`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает термины (MeSH-дескрипторы, ключевые слова) из записей публикаций ChEMBL API. Это производная сущность — извлекает вложенные данные терминов из ответов API `/document` и преобразует связь 1:M (одна публикация → множество терминов) в плоскую структуру.

**Типы терминов:**
- `MESH-HEADING` — MeSH-дескрипторы
- `MESH-QUALIFIER` — MeSH-квалификаторы/подзаголовки
- `KEYWORD` — Ключевые слова, заданные авторами

---

## 2. Ключевые поля

### Композитный ключ

| Поле | Тип | Описание |
|------|-----|----------|
| `document-chembl-id` | `str` | FK → ChEMBL ID родительской публикации |
| `term` | `str` | Текст термина (напр., "Aspirin", "kinase inhibitor") |
| `term-type` | `str` | Тип термина: MESH-HEADING, MESH-QUALIFIER, KEYWORD |

### MeSH-специфичные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `mesh-id` | `str \| None` | MeSH идентификатор (напр., "D001241") |
| `qualifier` | `str \| None` | MeSH квалификатор (напр., "pharmacology") |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication-term-transformer.py`

### Entity ID

Entity ID вычисляется как SHA256-хэш композитного ключа:

```python
composite = f"{document-chembl-id}:{term-type}:{normalized-term}"
entity-id = hashlib.sha256(composite.encode()).hexdigest()[:16]
```

**Нормализация термина:** `term.lower().strip()`

### Извлечение терминов

Трансформер извлекает термины из двух полей публикации:
1. `mesh-terms` — массив MeSH-терминов (heading + qualifier)
2. `keywords` — массив ключевых слов авторов

---

## 4. Валидация

### DQ-правила

1. **`document-chembl-id`** — обязательное, формат `CHEMBL\d+`
2. **`term`** — обязательное, минимум 1 символ
3. **`term-type`** — обязательное, одно из: MESH-HEADING, MESH-QUALIFIER, KEYWORD, CONCEPT

### Gold-фильтры

```yaml
gold-filters:
  columns:
    term-type: [MESH-HEADING, KEYWORD]  # Основные типы терминов
  required-fields:
    - document-chembl-id
    - term
    - term-type
```

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_publication_term

# С ограничением
bioetl run chembl_publication_term --limit 1000

# С фильтрацией по публикациям
bioetl run chembl_publication_term --input-filter data/input/publications.csv
```

---

## 6. Партиционирование

Silver-таблица партиционирована по `term-type` для эффективных запросов по типу термина.

```yaml
sink:
  silver:
    partition-by: ["term-type"]
```

---

## 7. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/publication-term.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication-term-transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/publication-term.py` |
| Сущность | `src/bioetl/domain/entities/chembl-structures.py` (PublicationTerm) |
| Схема | `src/bioetl/domain/schemas/chembl/publication-term.py` |

---

## 8. Связь с родительской сущностью

`chembl_publication_term` — производная от `chembl_publication`. Для полного покрытия рекомендуется сначала загрузить публикации:

```bash
bioetl run chembl_publication --limit 100
bioetl run chembl_publication_term --limit 1000
```

---

*Последнее обновление: 2026-01-05*
