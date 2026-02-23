# Пайплайн: ChEMBL Publication Similarity

**Имя пайплайна:** `chembl_publication_similarity`
**Провайдер:** `chembl`
**Сущность:** `publication-similarity`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о сходстве публикаций (коэффициенты Танимото) из API ChEMBL. Используется для анализа связей между научными публикациями на основе молекулярного и таргетного сходства. Endpoint API остаётся `/document-similarity`.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `sim-id` | `int` | Уникальный идентификатор записи сходства |
| `doc-1` | `int` | ID первой публикации |
| `doc-2` | `int` | ID второй публикации |
| `pubmed-id1` | `int` | PubMed ID первой публикации |
| `pubmed-id2` | `int` | PubMed ID второй публикации |

### Коэффициенты Танимото

| Поле | Тип | Описание |
|------|-----|----------|
| `tid-tani` | `float` | Коэффициент Танимото по таргетам |
| `mol-tani` | `float` | Коэффициент Танимото по молекулам |
| `avg-tani` | `float` | Среднее значение (вычисляемое) |
| `max-tani` | `float` | Максимальное значение (вычисляемое) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication-similarity-transformer.py`

### Entity ID

```python
entity-id = f"chembl:{sim-id}"
```

### Вычисляемые метрики

```python
avg-tani = round((tid-tani + mol-tani) / 2, 6)
max-tani = round(max(tid-tani, mol-tani), 6)
```

Если один из коэффициентов отсутствует, используется доступное значение.

---

## 4. Валидация

### DQ-правила

1. **`sim-id`** — обязательное
2. **`doc-1`**, **`doc-2`** — обязательные (foreign keys)

### Gold-фильтры

- `max-tani >= 0.5` — только значимые связи попадают в Gold
- Обязательные поля: `sim-id`, `doc-1`, `doc-2`

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_publication_similarity

# С ограничением
bioetl run chembl_publication_similarity --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/publication-similarity.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication-similarity-transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/publication-similarity.py` |

---

*Последнее обновление: 2026-01-06*
