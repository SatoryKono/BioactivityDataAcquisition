# Gold Layer Data Contracts

Контракты данных для Gold-слоя BioETL.

> **Версия**: 1.1.0
> **Последнее обновление**: 2026-02-04
> **Связанные ADR**: [ADR-018](../02-architecture/decisions/ADR-018-gold-strict-validation.md), [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md)

______________________________________________________________________

## Содержание

1. [Обзор](#%D0%BE%D0%B1%D0%B7%D0%BE%D1%80)
1. [Архитектура Gold-слоя](#%D0%B0%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%82%D1%83%D1%80%D0%B0-gold-%D1%81%D0%BB%D0%BE%D1%8F)
1. [Фильтрация Silver → Gold](#%D1%84%D0%B8%D0%BB%D1%8C%D1%82%D1%80%D0%B0%D1%86%D0%B8%D1%8F-silver--gold)
1. [Контракты по провайдерам](#%D0%BA%D0%BE%D0%BD%D1%82%D1%80%D0%B0%D0%BA%D1%82%D1%8B-%D0%BF%D0%BE-%D0%BF%D1%80%D0%BE%D0%B2%D0%B0%D0%B9%D0%B4%D0%B5%D1%80%D0%B0%D0%BC)
   - [ChEMBL](#chembl)
   - [PubChem](#pubchem)
   - [UniProt](#uniprot)
   - [PubMed](#pubmed)
1. [Системные поля](#%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%BD%D1%8B%D0%B5-%D0%BF%D0%BE%D0%BB%D1%8F)
1. [Режимы записи](#%D1%80%D0%B5%D0%B6%D0%B8%D0%BC%D1%8B-%D0%B7%D0%B0%D0%BF%D0%B8%D1%81%D0%B8)
1. [Примеры запросов](#%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80%D1%8B-%D0%B7%D0%B0%D0%BF%D1%80%D0%BE%D1%81%D0%BE%D0%B2)
1. [Валидация](#%D0%B2%D0%B0%D0%BB%D0%B8%D0%B4%D0%B0%D1%86%D0%B8%D1%8F)

______________________________________________________________________

## Обзор

Gold-слой содержит **бизнес-готовые данные** с:

- Строгой валидацией через Pandera (`strict=True`)
- Фильтрацией по бизнес-правилам (качество, релевантность)
- Детерминистичной записью (сортировка по primary key)
- ACID-транзакциями через Delta Lake

### Принципы Gold-слоя

| Принцип               | Описание                                           |
| --------------------- | -------------------------------------------------- |
| **Strict Validation** | Все поля валидируются перед записью (REQ-DATA-009) |
| **Business Filters**  | Только качественные данные проходят в Gold         |
| **Idempotency**       | Повторный запуск даёт идентичный результат         |
| **Traceability**      | Каждая запись содержит `_run_id`, `content_hash`   |

______________________________________________________________________

## Архитектура Gold-слоя

```
Silver Layer                     Gold Layer
┌─────────────────┐             ┌─────────────────┐
│  All Records    │             │ Filtered        │
│  (validated)    │──────────►  │ (business-ready)│
│                 │  Filters    │                 │
│  ~100% данных   │             │  ~20-60% данных │
└─────────────────┘             └─────────────────┘
        │                               │
        ▼                               ▼
   Delta Lake                      Delta Lake
   (forensic)                      (analytics)
```

### Путь данных

1. **Silver Record** → Все провалидированные записи из Bronze
1. **Gold Filters** → Применение бизнес-фильтров из YAML-конфига
1. **Schema Validation** → Проверка Pandera-схемой (`strict=True`)
1. **Deterministic Write** → Сортировка по PK, запись в Delta Lake

______________________________________________________________________

## Фильтрация Silver → Gold

Gold-фильтры определяются в YAML-конфигах пайплайнов.

### Типы фильтров

| Тип фильтра            | Описание              | Пример                                   |
| ---------------------- | --------------------- | ---------------------------------------- |
| **columns**            | Inclusion list (IN)   | `standard_type: [IC50, Ki]`              |
| **ranges**             | Числовой диапазон     | `standard_value: {min: 0}`               |
| **list_lengths**       | Длина списка          | `component_accessions: {min: 1, max: 1}` |
| **list_contains**      | Содержимое списка     | `component_types: {values: [PROTEIN]}`   |
| **required_fields**    | Обязательные поля     | `[target_chembl_id, standard_value]`     |
| **exclude_if_present** | Исключение по наличию | `[deprecated_field]`                     |

### Пример конфигурации

```yaml
# configs/pipelines/chembl/activity.yaml
gold_filters:
  columns:
    standard_type: [IC50, Ki]
    standard_units: [nM]
    assay_type: [B, F]
  ranges:
    standard_value:
      min: 0
      include_min: false
  required_fields:
    - standard_type
    - standard_value
    - target_chembl_id
```

______________________________________________________________________

## Контракты по провайдерам

### ChEMBL

#### chembl_activity

**Primary Key**: `activity_id`
**Назначение**: Биоактивность соединений (IC50, Ki, EC50)

##### Gold-фильтры (Бизнес-логика)

| Фильтр                | Значения     | Обоснование                                   |
| --------------------- | ------------ | --------------------------------------------- |
| `standard_type`       | `[IC50, Ki]` | Только стандартизированные метрики связывания |
| `standard_units`      | `[nM]`       | Единый масштаб для сравнения                  |
| `standard_relation`   | `["="]`      | Точные значения, не диапазоны                 |
| `assay_type`          | `[B, F]`     | Binding/Functional assays                     |
| `potential_duplicate` | `["0"]`      | Исключение дубликатов                         |
| `standard_value`      | `> 0`        | Положительные значения активности             |

##### Ключевые поля

| Поле                 | Тип   | Nullable | Описание                 |
| -------------------- | ----- | -------- | ------------------------ |
| `entity_id`          | str   | No       | Уникальный идентификатор |
| `activity_id`        | str   | No       | ChEMBL Activity ID       |
| `molecule_chembl_id` | str   | No       | ID молекулы              |
| `target_chembl_id`   | str   | Yes      | ID мишени                |
| `assay_chembl_id`    | str   | Yes      | ID эксперимента          |
| `standard_type`      | str   | Yes      | Тип метрики (IC50, Ki)   |
| `standard_value`     | float | Yes      | Значение активности      |
| `standard_units`     | str   | Yes      | Единицы измерения        |
| `pchembl_value`      | float | Yes      | -log10(IC50)             |
| `canonical_smiles`   | str   | Yes      | SMILES молекулы          |
| `content_hash`       | str   | No       | SHA256 хэш записи        |

##### Лиганд-эффективность

| Поле                    | Описание                     |
| ----------------------- | ---------------------------- |
| `ligand_efficiency_bei` | Binding Efficiency Index     |
| `ligand_efficiency_le`  | Ligand Efficiency            |
| `ligand_efficiency_lle` | Lipophilic Ligand Efficiency |
| `ligand_efficiency_sei` | Surface Efficiency Index     |

______________________________________________________________________

#### chembl_molecule

**Primary Key**: `molecule_chembl_id`
**Назначение**: Химические соединения и их свойства

##### Gold-фильтры

| Фильтр           | Значения           | Обоснование                  |
| ---------------- | ------------------ | ---------------------------- |
| `molecule_type`  | `[Small molecule]` | Drug-like молекулы           |
| `structure_type` | `[MOL]`            | Структурированные соединения |
| `inorganic_flag` | `["0"]`            | Только органические          |

##### Ключевые поля

| Поле                           | Тип   | Nullable | Описание                         |
| ------------------------------ | ----- | -------- | -------------------------------- |
| `molecule_chembl_id`           | str   | No       | ChEMBL Molecule ID               |
| `pref_name`                    | str   | Yes      | Предпочтительное название        |
| `molecule_type`                | str   | Yes      | Тип молекулы                     |
| `max_phase`                    | float | Yes      | Фаза клинических испытаний (0-4) |
| `structure_canonical_smiles`   | str   | Yes      | Каноническая SMILES              |
| `structure_standard_inchi`     | str   | Yes      | InChI                            |
| `structure_standard_inchi_key` | str   | Yes      | InChIKey                         |

##### Физико-химические свойства

| Поле                      | Описание                   |
| ------------------------- | -------------------------- |
| `property_alogp`          | Расчётный logP             |
| `property_mw_freebase`    | Молекулярная масса         |
| `property_hba`            | Hydrogen Bond Acceptors    |
| `property_hbd`            | Hydrogen Bond Donors       |
| `property_psa`            | Polar Surface Area         |
| `property_rtb`            | Rotatable Bonds            |
| `property_ro5_violations` | Нарушения правила Lipinski |

______________________________________________________________________

#### chembl_assay

**Primary Key**: `assay_chembl_id`
**Назначение**: Биологические эксперименты

##### Gold-фильтры

| Фильтр              | Значения     | Обоснование                     |
| ------------------- | ------------ | ------------------------------- |
| `assay_type`        | `[B, F]`     | Binding, Functional             |
| `confidence_score`  | `["8", "9"]` | Высокая уверенность (шкала 0-9) |
| `relationship_type` | `[D]`        | Direct interaction only         |

##### Ключевые поля

| Поле               | Тип   | Nullable | Описание            |
| ------------------ | ----- | -------- | ------------------- |
| `assay_chembl_id`  | str   | No       | ChEMBL Assay ID     |
| `target_chembl_id` | str   | Yes      | ID мишени           |
| `assay_type`       | str   | Yes      | Тип эксперимента    |
| `description`      | str   | Yes      | Описание            |
| `confidence_score` | float | Yes      | Уровень уверенности |
| `bao_format`       | str   | Yes      | BAO Format ID       |
| `assay_organism`   | str   | Yes      | Организм            |

______________________________________________________________________

#### chembl_target

**Primary Key**: `target_chembl_id`
**Назначение**: Биологические мишени (белки)

##### Gold-фильтры

| Фильтр                 | Значения              | Обоснование            |
| ---------------------- | --------------------- | ---------------------- |
| `target_type`          | `[SINGLE PROTEIN]`    | Единичные белки        |
| `component_accessions` | length: 1             | Один UniProt accession |
| `component_types`      | contains: `[PROTEIN]` | Тип компонента — белок |

##### Ключевые поля

| Поле                   | Тип       | Nullable | Описание           |
| ---------------------- | --------- | -------- | ------------------ |
| `target_chembl_id`     | str       | No       | ChEMBL Target ID   |
| `pref_name`            | str       | Yes      | Название           |
| `target_type`          | str       | Yes      | Тип мишени         |
| `organism`             | str       | Yes      | Организм           |
| `tax_id`               | float     | Yes      | NCBI Taxonomy ID   |
| `component_accessions` | list[str] | Yes      | UniProt accessions |

______________________________________________________________________

#### chembl_target_component

**Primary Key**: `component_id`
**Назначение**: Компоненты мишеней (белковые последовательности)

##### Gold-фильтры

| Фильтр           | Значения    | Обоснование               |
| ---------------- | ----------- | ------------------------- |
| `component_type` | `[PROTEIN]` | Только белки              |
| required         | `accession` | Наличие UniProt accession |

##### Ключевые поля

| Поле                      | Тип   | Nullable | Описание           |
| ------------------------- | ----- | -------- | ------------------ |
| `component_id`            | float | No       | Component ID       |
| `accession`               | str   | Yes      | UniProt accession  |
| `component_type`          | str   | Yes      | Тип компонента     |
| `organism`                | str   | Yes      | Организм           |
| `protein_classifications` | str   | Yes      | JSON классификации |

______________________________________________________________________

#### chembl_publication

**Primary Key**: `document_chembl_id`
**Назначение**: Научные публикации из ChEMBL API (silver_table/gold_table: `chembl_publication`)

##### Gold-фильтры

| Фильтр     | Значения                              | Обоснование                                            |
| ---------- | ------------------------------------- | ------------------------------------------------------ |
| `doc_type` | `[PUBLICATION]`                       | Только публикации                                      |
| `year`     | `> 1950`                              | Современные публикации                                 |
| required   | `document_chembl_id, doc_type, title` | Базовые метаданные (PubMed ID/DOI могут отсутствовать) |

##### Ключевые поля

| Поле                 | Тип   | Nullable | Описание           |
| -------------------- | ----- | -------- | ------------------ |
| `document_chembl_id` | str   | No       | ChEMBL Document ID |
| `pubmed_id`          | float | Yes      | PubMed ID          |
| `doi`                | str   | Yes      | DOI                |
| `title`              | str   | Yes      | Заголовок          |
| `journal`            | str   | Yes      | Журнал             |
| `year`               | float | Yes      | Год публикации     |
| `authors`            | str   | Yes      | Авторы             |

______________________________________________________________________

#### chembl_compound_record

**Primary Key**: `record_id`
**Назначение**: Связь молекула-документ

##### Gold-фильтры

| Фильтр   | Значения                                 | Обоснование    |
| -------- | ---------------------------------------- | -------------- |
| required | `molecule_chembl_id, document_chembl_id` | Полнота связей |

##### Ключевые поля

| Поле                 | Тип   | Nullable | Описание              |
| -------------------- | ----- | -------- | --------------------- |
| `record_id`          | float | No       | Record ID             |
| `molecule_chembl_id` | str   | No       | ChEMBL Molecule ID    |
| `document_chembl_id` | str   | No       | ChEMBL Document ID    |
| `compound_key`       | str   | Yes      | Название в публикации |
| `compound_name`      | str   | Yes      | Полное название       |

______________________________________________________________________

#### chembl_cell_line

**Primary Key**: `cell_chembl_id`
**Назначение**: Клеточные линии

##### Gold-фильтры

| Фильтр   | Значения    | Обоснование      |
| -------- | ----------- | ---------------- |
| required | `cell_name` | Наличие названия |

##### Ключевые поля

| Поле                   | Тип | Nullable | Описание            |
| ---------------------- | --- | -------- | ------------------- |
| `cell_chembl_id`       | str | No       | ChEMBL Cell Line ID |
| `cell_name`            | str | No       | Название            |
| `cell_description`     | str | Yes      | Описание            |
| `cell_source_tissue`   | str | Yes      | Ткань-источник      |
| `cell_source_organism` | str | Yes      | Организм            |
| `cellosaurus_id`       | str | Yes      | Cellosaurus ID      |

______________________________________________________________________

### PubChem

#### pubchem_compound

**Primary Key**: `cid`
**Назначение**: Химические соединения PubChem

##### Gold-фильтры

| Фильтр   | Значения                 | Обоснование        |
| -------- | ------------------------ | ------------------ |
| required | `cid, molecular_formula` | Минимальные данные |

##### Ключевые поля

| Поле                | Тип | Nullable | Описание             |
| ------------------- | --- | -------- | -------------------- |
| `entity_id`         | str | No       | Уникальный ID        |
| `cid`               | str | No       | PubChem Compound ID  |
| `molecular_formula` | str | Yes      | Молекулярная формула |
| `molecular_weight`  | str | Yes      | Молекулярная масса   |
| `canonical_smiles`  | str | Yes      | Каноническая SMILES  |
| `isomeric_smiles`   | str | Yes      | Изомерная SMILES     |
| `inchi`             | str | Yes      | InChI                |
| `inchikey`          | str | Yes      | InChIKey             |
| `iupac_name`        | str | Yes      | IUPAC название       |

______________________________________________________________________

### UniProt

#### uniprot_protein

**Primary Key**: `accession`
**Назначение**: Белки UniProt

##### Gold-фильтры

| Фильтр     | Значения                          | Обоснование                  |
| ---------- | --------------------------------- | ---------------------------- |
| `reviewed` | `["true"]`                        | Только Swiss-Prot (reviewed) |
| required   | `accession, entry_name, organism` | Полнота данных               |

##### Ключевые поля

| Поле              | Тип       | Nullable | Описание                 |
| ----------------- | --------- | -------- | ------------------------ |
| `entity_id`       | str       | No       | Уникальный ID            |
| `accession`       | str       | No       | UniProt Accession        |
| `entry_name`      | str       | Yes      | Entry name               |
| `protein_name`    | str       | Yes      | Название белка           |
| `gene_names`      | list[str] | Yes      | Названия генов           |
| `organism_id`     | float     | Yes      | NCBI Taxonomy ID         |
| `sequence_length` | float     | Yes      | Длина последовательности |

______________________________________________________________________

### PubMed

#### pubmed_publication

**Primary Key**: `pmid`
**Назначение**: Публикации PubMed

##### Gold-фильтры

| Фильтр   | Значения      | Обоснование            |
| -------- | ------------- | ---------------------- |
| required | `pmid, title` | Минимальные метаданные |

##### Ключевые поля

| Поле         | Тип       | Nullable | Описание          |
| ------------ | --------- | -------- | ----------------- |
| `entity_id`  | str       | No       | Уникальный ID     |
| `pmid`       | str       | No       | PubMed ID         |
| `doi`        | str       | Yes      | DOI               |
| `pmc_id`     | str       | Yes      | PubMed Central ID |
| `title`      | str       | Yes      | Заголовок         |
| `abstract`   | str       | Yes      | Абстракт          |
| `journal`    | str       | Yes      | Журнал            |
| `authors`    | list[str] | Yes      | Авторы            |
| `pub_year`   | float     | Yes      | Год публикации    |
| `mesh_terms` | list[str] | Yes      | MeSH термины      |
| `keywords`   | list[str] | Yes      | Ключевые слова    |

______________________________________________________________________

## Системные поля

Все Gold-таблицы содержат следующие метаданные:

| Поле               | Alias           | Тип | Nullable | Описание                           |
| ------------------ | --------------- | --- | -------- | ---------------------------------- |
| `entity_id`        | —               | str | No       | Глобальный уникальный ID           |
| `content_hash`     | —               | str | No       | SHA256 хэш содержимого             |
| `_run_id`          | run_id          | str | No       | ID запуска пайплайна               |
| `_run_type`        | run_type        | str | No       | Тип запуска (incremental/backfill) |
| `_source_batch_id` | source_batch_id | str | Yes      | ID исходного batch                 |
| `_ingestion_ts`    | ingestion_ts    | str | No       | Timestamp загрузки (ISO 8601)      |
| `_index`           | index           | int | No       | Порядковый номер в batch           |

### Content Hash

Формула вычисления:

```python
sha256(provider + canonical_json(record))
```

**Нормализация перед хэшированием:**

- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → ISO `YYYY-MM-DD`
- Strings → `strip()`
- **Исключаются**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`

______________________________________________________________________

## Режимы записи

| Режим         | Enum                      | Поведение                         | Идемпотентность          |
| ------------- | ------------------------- | --------------------------------- | ------------------------ |
| **OVERWRITE** | `GoldWriteMode.OVERWRITE` | Полная замена таблицы             | Да                       |
| **APPEND**    | `GoldWriteMode.APPEND`    | Добавление записей                | Нет (возможны дубликаты) |
| **SCD2**      | `GoldWriteMode.SCD2`      | Slowly Changing Dimensions Type 2 | Да (upsert)              |

### SCD2 конфигурация

При использовании SCD2 добавляются поля:

| Поле         | Тип      | Описание                   |
| ------------ | -------- | -------------------------- |
| `valid_from` | datetime | Начало действия версии     |
| `valid_to`   | datetime | Окончание (NULL = текущая) |
| `is_current` | bool     | Текущая версия             |
| `version`    | int      | Номер версии               |

______________________________________________________________________

## Примеры запросов

### Polars

```python
import polars as pl
from deltalake import DeltaTable

# Загрузка Gold-таблицы
dt = DeltaTable("data/output/gold/chembl_activity")
df = pl.from_arrow(dt.to_pyarrow_table())

# Фильтрация активных IC50 для конкретной мишени
activities = df.filter(
    (pl.col("target_chembl_id") == "CHEMBL1234")
    & (pl.col("standard_type") == "IC50")
    & (pl.col("standard_value") < 100)  # nM
).select(["molecule_chembl_id", "standard_value", "pchembl_value", "canonical_smiles"])
```

### SQL (DuckDB)

```sql
-- Подключение к Delta Lake
INSTALL delta;
LOAD delta;

-- Топ-10 молекул по активности для мишени
SELECT
    molecule_chembl_id,
    standard_value,
    pchembl_value,
    canonical_smiles
FROM delta_scan('data/output/gold/chembl_activity')
WHERE target_chembl_id = 'CHEMBL1234'
  AND standard_type = 'IC50'
ORDER BY standard_value ASC
LIMIT 10;
```

### Связывание таблиц

```sql
-- Молекулы с активностью и свойствами
SELECT
    a.molecule_chembl_id,
    a.target_chembl_id,
    a.standard_value AS ic50_nm,
    m.property_alogp,
    m.property_mw_freebase AS mw,
    m.structure_canonical_smiles
FROM delta_scan('data/output/gold/chembl_activity') a
JOIN delta_scan('data/output/gold/chembl_molecule') m
  ON a.molecule_chembl_id = m.molecule_chembl_id
WHERE a.standard_type = 'IC50'
  AND a.standard_value < 100;
```

### Анализ по мишеням

```sql
-- Статистика активности по мишеням
SELECT
    t.pref_name AS target_name,
    t.organism,
    COUNT(*) AS activity_count,
    AVG(a.pchembl_value) AS avg_pchembl,
    MIN(a.standard_value) AS best_ic50_nm
FROM delta_scan('data/output/gold/chembl_activity') a
JOIN delta_scan('data/output/gold/chembl_target') t
  ON a.target_chembl_id = t.target_chembl_id
WHERE a.standard_type = 'IC50'
GROUP BY t.pref_name, t.organism
ORDER BY activity_count DESC
LIMIT 20;
```

### Time-travel запросы (Delta Lake)

```python
from deltalake import DeltaTable

# Версия на определённый timestamp
dt = DeltaTable("data/output/gold/chembl_activity")
df_historical = pl.from_arrow(
    dt.load_as_version(datetime(2025, 1, 1)).to_pyarrow_table()
)

# Сравнение версий
current_count = dt.to_pyarrow_table().num_rows
previous = dt.load_as_version(dt.version() - 1)
previous_count = previous.to_pyarrow_table().num_rows
print(f"Added {current_count - previous_count} records")
```

______________________________________________________________________

## Валидация

### Pandera Schema

Все Gold-схемы определены в `src/bioetl/domain/contracts/gold/`.

```python
class ChEMBLActivityGoldSchema(pa.DataFrameModel):
    entity_id: Series[str] = pa.Field(nullable=False)
    activity_id: Series[str] = pa.Field(nullable=False)
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    # ... остальные поля

    class Config:
        strict = True  # REQ-DATA-009
```

### Проверка контракта

```python
from bioetl.infrastructure.schemas.gold import ChEMBLActivityGoldSchema
import polars as pl

# Загрузка и валидация
df = pl.read_delta("data/output/gold/chembl_activity")
validated = ChEMBLActivityGoldSchema.validate(df.to_pandas())
```

### Data Quality пороги

| Порог    | Значение       | Действие        |
| -------- | -------------- | --------------- |
| **Soft** | >5% DQ errors  | Warning в логах |
| **Hard** | >20% DQ errors | Fail batch      |

______________________________________________________________________

## Gold Schema Implementation

Gold-схемы реализованы как **Python Pandera DataFrameModel** классы в `src/bioetl/domain/contracts/gold/`.

Каждая Gold-схема определяет:

- Строгую валидацию типов (`strict=True`)
- Nullable/non-nullable поля
- Coercion rules (например, `int→float` для nullable integers)

### JSON Contract Exports

JSON exports для Gold-схем хранятся в `docs/04-reference/contracts/gold/`:

- `chembl_activity_v1.0.json`
- `chembl_assay_parameters_v1.0.json`
- `chembl_assay_v1.0.json`
- `chembl_cell_line_v1.0.json`
- `chembl_compound_record_v1.0.json`
- `chembl_document_similarity_v1.0.json`
- `chembl_document_term_v1.0.json`
- `chembl_document_v1.0.json`
- `chembl_molecule_v1.0.json`
- `chembl_protein_class_v1.0.json`
- `chembl_subcellular_fraction_v1.0.json`
- `chembl_target_component_v1.0.json`
- `chembl_target_v1.0.json`
- `chembl_tissue_v1.0.json`
- `composite_publication_v1.0.json`
- `crossref_publication_v1.0.json`
- `openalex_publication_v1.0.json`
- `pubchem_compound_v1.0.json`
- `pubmed_publication_v1.0.json`
- `semanticscholar_publication_v1.0.json`
- `uniprot_idmapping_v1.0.json`

## Связанные документы

- [ADR-018: Gold Strict Validation](../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-002: Medallion Architecture](../02-architecture/decisions/ADR-002-medallion-architecture.md)
- [Data Layers](../02-architecture/data-layers.md)
- [JSON Contract Exports](gold/)

______________________________________________________________________

## Сводная таблица контрактов

| Provider | Entity           | Primary Key          | Filters              | Fields |
| -------- | ---------------- | -------------------- | -------------------- | ------ |
| ChEMBL   | activity         | `activity_id`        | 5 column + 1 range   | ~100   |
| ChEMBL   | molecule         | `molecule_chembl_id` | 3 column             | ~60    |
| ChEMBL   | assay            | `assay_chembl_id`    | 3 column             | ~45    |
| ChEMBL   | target           | `target_chembl_id`   | 1 col + list filters | ~25    |
| ChEMBL   | target_component | `component_id`       | 1 column             | ~13    |
| ChEMBL   | document         | `document_chembl_id` | 1 col + 1 range      | ~17    |
| ChEMBL   | compound_record  | `record_id`          | required only        | ~8     |
| ChEMBL   | cell_line        | `cell_chembl_id`     | required only        | ~12    |
| PubChem  | compound         | `cid`                | required only        | ~10    |
| UniProt  | protein          | `accession`          | 1 column             | ~8     |
| PubMed   | publication      | `pmid`               | required only        | ~24    |
