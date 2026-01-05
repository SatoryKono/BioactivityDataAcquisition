# Пайплайн: ChEMBL Cell Line

**Имя пайплайна:** `chembl_cell_line`
**Провайдер:** `chembl`
**Сущность:** `cell_line`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о клеточных линиях из API ChEMBL. Клеточные линии — это биологические объекты, используемые для in vitro экспериментов. Они имеют связь M:N с сущностью Assay (через FK `assay.cell_chembl_id`).

**Источник данных:** ChEMBL REST API, таблица `cell_dictionary`

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `cell_chembl_id` | `str` | Уникальный ChEMBL ID клеточной линии (PK) |
| `cell_name` | `str` | Название клеточной линии (напр., HeLa, MCF7) |

### Метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `cell_description` | `str` | Описание клеточной линии |
| `cell_type` | `str` | Тип клеточной линии (напр., Cancer cell line) |

### Источник

| Поле | Тип | Описание |
|------|-----|----------|
| `cell_source_tissue` | `str` | Ткань-источник (напр., Cervix, Breast) |
| `cell_source_organism` | `str` | Организм-источник (напр., Homo sapiens) |
| `cell_source_tax_id` | `int` | NCBI Taxonomy ID организма-источника |

### Внешние идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `cellosaurus_id` | `str` | Cellosaurus ID (формат: `CVCL_XXXX`) |
| `clo_id` | `str` | Cell Line Ontology ID (формат: `CLO_XXXXX`) |
| `cl_lincs_id` | `str` | LINCS ID (Library of Integrated Network-Based Cellular Signatures) |
| `efo_id` | `str` | EFO ontology ID (формат: `EFO_XXXXX`) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/cell_line_transformer.py`

### Нормализация данных

- **cell_name:** Строка нормализуется через `normalize_to_string()` (strip whitespace)
- **cell_source_tax_id:** Валидируется через `validate_positive_int()` (должен быть >= 1)
- **Внешние ID:** Пустые строки и whitespace преобразуются в `NULL`

### Entity ID

```python
entity_id = f"chembl:{cell_chembl_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`cell_chembl_id`** — обязательное, формат `^CHEMBL\d+$`
2. **`cell_name`** — обязательное
3. **`cell_source_tax_id`** — если указан, должен быть >= 1
4. **Внешние ID** — если указаны, валидируются по regex:
   - `cellosaurus_id`: `^CVCL_[A-Z0-9]+$`
   - `clo_id`: `^CLO_\d+$`
   - `efo_id`: `^EFO_\d+$`

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_cell_line

# С ограничением количества записей
bioetl run chembl_cell_line --limit 500

# Полная перезагрузка
bioetl run chembl_cell_line --run-type rebuild

# С входным фильтром по списку ID
bioetl run chembl_cell_line --input-filter data/input/cell.csv
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/cell_line.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/cell_line_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/cell_line.py` |
| Схема | `src/bioetl/domain/schemas/chembl/cell_line.py` |
| Сущность | `src/bioetl/domain/entities.py` |
| Фабрика | `src/bioetl/composition/factories/pipeline_factories.py` |

---

## 7. Связи с другими сущностями

```
Cell Line (cell_chembl_id)
    └── Assay (cell_chembl_id FK) [M:N]
        └── Activity [1:N]
```

---

## 8. Примеры данных

### Bronze (raw JSON)

```json
{
  "cell_chembl_id": "CHEMBL3308376",
  "cell_name": "HeLa",
  "cell_description": "Human cervical cancer cell line",
  "cell_source_tissue": "Cervix",
  "cell_source_organism": "Homo sapiens",
  "cell_source_tax_id": 9606,
  "cell_type": "Cancer cell line",
  "cellosaurus_id": "CVCL_0030",
  "clo_id": "CLO_0003684",
  "cl_lincs_id": "LCL-1234",
  "efo_id": "EFO_0001185"
}
```

### Silver (нормализованный)

| cell_chembl_id | cell_name | cell_source_organism | cell_source_tax_id | cellosaurus_id |
|----------------|-----------|----------------------|--------------------|----------------|
| CHEMBL3308376 | HeLa | Homo sapiens | 9606 | CVCL_0030 |

---

*Последнее обновление: 2025-01-05*
