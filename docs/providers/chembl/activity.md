# Пайплайн: ChEMBL Activity

**Имя пайплайна:** `chembl_activity`
**Провайдер:** `chembl`
**Сущность:** `activity`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о биологической активности молекул из API ChEMBL. Каждая запись содержит результат измерения активности (IC50, Ki и др.) для пары молекула-мишень.

---

## 2. Конфигурация

**Файл:** `configs/pipelines/chembl/activity.yaml`

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.0.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"

gold_filter_types:
    - IC50
    - Ki

transform:
    steps:
        - normalize_values
        - add_metadata
        - calculate_content_hash

sink:
    bronze:
        path: "data/output/bronze"
        format: jsonl
        save_json: true
    silver:
        path: "data/output/silver"
        format: delta
        mode: merge
        partition_by: ["year", "month"]
    gold:
        enabled: true
        path: "data/output/gold"
        format: delta
        mode: overwrite

dq_rules:
    soft_fail_threshold: 0.05   # 5% ошибок → WARNING
    hard_fail_threshold: 0.20   # 20% ошибок → FAIL BATCH
```

---

## 3. Схема данных

### 3.1. Определение сущности Activity

**Файл:** `src/bioetl/domain/entities.py`

Сущность `Activity` содержит **52 поля**, сгруппированных по категориям:

#### Идентификаторы

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `activity_id` | `str` | **Да** | Уникальный идентификатор записи активности |
| `molecule_chembl_id` | `str` | **Да** | ChEMBL ID молекулы (например, `CHEMBL25`) |
| `target_chembl_id` | `str` | Нет | ChEMBL ID мишени |
| `assay_chembl_id` | `str` | Нет | ChEMBL ID анализа |
| `document_chembl_id` | `str` | Нет | ChEMBL ID публикации |
| `record_id` | `int` | Нет | Внутренний ID записи |
| `src_id` | `int` | Нет | ID источника данных |

#### Данные молекулы

| Поле | Тип | Описание |
|------|-----|----------|
| `canonical_smiles` | `str` | SMILES-формула молекулы |
| `molecule_pref_name` | `str` | Предпочтительное название молекулы |
| `parent_molecule_chembl_id` | `str` | ID родительской молекулы |

#### Данные мишени

| Поле | Тип | Описание |
|------|-----|----------|
| `target_pref_name` | `str` | Название мишени |
| `target_organism` | `str` | Организм мишени |
| `target_tax_id` | `str` | Таксономический ID |

#### Данные анализа

| Поле | Тип | Описание |
|------|-----|----------|
| `assay_type` | `str` | Тип анализа (B, F, A, T, P) |
| `assay_description` | `str` | Описание анализа |
| `bao_endpoint` | `str` | BAO endpoint (онтология) |
| `bao_format` | `str` | BAO format |
| `bao_label` | `str` | BAO label |

#### Сырые значения активности

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `str` | Тип измерения (сырой) |
| `value` | `float` | Значение (сырое) |
| `units` | `str` | Единицы измерения (сырые) |
| `relation` | `str` | Отношение (`=`, `<`, `>`, `~`) |
| `upper_value` | `float` | Верхняя граница диапазона |
| `text_value` | `str` | Текстовое значение |

#### Стандартизированные значения

| Поле | Тип | Описание |
|------|-----|----------|
| `standard_type` | `str` | Тип: IC50, Ki, EC50, Kd и др. |
| `standard_value` | `float` | Стандартизированное значение |
| `standard_units` | `str` | Единицы: nM, uM, и др. |
| `standard_relation` | `str` | Отношение |
| `standard_upper_value` | `float` | Верхняя граница |
| `standard_flag` | `int` | Флаг стандартизации |

#### Вычисляемые метрики

| Поле | Тип | Описание |
|------|-----|----------|
| `pchembl_value` | `float` | pChEMBL = -log10(IC50 в молях) |
| `ligand_efficiency` | `str` | Эффективность лиганда (JSON) |

#### Метаданные качества

| Поле | Тип | Описание |
|------|-----|----------|
| `activity_comment` | `str` | Комментарий к активности |
| `data_validity_comment` | `str` | Комментарий о валидности |
| `data_validity_description` | `str` | Описание проблемы с данными |
| `potential_duplicate` | `int` | Флаг потенциального дубликата |

#### Системные поля (добавляются при обработке)

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_id` | `str` | `chembl:{activity_id}` |
| `content_hash` | `str` | SHA256-хеш содержимого |
| `_run_id` | `str` | UUID запуска пайплайна |
| `_run_type` | `str` | `incremental`, `backfill`, `rebuild` |
| `_source_batch_id` | `str` | UUID батча |
| `_ingestion_ts` | `str` | Timestamp загрузки (ISO8601) |

---

### 3.2. Валидация при создании сущности

```python
def _validate_invariants(self) -> None:
    if not self.activity_id:
        raise ValueError("Activity ID is required")
    if not self.molecule_chembl_id:
        raise ValueError("Molecule ID is required")
    if self.pchembl_value is not None and self.pchembl_value < 0:
        raise ValueError("pChemBL value must be non-negative")
```

---

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/activity_transformer.py`

### 4.1. Этапы трансформации

```
Сырой JSON (ChEMBL API)
         │
         ▼
    1. Генерация entity_id
         │
         ▼
    2. Нормализация типов
         │
         ▼
    3. Генерация content_hash
         │
         ▼
    4. Добавление системных полей
         │
         ▼
    SilverRecord (dict)
```

### 4.2. Правила нормализации типов

| Исходный тип | Преобразование |
|--------------|----------------|
| `float` с NaN/Inf | → `None` |
| `float` | → `round(value, 10)` |
| `int` | → безопасная конвертация или `None` |
| `str` | → `strip()` |
| `dict`, `list` | → JSON-строка |

### 4.3. Генерация идентификаторов

```python
# Entity ID: уникальный бизнес-ключ
entity_id = f"chembl:{activity_id}"

# Content Hash: SHA256 для версионирования
content_hash = sha256(
    "chembl" + canonical_json(business_fields)
)
```

### 4.4. Поля, исключённые из хеша

```python
META_FIELDS = {
    "_ingestion_ts",
    "_run_id",
    "_run_type",
    "_dq_warn",
    "_dq_error",
    "_source_batch_id",
}
```

---

## 5. Валидация и Data Quality

### 5.1. Классификация ошибок

| Тип | Поведение | Примеры |
|-----|-----------|---------|
| **Critical** | Остановка пайплайна | Auth failure, schema mismatch |
| **Recoverable** | Retry (3x, backoff 2.0) | 429, 502, 504 |
| **Data Quality** | Карантин записи | Invalid SMILES, missing field |

### 5.2. DQ-правила для Activity

1. **`standard_value` > 0** — не null, не отрицательный
2. **`standard_type`** ∈ {IC50, Ki, EC50, Kd, ...}
3. **`molecule_chembl_id`** соответствует regex `^CHEMBL\d+$`

### 5.3. Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок в батче | WARNING в лог |
| Hard | > 20% ошибок в батче | `DataQualityThresholdError` |

### 5.4. Карантин

Записи, не прошедшие валидацию, отправляются в карантин:

```python
{
    "raw_record": {...},      # Исходная запись
    "error_code": "INVALID_STANDARD_VALUE",
    "error_details": "standard_value is negative",
    "batch_id": "uuid",
    "timestamp": "2025-12-19T10:30:00Z"
}
```

---

## 6. Запись в слои Medallion

### 6.1. Bronze Layer

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

```
Путь: bronze/v1/chembl/activity/2025-12-19/batch_{uuid}.jsonl.zst
```

| Параметр | Значение |
|----------|----------|
| **Формат** | JSONL + Zstandard (level 3) |
| **Режим** | Append-only |
| **Retention** | 90 дней |
| **Chunk size** | 256 KB |

**Metadata sidecar** (`.meta.json`):
```json
{
    "run_id": "uuid",
    "run_type": "incremental",
    "ingestion_ts": "2025-12-19T10:30:00Z",
    "provider": "chembl",
    "entity": "activity",
    "batch_id": "uuid"
}
```

---

### 6.2. Silver Layer

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

**PyArrow Schema** (`src/bioetl/infrastructure/schemas/silver.py`):

```python
CHEMBL_ACTIVITY_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("activity_id", pa.string()),
    pa.field("molecule_chembl_id", pa.string()),
    pa.field("target_chembl_id", pa.string()),
    pa.field("standard_type", pa.string()),
    pa.field("standard_value", pa.float64()),
    pa.field("standard_units", pa.string()),
    pa.field("pchembl_value", pa.float64()),
    pa.field("_run_id", pa.string()),
    pa.field("_run_type", pa.string()),
    pa.field("_ingestion_ts", pa.string()),
    # ... всего 52 поля
])
```

| Параметр | Значение |
|----------|----------|
| **Формат** | Delta Lake |
| **Merge Key** | `activity_id` |
| **Партиционирование** | `year`, `month` |
| **Приоритет конфликтов** | REBUILD > BACKFILL > INCREMENTAL |

---

### 6.3. Gold Layer

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Фильтр для Gold

```python
def should_include(self, context, record) -> bool:
    return all([
        record.get("standard_value") is not None,  # Есть значение
        record.get("standard_units"),               # Есть единицы
        record.get("target_chembl_id"),             # Есть мишень
        record.get("standard_type") in {"IC50", "Ki"},  # Правильный тип
        not record.get("data_validity_comment"),    # Нет флагов проблем
    ])
```

| Параметр | Значение |
|----------|----------|
| **Формат** | Delta Lake |
| **Режим** | Overwrite |
| **Валидация** | Strict Pandera schema |

#### Data Contract

**Файл:** `docs/contracts/gold/activity.json`

```json
{
    "required": [
        "activity_id",
        "molecule_chembl_id",
        "_content_hash",
        "_ingestion_ts"
    ],
    "properties": {
        "activity_id": {"type": "integer"},
        "molecule_chembl_id": {"type": "string", "pattern": "^CHEMBL\\d+$"},
        "standard_type": {"type": "string"},
        "standard_value": {"type": ["number", "null"]},
        "pchembl_value": {"type": ["number", "null"]}
    }
}
```

---

## 7. Полный поток данных

```
ChEMBL API (/activity.json)
         │
         ▼
┌─────────────────────────────────────────┐
│  BRONZE (сырые данные)                  │
│  ─────────────────────────────────────  │
│  • Путь: bronze/v1/chembl/activity/...  │
│  • Формат: JSONL + Zstandard            │
│  • Режим: Append-only                   │
│  • Retention: 90 дней                   │
└─────────────────────────────────────────┘
         │
         ▼ ActivityTransformer.transform()
         │
         ├── DQ Error? ──► QUARANTINE
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────┐
│  SILVER (нормализованные данные)        │
│  ─────────────────────────────────────  │
│  • Формат: Delta Lake                   │
│  • Merge by: activity_id                │
│  • Schema: 52 поля (PyArrow)            │
│  • Партиции: year/month                 │
└─────────────────────────────────────────┘
         │
         ▼ ActivityGoldFilter.should_include()
         │
         ├── Не прошёл? ──► (пропускаем)
         │
         ▼
┌─────────────────────────────────────────┐
│  GOLD (бизнес-данные)                   │
│  ─────────────────────────────────────  │
│  • Только IC50/Ki с полными данными     │
│  • Strict Pandera validation            │
│  • Режим: Overwrite                     │
└─────────────────────────────────────────┘
```

---

## 8. Результат обработки батча

```python
@dataclass
class BatchResult:
    bronze_count: int       # Записей в Bronze
    silver_count: int       # Успешно трансформировано
    gold_count: int         # Прошло Gold-фильтр
    quarantined_count: int  # Отправлено в карантин
```

---

## 9. Watermark (инкрементальная загрузка)

**Файл:** `src/bioetl/application/pipelines/chembl/activity_watermark.py`

Для инкрементальных запусков используется `activity_id` как watermark:

```python
def extract(self, context, record) -> Watermark:
    activity_id = record.get("activity_id")
    if activity_id is not None:
        return Watermark.from_id(str(activity_id))
    return Watermark.from_id("")
```

---

## 10. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/activity.yaml` |
| Сущность | `src/bioetl/domain/entities.py` |
| Трансформер | `src/bioetl/application/pipelines/chembl/activity_transformer.py` |
| Gold-фильтр | `src/bioetl/application/pipelines/chembl/activity_gold_filter.py` |
| Watermark | `src/bioetl/application/pipelines/chembl/activity_watermark.py` |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` |
| Bronze Writer | `src/bioetl/infrastructure/storage/bronze_writer.py` |
| Delta Writer | `src/bioetl/infrastructure/storage/delta_writer.py` |
| Gold Writer | `src/bioetl/infrastructure/storage/gold_writer.py` |
| Data Contract | `docs/contracts/gold/activity.json` |

---

## 11. Пример использования CLI

```bash
# Инкрементальная загрузка (по умолчанию)
bioetl run chembl_activity

# С ограничением количества записей
bioetl run chembl_activity --limit 1000

# Backfill за период
bioetl run chembl_activity --run-type backfill --start-date 2024-01-01

# Полная перезагрузка
bioetl run chembl_activity --run-type rebuild
```

---

*Последнее обновление: 2025-12-19*
