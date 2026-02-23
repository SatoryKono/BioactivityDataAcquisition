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

**Файл:** `configs/pipelines/chembl/activity.yaml`

```yaml
pipeline-name: chembl_activity
provider: chembl
entity-type: activity
version: "1.2.0"
primary-keys: ["activity-id"]
silver-table: "chembl_activity"

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
        partition-by: ["year", "month"]
    gold:
        enabled: true
        path: "data/output/gold"
        format: delta
        mode: overwrite

dq-overrides:
    soft-fail-threshold: 0.05   # 5% ошибок → WARNING
    hard-fail-threshold: 0.20   # 20% ошибок → FAIL BATCH
```

----------------------------------------------------------------------

## 3. Схема данных

### 3.1. Определение сущности Activity

**Файл:** `src/bioetl/domain/entities/bioactivity.py`

Сущность `Bioactivity` содержит **63 dataclass-поля** (включая унаследованные служебные поля `BaseEntity`), сгруппированных по категориям:

#### Идентификаторы

| Поле                 | Тип   | Обязательное | Описание                                   |
| -------------------- | ----- | ------------ | ------------------------------------------ |
| `activity-id`        | `str` | **Да**       | Уникальный идентификатор записи активности |
| `molecule-id`        | `str` | **Да**       | Канонический ID молекулы (например, `CHEMBL25`) |
| `target-id`          | `str` | Нет          | Канонический ID мишени                     |
| `assay-id`           | `str` | Нет          | Канонический ID анализа                    |
| `publication-id`     | `str` | Нет          | Канонический ID публикации (provider PK)   |
| `publication-doi`    | `str` | Нет          | DOI публикации                             |
| `publication-pmid`   | `str` | Нет          | PubMed ID                                  |
| `publication-pmc-id` | `str` | Нет          | PubMed Central ID                          |
| `record-id`          | `int` | Нет          | Внутренний ID записи                       |
| `src-id`             | `int` | Нет          | ID источника данных                        |

#### Данные молекулы

| Поле                        | Тип   | Описание                           |
| --------------------------- | ----- | ---------------------------------- |
| `canonical-smiles`          | `str` | SMILES-формула молекулы            |
| `molecule-pref-name`        | `str` | Предпочтительное название молекулы |
| `parent-molecule-id`        | `str` | ID родительской молекулы           |

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
| `standard-type`        | `str`   | Тип: IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd и др. |
| `standard-value`       | `float` | Стандартизированное значение                                         |
| `standard-units`       | `str`   | Единицы: nM, uM, и др.                                               |
| `standard-relation`    | `str`   | Отношение                                                            |
| `standard-upper-value` | `float` | Верхняя граница                                                      |
| `standard-text-value`  | `str`   | Текстовое стандартизированное значение                               |
| `standard-flag`        | `int`   | Флаг стандартизации                                                  |

#### Вычисляемые метрики

| Поле            | Тип     | Описание                       |
| --------------- | ------- | ------------------------------ |
| `pchembl-value` | `float` | pChEMBL = -log10(IC50 в молях) |

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
| `publication-year` | `int` | Год публикации                        |

#### Метаданные качества

|Поле|Тип|Описание|
|---|---|---|
|`activity-comment`|`str`|Комментарий к активности|
|`data-validity-comment`|`str`|Комментарий о валидности|
|`data-validity-description`|`str`|Описание проблемы с данными|
|`potential-duplicate`|`int`|Флаг потенциального дубликата|
|`manual-curation-flag`|`int`|Флаг ручной кураторской проверки (0/1)|
|`original-activity-id`|`int`|ID исходной записи активности (traceability)|

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
| `entity-id`        | `str` | `chembl:{activity-id}`               |
| `content-hash`     | `str` | SHA256-хеш содержимого               |
| `-run-id`          | `str` | UUID запуска пайплайна               |
| `-run-type`        | `str` | `incremental`, `backfill`, `rebuild` |
| `-source-batch-id` | `str` | UUID батча                           |
| `-ingestion-ts`    | `str` | Timestamp загрузки (ISO8601)         |

----------------------------------------------------------------------

### 3.2. Валидация при создании сущности

```python
def -validate-invariants(self) -> None:
    if not self.activity-id:
        raise ValueError("Activity ID is required")
    if not self.molecule-id:
        raise ValueError("Molecule ID is required")
    if self.pchembl-value is not None and self.pchembl-value < 0:
        raise ValueError("pChemBL value must be non-negative")
```

----------------------------------------------------------------------

## 4. Нормализация данных

**Файл:** `src/bioetl/application/pipelines/chembl/activity-transformer.py`

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
entity-id = f"chembl:{activity-id}"

# Content Hash: SHA256 для версионирования
content-hash = sha256("chembl" + canonical-json(business-fields))
```

### 4.4. Поля, исключённые из хеша

```python
META-FIELDS = {
    "-ingestion-ts",
    "-run-id",
    "-run-type",
    "-dq-warn",
    "-dq-error",
    "-source-batch-id",
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

1. **`standard-value` > 0** — не null, не отрицательный
1. **`standard-type`** ∈ {IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, Kd, ...}
1. **`molecule-id`** соответствует regex `^CHEMBL\d+$`

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
    "error-code": "INVALID-STANDARD-VALUE",
    "error-details": "standard-value is negative",
    "batch-id": "uuid",
    "timestamp": "2025-12-19T10:30:00Z",
}
```

----------------------------------------------------------------------

## 6. Запись в слои Medallion

### 6.1. Bronze Layer

**Файл:** `src/bioetl/infrastructure/storage/bronze-writer.py`

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
    "run-id": "uuid",
    "run-type": "incremental",
    "ingestion-ts": "2025-12-19T10:30:00Z",
    "provider": "chembl",
    "entity": "activity",
    "batch-id": "uuid"
}
```

----------------------------------------------------------------------

### 6.2. Silver Layer

**Файл:** `src/bioetl/infrastructure/storage/delta-writer.py`

**PyArrow Schema** (`src/bioetl/infrastructure/schemas/silver.py`):

```python
CHEMBL-ACTIVITY-SCHEMA = pa.schema(
    [
        pa.field("entity-id", pa.string()),
        pa.field("content-hash", pa.string()),
        pa.field("activity-id", pa.string()),
        pa.field("molecule-id", pa.string()),
        pa.field("target-id", pa.string()),
        pa.field("assay-id", pa.string()),
        pa.field("publication-id", pa.string()),
        pa.field("publication-doi", pa.string()),
        pa.field("publication-pmid", pa.string()),
        pa.field("publication-pmc-id", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("publication-year", pa.int64()),
        pa.field("standard-type", pa.string()),
        pa.field("standard-value", pa.float64()),
        pa.field("standard-units", pa.string()),
        pa.field("pchembl-value", pa.float64()),
        pa.field("-run-id", pa.string()),
        pa.field("-run-type", pa.string()),
        pa.field("-ingestion-ts", pa.string()),
        # ... всего 62 поля (включая action-type*)
    ]
)
```

| Параметр                 | Значение                         |
| ------------------------ | -------------------------------- |
| **Формат**               | Delta Lake                       |
| **Merge Key**            | `activity-id`                    |
| **Партиционирование**    | `year`, `month`                  |
| **Приоритет конфликтов** | REBUILD > BACKFILL > INCREMENTAL |

----------------------------------------------------------------------

### 6.3. Gold Layer

**Файл:** `src/bioetl/infrastructure/storage/gold-writer.py`

#### Фильтр для Gold

```python
def should-include(self, context, record) -> bool:
    return all(
        [
            record.get("standard-value") is not None,  # Есть значение
            record.get("standard-units"),  # Есть единицы
            record.get("target-id"),  # Есть мишень
            record.get("standard-type") in {"IC50", "Ki", "Kd", "EC50", "AC50", "GI50", "ED50", "MIC", "CC50"},  # 9 типов
            not record.get("data-validity-comment"),  # Нет флагов проблем
        ]
    )
```

| Параметр      | Значение              |
| ------------- | --------------------- |
| **Формат**    | Delta Lake            |
| **Режим**     | Overwrite             |
| **Валидация** | Strict Pandera schema |

#### Data Contract

**Файл:** `docs/04-reference/contracts/gold/chembl_activity_v1.0.json`

```json
{
    "required": [
        "activity-id",
        "molecule-id",
        "-content-hash",
        "-ingestion-ts"
    ],
    "properties": {
        "activity-id": {"type": "integer"},
        "molecule-id": {"type": "string", "pattern": "^CHEMBL\\d+$"},
        "standard-type": {"type": "string"},
        "standard-value": {"type": ["number", "null"]},
        "pchembl-value": {"type": ["number", "null"]}
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
│  • Merge by: activity-id                │
│  • Schema: 62 поля (PyArrow)            │
│  • Партиции: year/month                 │
└─────────────────────────────────────────┘
         │
         ▼ ActivityGoldFilter.should-include()
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

## 9. Watermark (инкрементальная загрузка)

**Файл:** `src/bioetl/application/pipelines/chembl/activity-watermark.py`

Для инкрементальных запусков используется `activity-id` как watermark:

```python
def extract(self, context, record) -> Watermark:
    activity-id = record.get("activity-id")
    if activity-id is not None:
        return Watermark.from-id(str(activity-id))
    return Watermark.from-id("")
```

----------------------------------------------------------------------

## 10. Связанные файлы

| Компонент     | Путь                                                              |
| ------------- | ----------------------------------------------------------------- |
| Конфигурация  | `configs/pipelines/chembl/activity.yaml`                          |
| Сущность      | `src/bioetl/domain/entities/bioactivity.py`                       |
| Трансформер   | `src/bioetl/application/pipelines/chembl/activity-transformer.py` |
| Gold-фильтр   | `src/bioetl/application/pipelines/chembl/activity-gold-filter.py` |
| Watermark     | `src/bioetl/application/pipelines/chembl/activity-watermark.py`   |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py`                     |
| Bronze Writer | `src/bioetl/infrastructure/storage/bronze-writer.py`              |
| Delta Writer  | `src/bioetl/infrastructure/storage/delta-writer.py`               |
| Gold Writer   | `src/bioetl/infrastructure/storage/gold-writer.py`                |
| Data Contract | `docs/04-reference/contracts/gold/chembl_activity_v1.0.json`                               |

----------------------------------------------------------------------

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

----------------------------------------------------------------------

*Последнее обновление: 2025-12-24*
