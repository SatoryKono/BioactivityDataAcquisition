# Пайплайн: ChEMBL Cell Line

**Имя пайплайна:** `chembl_cell_line`
**Провайдер:** `chembl`
**Сущность:** `cell-line`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о клеточных линиях из API ChEMBL. Клеточные линии — это биологические объекты, используемые для in vitro экспериментов. Они имеют связь M:N с сущностью Assay (через FK `assay.cell_chembl_id`).

**Источник данных:** ChEMBL REST API, таблица `cell-dictionary`

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `cell_chembl_id` | `str` | Уникальный ChEMBL ID клеточной линии (PK) |
| `cell-name` | `str` | Название клеточной линии (напр., HeLa, MCF7) |

### Метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `cell-description` | `str` | Описание клеточной линии |
| `cell-type` | `str` | Тип клеточной линии (напр., Cancer cell line) |

### Источник

| Поле | Тип | Описание |
|------|-----|----------|
| `cell-source-tissue` | `str` | Ткань-источник (напр., Cervix, Breast) |
| `cell-source-organism` | `str` | Организм-источник (напр., Homo sapiens) |
| `cell-source-tax-id` | `int` | NCBI Taxonomy ID организма-источника |

### Внешние идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `cellosaurus-id` | `str` | Cellosaurus ID (формат: `CVCL-XXXX`) |
| `clo-id` | `str` | Cell Line Ontology ID (формат: `CLO-XXXXX`) |
| `cl-lincs-id` | `str` | LINCS ID (Library of Integrated Network-Based Cellular Signatures) |
| `efo-id` | `str` | EFO ontology ID (формат: `EFO-XXXXX`) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/cell_line_transformer.py`

### Нормализация данных

- **cell-name:** Строка нормализуется через `normalize_to_string()` (strip whitespace)
- **cell-source-tax-id:** Валидируется через `validate-positive-int()` (должен быть >= 1)
- **Внешние ID:** Пустые строки и whitespace преобразуются в `NULL`

### Entity ID

```python
entity_id = f"chembl:{cell_chembl_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`cell_chembl_id`** — обязательное, формат `^CHEMBL\d+$`
2. **`cell-name`** — обязательное
3. **`cell-source-tax-id`** — если указан, должен быть >= 1
4. **Внешние ID** — если указаны, валидируются по regex:
   - `cellosaurus-id`: `^CVCL-[A-Z0-9]+$`
   - `clo-id`: `^CLO-\d+$`
   - `efo-id`: `^EFO-\d+$`

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_cell_line

# С ограничением количества записей
bioetl run --pipeline chembl_cell_line --limit 500

# Полная перезагрузка
bioetl run --pipeline chembl_cell_line --run-type rebuild

# С входным фильтром по списку ID
bioetl run --pipeline chembl_cell_line --input-csv data/input/cell.csv
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/cell_line.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/cell_line_transformer.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |
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
  "cell-name": "HeLa",
  "cell-description": "Human cervical cancer cell line",
  "cell-source-tissue": "Cervix",
  "cell-source-organism": "Homo sapiens",
  "cell-source-tax-id": 9606,
  "cell-type": "Cancer cell line",
  "cellosaurus-id": "CVCL-0030",
  "clo-id": "CLO-0003684",
  "cl-lincs-id": "LCL-1234",
  "efo-id": "EFO-0001185"
}
```

### Silver (нормализованный)

| cell_chembl_id | cell-name | cell-source-organism | cell-source-tax-id | cellosaurus-id |
|----------------|-----------|----------------------|--------------------|----------------|
| CHEMBL3308376 | HeLa | Homo sapiens | 9606 | CVCL-0030 |

---

*Последнее обновление: 2025-01-05*
