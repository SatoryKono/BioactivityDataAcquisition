# Пайплайн: ChEMBL Document Similarity

**Имя пайплайна:** `chembl_document_similarity`
**Провайдер:** `chembl`
**Сущность:** `document_similarity`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о сходстве документов (коэффициенты Танимото) из API ChEMBL. Используется для анализа связей между научными публикациями на основе молекулярного и таргетного сходства.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `sim_id` | `int` | Уникальный идентификатор записи сходства |
| `doc_1` | `int` | ID первого документа |
| `doc_2` | `int` | ID второго документа |
| `pubmed_id1` | `int` | PubMed ID первого документа |
| `pubmed_id2` | `int` | PubMed ID второго документа |

### Коэффициенты Танимото

| Поле | Тип | Описание |
|------|-----|----------|
| `tid_tani` | `float` | Коэффициент Танимото по таргетам |
| `mol_tani` | `float` | Коэффициент Танимото по молекулам |
| `avg_tani` | `float` | Среднее значение (вычисляемое) |
| `max_tani` | `float` | Максимальное значение (вычисляемое) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/document_similarity_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{sim_id}"
```

### Вычисляемые метрики

```python
avg_tani = round((tid_tani + mol_tani) / 2, 6)
max_tani = round(max(tid_tani, mol_tani), 6)
```

Если один из коэффициентов отсутствует, используется доступное значение.

---

## 4. Валидация

### DQ-правила

1. **`sim_id`** — обязательное
2. **`doc_1`**, **`doc_2`** — обязательные (foreign keys)

### Gold-фильтры

- `max_tani >= 0.5` — только значимые связи попадают в Gold
- Обязательные поля: `sim_id`, `doc_1`, `doc_2`

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_document_similarity

# С ограничением
bioetl run chembl_document_similarity --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/document_similarity.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/document_similarity_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/document_similarity.py` |

---

*Последнее обновление: 2026-01-06*
