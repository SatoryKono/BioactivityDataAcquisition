# Пайплайн: ChEMBL Publication Similarity

**Имя пайплайна:** `chembl_publication_similarity`
**Провайдер:** `chembl`
**Сущность:** `publication_similarity`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о сходстве публикаций (коэффициенты Танимото) из API ChEMBL. Используется для анализа связей между научными публикациями на основе молекулярного и таргетного сходства. Endpoint API остаётся `/document-similarity`.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `sim_id` | `int` | Уникальный идентификатор записи сходства |
| `doc_1` | `int` | ID первой публикации |
| `doc_2` | `int` | ID второй публикации |
| `pubmed_id1` | `int` | PubMed ID первой публикации |
| `pubmed_id2` | `int` | PubMed ID второй публикации |

### Коэффициенты Танимото

| Поле | Тип | Описание |
|------|-----|----------|
| `tid_tani` | `float` | Коэффициент Танимото по таргетам |
| `mol_tani` | `float` | Коэффициент Танимото по молекулам |
| `avg_tani` | `float` | Среднее значение (вычисляемое) |
| `max_tani` | `float` | Максимальное значение (вычисляемое) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py`

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
bioetl run --pipeline chembl_publication_similarity

# С ограничением
bioetl run --pipeline chembl_publication_similarity --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/publication_similarity.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |

---

*Последнее обновление: 2026-03-03*
