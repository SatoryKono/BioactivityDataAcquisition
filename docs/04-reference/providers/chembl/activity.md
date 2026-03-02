# Пайплайн: ChEMBL Activity

**Имя пайплайна:** `chembl_activity`
**Провайдер:** `chembl`
**Сущность:** `activity`
**Версия схемы:** 1.2.0

----------------------------------------------------------------------

## 1. Описание

Пайплайн извлекает данные о биологической активности молекул из API ChEMBL. Каждая запись содержит результат измерения активности (IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50 и др.) для пары молекула-мишень.

----------------------------------------------------------------------

## 2. Конфигурация

**Файл:** `configs/entities/chembl/activity.yaml`

```yaml
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
primary_keys: ["activity_id"]
silver_table: "chembl_activity"

gold-filter-types:
    - IC50
    - Ki
    - Kd
    - EC50
    - AC50
    - GI50
    - ED50
    - MIC
    - CC50

transform:
    steps:
        - normalize-values
        - add-metadata
        - calculate-content-hash

sink:
    bronze:
        path: "data/output/bronze"
        format: jsonl
        save-json: true
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

dq_overrides:
    soft_fail_threshold: 0.05   # 5% ошибок → WARNING
    hard_fail_threshold: 0.20   # 20% ошибок → FAIL BATCH
```

----------------------------------------------------------------------

## 3. Схема данных

### 3.1. Определение сущности Activity

**Файл:** `src/bioetl/domain/entities/bioactivity.py`

Сущность `Bioactivity` содержит **63 dataclass-поля** (включая унаследованные служебные поля `BaseEntity`), сгруппированных по категориям:

#### Идентификаторы

| Поле                 | Тип   | Обязательное | Описание                                   |
| -------------------- | ----- | ------------ | ------------------------------------------ |
| `activity_id`        | `str` | **Да**       | Уникальный идентификатор записи активности |
| `molecule_id`        | `str` | **Да**       | Канонический ID молекулы (например, `CHEMBL25`) |
| `target_id`          | `str` | Нет          | Канонический ID мишени                     |
| `assay_id`           | `str` | Нет          | Канонический ID анализа                    |
| `publication_id`     | `str` | Нет          | Канонический ID публикации (provider PK)   |
| `publication_doi`    | `str` | Нет          | DOI публикации                             |
| `publication_pmid`   | `str` | Нет          | PubMed ID                                  |
| `publication_pmc_id` | `str` | Нет          | PubMed Central ID                          |
| `record-id`          | `int` | Нет          | Внутренний ID записи                       |
| `src-id`             | `int` | Нет          | ID источника данных                        |

#### Данные молекулы

| Поле                        | Тип   | Описание                           |
| --------------------------- | ----- | ---------------------------------- |
| `canonical-smiles`          | `str` | SMILES-формула молекулы            |
| `molecule-pref-name`        | `str` | Предпочтительное название молекулы |
| `parent-molecule_id`        | `str` | ID родительской молекулы           |

#### Данные мишени

|Поле|Тип|Описание|
|---|---|---|
|`target-pref-name`|`str`|Название мишени|
|`target-organism`|`str`|Организм мишени|
|`taxonomy-id`|`float`|NCBI Taxonomy ID (nullable int pattern)|

#### Данные анализа

|Поле|Тип|Описание|
|---|---|---|
|`assay-type`|`str`|Тип анализа (B, F, A, T, P)|
|`assay-description`|`str`|Описание анализа|
|`assay-variant-accession`|`str`|Accession варианта белка в анализе|
|`assay-variant-mutation`|`str`|Мутация варианта в анализе|
|`bao-endpoint`|`str`|BAO endpoint (онтология)|
|`bao-format`|`str`|BAO format|
|`bao-label`|`str`|BAO label|

#### Сырые значения активности

| Поле          | Тип     | Описание                       |
| ------------- | ------- | ------------------------------ |
| `type`        | `str`   | Тип измерения (сырой)          |
| `value`       | `float` | Значение (сырое)               |
| `units`       | `str`   | Единицы измерения (сырые)      |
| `relation`    | `str`   | Отношение (`=`, `<`, `>`, `~`) |
| `upper-value` | `float` | Верхняя граница диапазона      |
| `text-value`  | `str`   | Текстовое значение             |
| `qudt-units`  | `str`   | Единицы из онтологии QUDT      |
| `uo-units`    | `str`   | Единицы из онтологии UO        |

#### Стандартизированные значения

| Поле                   | Тип     | Описание                                                             |
| ---------------------- | ------- | -------------------------------------------------------------------- |
| `standard_type`        | `str`   | Тип: IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd и др. |
| `standard_value`       | `float` | Стандартизированное значение                                         |
| `standard_units`       | `str`   | Единицы: nM, uM, и др.                                               |
| `standard-relation`    | `str`   | Отношение                                                            |
| `standard-upper-value` | `float` | Верхняя граница                                                      |
| `standard-text-value`  | `str`   | Текстовое стандартизированное значение                               |
| `standard-flag`        | `int`   | Флаг стандартизации                                                  |

#### Вычисляемые метрики

| Поле            | Тип     | Описание                       |
| --------------- | ------- | ------------------------------ |
| `pchembl_value` | `float` | pChEMBL = -log10(IC50 в молях) |

##### Метрики эффективности лиганда (Ligand Efficiency)

| Поле                    | Тип     | Описание                                                                   |
| ----------------------- | ------- | -------------------------------------------------------------------------- |
| `ligand-efficiency-bei` | `float` | **BEI** (Binding Efficiency Index) — эффективность связывания на атом      |
| `ligand-efficiency-le`  | `float` | **LE** (Ligand Efficiency) — изменение энергии связывания на тяжелый атом  |
| `ligand-efficiency-lle` | `float` | **LLE** (Lipophilic Ligand Efficiency) — баланс активности и липофильности |
| `ligand-efficiency-sei` | `float` | **SEI** (Surface Efficiency Index) — эффективность по площади поверхности  |

> **Примечание**: Все метрики ligand-efficiency вычисляются ChEMBL и предоставляются через API. В Silver слое они разворачиваются из вложенного словаря в отдельные колонки для удобства аналитики.

#### Данные публикации (Document/Publication data)

| Поле               | Тип   | Описание                              |
| ------------------ | ----- | ------------------------------------- |
| `journal`          | `str` | Журнал публикации                     |
| `publication_year` | `int` | Год публикации                        |

#### Метаданные качества

|Поле|Тип|Описание|
|---|---|---|
|`activity-comment`|`str`|Комментарий к активности|
|`data_validity_comment`|`str`|Комментарий о валидности|
|`data-validity-description`|`str`|Описание проблемы с данными|
|`potential-duplicate`|`int`|Флаг потенциального дубликата|
|`manual-curation-flag`|`int`|Флаг ручной кураторской проверки (0/1)|
|`original-activity_id`|`int`|ID исходной записи активности (traceability)|

#### Тип действия (Action Type)

Поля развёрнуты из вложенного словаря ChEMBL API (`action-type`):

| Поле               | Тип   | Описание                                            |
| ------------------ | ----- | --------------------------------------------------- |
| `action-type`      | `str` | Тип действия: INHIBITOR, AGONIST, ANTAGONIST и др.  |
| `action-type-description` | `str` | Описание типа действия                              |
| `action-type-parent-type` | `str` | Родительская группа типа действия (может быть null) |

> **Примечание**: Поля `action-type-*` извлекаются из вложенного словаря API с помощью `flatten-nested-dict()`. Если запись не содержит информации о типе действия, все поля будут `None`.

#### Системные поля (добавляются при обработке)

| Поле               | Тип   | Описание                             |
| ------------------ | ----- | ------------------------------------ |
| `entity-id`        | `str` | `chembl:{activity_id}`               |
| `content-hash`     | `str` | SHA256-хеш содержимого               |
| `-run_id`          | `str` | UUID запуска пайплайна               |
| `-run_type`        | `str` | `incremental`, `backfill`, `rebuild` |
| `-source-batch_id` | `str` | UUID батча                           |
| `-ingestion_ts`    | `str` | Timestamp загрузки (ISO8601)         |

----------------------------------------------------------------------

### 3.2. Валидация при создании сущности

```python
def -validate-invariants(self) -> None:
    if not self.activity_id:
        raise ValueError("Activity ID is required")
    if not self.molecule_id:
        raise ValueError("Molecule ID is required")
    if self.pchembl_value is not None and self.pchembl_value < 0:
        raise ValueError("pChemBL value must be non-negative")
```

----------------------------------------------------------------------

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/activity_transformer.py`

### 4.1. Этапы трансформации

```
Сырой JSON (ChEMBL API)
         │
         ▼
    1. Генерация entity-id
         │
         ▼
    2. Нормализация типов
         │
         ▼
    3. Генерация content-hash
         │
         ▼
    4. Добавление системных полей
         │
         ▼
    SilverRecord (dict)
```

### 4.2. Правила нормализации типов

| Исходный тип      | Преобразование                      |
| ----------------- | ----------------------------------- |
| `float` с NaN/Inf | → `None`                            |
| `float`           | → `round(value, 10)`                |
| `int`             | → безопасная конвертация или `None` |
| `str`             | → `strip()`                         |
| `dict`, `list`    | → JSON-строка                       |

### 4.3. Генерация идентификаторов

```python
# Entity ID: уникальный бизнес-ключ
entity-id = f"chembl:{activity_id}"

# Content Hash: SHA256 для версионирования
content-hash = sha256("chembl" + canonical-json(business-fields))
```

### 4.4. Поля, исключённые из хеша

```python
META_FIELDS = {
    "-ingestion_ts",
    "-run_id",
    "-run_type",
    "-dq-warn",
    "-dq-error",
    "-source-batch_id",
}
```

----------------------------------------------------------------------

## 5. Валидация и Data Quality

### 5.1. Классификация ошибок

| Тип              | Поведение               | Примеры                       |
| ---------------- | ----------------------- | ----------------------------- |
| **Critical**     | Остановка пайплайна     | Auth failure, schema mismatch |
| **Recoverable**  | Retry (3x, backoff 2.0) | 429, 502, 504                 |
| **Data Quality** | Карантин записи         | Invalid SMILES, missing field |

### 5.2. DQ-правила для Activity

1. **`standard_value` > 0** — не null, не отрицательный
1. **`standard_type`** ∈ {IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd, ...}
1. **`molecule_id`** соответствует regex `^CHEMBL\d+$`

### 5.3. Пороги ошибок

| Порог | Условие              | Действие                    |
| ----- | -------------------- | --------------------------- |
| Soft  | > 5% ошибок в батче  | WARNING в лог               |
| Hard  | > 20% ошибок в батче | `DataQualityThresholdError` |

### 5.4. Карантин

Записи, не прошедшие валидацию, отправляются в карантин:

```python
{
    "raw-record": {...},  # Исходная запись
    "error_code": "INVALID-STANDARD-VALUE",
    "error_details": "standard_value is negative",
    "batch_id": "uuid",
    "timestamp": "2025-12-19T10:30:00Z",
}
```

----------------------------------------------------------------------

## 6. Запись в слои Medallion

### 6.1. Bronze Layer

**Файл:** `src/bioetl/infrastructure/storage/bronze_writer.py`

```
Путь: bronze/v1/chembl/activity/2025-12-19/batch-{uuid}.jsonl.zst
```

| Параметр       | Значение                    |
| -------------- | --------------------------- |
| **Формат**     | JSONL + Zstandard (level 3) |
| **Режим**      | Append-only                 |
| **Retention**  | 90 дней                     |
| **Chunk size** | 256 KB                      |

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

----------------------------------------------------------------------

### 6.2. Silver Layer

**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`

**PyArrow Schema** (`src/bioetl/infrastructure/schemas/silver.py`):

```python
CHEMBL_ACTIVITY_SCHEMA = pa.schema(
    [
        pa.field("entity-id", pa.string()),
        pa.field("content-hash", pa.string()),
        pa.field("activity_id", pa.string()),
        pa.field("molecule_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("assay_id", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("publication_doi", pa.string()),
        pa.field("publication_pmid", pa.string()),
        pa.field("publication_pmc_id", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("standard_type", pa.string()),
        pa.field("standard_value", pa.float64()),
        pa.field("standard_units", pa.string()),
        pa.field("pchembl_value", pa.float64()),
        pa.field("-run_id", pa.string()),
        pa.field("-run_type", pa.string()),
        pa.field("-ingestion_ts", pa.string()),
        # ... всего 62 поля (включая action-type*)
    ]
)
```

| Параметр                 | Значение                         |
| ------------------------ | -------------------------------- |
| **Формат**               | Delta Lake                       |
| **Merge Key**            | `activity_id`                    |
| **Партиционирование**    | `year`, `month`                  |
| **Приоритет конфликтов** | REBUILD > BACKFILL > INCREMENTAL |

----------------------------------------------------------------------

### 6.3. Gold Layer

**Файл:** `src/bioetl/infrastructure/storage/gold_writer.py`

#### Фильтр для Gold

```python
def should_include(self, context, record) -> bool:
    return all(
        [
            record.get("standard_value") is not None,  # Есть значение
            record.get("standard_units"),  # Есть единицы
            record.get("target_id"),  # Есть мишень
            record.get("standard_type") in {"IC50", "Ki", "Kd", "EC50", "AC50", "GI50", "ED50", "MIC", "CC50"},  # 9 типов
            not record.get("data_validity_comment"),  # Нет флагов проблем
        ]
    )
```

| Параметр      | Значение              |
| ------------- | --------------------- |
| **Формат**    | Delta Lake            |
| **Режим**     | Overwrite             |
| **Валидация** | Strict Pandera schema |

#### Data Contract

**Файл:** `docs/04-reference/contracts/gold/chembl_activity-v1.0.json`

```json
{
    "required": [
        "activity_id",
        "molecule_id",
        "-content-hash",
        "-ingestion_ts"
    ],
    "properties": {
        "activity_id": {"type": "integer"},
        "molecule_id": {"type": "string", "pattern": "^CHEMBL\\d+$"},
        "standard_type": {"type": "string"},
        "standard_value": {"type": ["number", "null"]},
        "pchembl_value": {"type": ["number", "null"]}
    }
}
```

----------------------------------------------------------------------

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
│  • Schema: 62 поля (PyArrow)            │
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
│  • IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50 │
│  • Strict Pandera validation            │
│  • Режим: Overwrite                     │
└─────────────────────────────────────────┘
```

----------------------------------------------------------------------

## 8. Результат обработки батча

```python
@dataclass
class BatchResult:
    bronze-count: int  # Записей в Bronze
    silver-count: int  # Успешно трансформировано
    gold-count: int  # Прошло Gold-фильтр
    quarantined-count: int  # Отправлено в карантин
```

----------------------------------------------------------------------

## 9. Инкрементальная загрузка

Отдельный watermark-модуль удалён (см. ADR-011). Инкрементальность обеспечивается
через `run_type`, checkpoints и идемпотентный merge по ключам/хешу.

----------------------------------------------------------------------

## 10. Связанные файлы

| Компонент     | Путь                                                              |
| ------------- | ----------------------------------------------------------------- |
| Конфигурация  | `configs/entities/chembl/activity.yaml`                          |
| Сущность      | `src/bioetl/domain/entities/bioactivity.py`                       |
| Трансформер   | `src/bioetl/application/pipelines/chembl/activity_transformer.py` |
| Gold-фильтр   | `configs/entities/chembl/activity.yaml` (`filters.gold_filters`)   |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py`            |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py`                     |
| Bronze Writer | `src/bioetl/infrastructure/storage/bronze_writer.py`              |
| Delta Writer  | `src/bioetl/infrastructure/storage/delta_writer.py`               |
| Gold Writer   | `src/bioetl/infrastructure/storage/gold_writer.py`                |
| Data Contract | `docs/04-reference/contracts/gold/chembl_activity-v1.0.json`                               |

----------------------------------------------------------------------

## 11. Пример использования CLI

```bash
# Инкрементальная загрузка (по умолчанию)
bioetl run --pipeline chembl_activity

# С ограничением количества записей
bioetl run --pipeline chembl_activity --limit 1000

# Backfill за период
bioetl run --pipeline chembl_activity --run_type backfill

# Полная перезагрузка
bioetl run --pipeline chembl_activity --run_type rebuild
```

----------------------------------------------------------------------

*Последнее обновление: 2025-12-24*
