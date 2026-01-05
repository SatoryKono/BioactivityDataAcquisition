# Пайплайн: ChEMBL Document Term

**Имя пайплайна:** `chembl_document_term`
**Провайдер:** `chembl`
**Сущность:** `document_term`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает термины (MeSH-дескрипторы, ключевые слова) из записей документов ChEMBL API. Это производная сущность — извлекает вложенные данные терминов из ответов API `/document` и преобразует связь 1:M (один документ → множество терминов) в плоскую структуру.

**Типы терминов:**
- `MESH_HEADING` — MeSH-дескрипторы
- `MESH_QUALIFIER` — MeSH-квалификаторы/подзаголовки
- `KEYWORD` — Ключевые слова, заданные авторами

---

## 2. Ключевые поля

### Композитный ключ

| Поле | Тип | Описание |
|------|-----|----------|
| `document_chembl_id` | `str` | FK → ChEMBL ID родительского документа |
| `term` | `str` | Текст термина (напр., "Aspirin", "kinase inhibitor") |
| `term_type` | `str` | Тип термина: MESH_HEADING, MESH_QUALIFIER, KEYWORD |

### MeSH-специфичные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `mesh_id` | `str \| None` | MeSH идентификатор (напр., "D001241") |
| `qualifier` | `str \| None` | MeSH квалификатор (напр., "pharmacology") |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/document_term_transformer.py`

### Entity ID

Entity ID вычисляется как SHA256-хэш композитного ключа:

```python
composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
entity_id = hashlib.sha256(composite.encode()).hexdigest()[:16]
```

**Нормализация термина:** `term.lower().strip()`

### Извлечение терминов

Трансформер извлекает термины из двух полей документа:
1. `mesh_terms` — массив MeSH-терминов (heading + qualifier)
2. `keywords` — массив ключевых слов авторов

---

## 4. Валидация

### DQ-правила

1. **`document_chembl_id`** — обязательное, формат `CHEMBL\d+`
2. **`term`** — обязательное, минимум 1 символ
3. **`term_type`** — обязательное, одно из: MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT

### Gold-фильтры

```yaml
gold_filters:
  columns:
    term_type: [MESH_HEADING, KEYWORD]  # Основные типы терминов
  required_fields:
    - document_chembl_id
    - term
    - term_type
```

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_document_term

# С ограничением
bioetl run chembl_document_term --limit 1000

# С фильтрацией по документам
bioetl run chembl_document_term --input-filter data/input/documents.csv
```

---

## 6. Партиционирование

Silver-таблица партиционирована по `term_type` для эффективных запросов по типу термина.

```yaml
sink:
  silver:
    partition_by: ["term_type"]
```

---

## 7. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/document_term.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/document_term_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/document_term.py` |
| Сущность | `src/bioetl/domain/entities/chembl_structures.py` (DocumentTerm) |
| Схема | `src/bioetl/domain/schemas/chembl/document_term.py` |

---

## 8. Связь с родительской сущностью

`chembl_document_term` — производная от `chembl_document`. Для полного покрытия рекомендуется сначала загрузить документы:

```bash
bioetl run chembl_document --limit 100
bioetl run chembl_document_term --limit 1000
```

---

*Последнее обновление: 2026-01-05*
