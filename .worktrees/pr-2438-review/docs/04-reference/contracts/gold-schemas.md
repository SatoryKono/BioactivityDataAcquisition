# Gold Layer Data Contracts

Контракты данных для Gold-слоя BioETL.

> **Версия**: 1.1.0
> **Последнее обновление**: 2026-02-04
> **Связанные ADR**: [ADR-018](../../02-architecture/decisions/ADR-018-gold-strict-validation.md), [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md)

---

## Содержание

1. [Обзор](#обзор)
2. [Архитектура Gold-слоя](#архитектура-gold-слоя)
3. [Фильтрация Silver → Gold](#фильтрация-silver--gold)
4. [Контракты по провайдерам](#контракты-по-провайдерам)
   - [ChEMBL](#chembl)
   - [PubChem](#pubchem)
   - [UniProt](#uniprot)
   - [PubMed](#pubmed)
5. [Системные поля](#системные-поля)
6. [Режимы записи](#режимы-записи)
7. [Примеры запросов](#примеры-запросов)
8. [Валидация](#валидация)

---

## Обзор

Gold-слой содержит **бизнес-готовые данные** с:
- Строгой валидацией через Pandera (`strict=True`)
- Фильтрацией по бизнес-правилам (качество, релевантность)
- Детерминистичной записью (сортировка по primary key)
- ACID-транзакциями через Delta Lake

### Принципы Gold-слоя

| Принцип | Описание |
|---------|----------|
| **Strict Validation** | Все поля валидируются перед записью (REQ-DATA-009) |
| **Business Filters** | Только качественные данные проходят в Gold |
| **Idempotency** | Повторный запуск даёт идентичный результат |
| **Traceability** | Каждая запись содержит `-run-id`, `content-hash` |

---

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
2. **Gold Filters** → Применение бизнес-фильтров из YAML-конфига
3. **Schema Validation** → Проверка Pandera-схемой (`strict=True`)
4. **Deterministic Write** → Сортировка по PK, запись в Delta Lake

---

## Фильтрация Silver → Gold

Gold-фильтры определяются в YAML-конфигах пайплайнов.

### Типы фильтров

| Тип фильтра | Описание | Пример |
|-------------|----------|--------|
| **columns** | Inclusion list (IN) | `standard-type: [IC50, Ki]` |
| **ranges** | Числовой диапазон | `standard-value: {min: 0}` |
| **list-lengths** | Длина списка | `component-accessions: {min: 1, max: 1}` |
| **list-contains** | Содержимое списка | `component-types: {values: [PROTEIN]}` |
| **required-fields** | Обязательные поля | `[target-chembl-id, standard-value]` |
| **exclude-if-present** | Исключение по наличию | `[deprecated-field]` |

### Пример конфигурации

```yaml
# configs/entities/chembl/activity.yaml
gold-filters:
  columns:
    standard-type: [IC50, Ki]
    standard-units: [nM]
    assay-type: [B, F]
  ranges:
    standard-value:
      min: 0
      include-min: false
  required-fields:
    - standard-type
    - standard-value
    - target-chembl-id
```

---

## Контракты по провайдерам

### ChEMBL

#### chembl_activity

**Primary Key**: `activity-id`
**Назначение**: Биоактивность соединений (IC50, Ki, EC50)

##### Gold-фильтры (Бизнес-логика)

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `standard-type` | `[IC50, Ki]` | Только стандартизированные метрики связывания |
| `standard-units` | `[nM]` | Единый масштаб для сравнения |
| `standard-relation` | `["="]` | Точные значения, не диапазоны |
| `assay-type` | `[B, F]` | Binding/Functional assays |
| `potential-duplicate` | `["0"]` | Исключение дубликатов |
| `standard-value` | `> 0` | Положительные значения активности |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity-id` | str | No | Уникальный идентификатор |
| `activity-id` | str | No | ChEMBL Activity ID |
| `molecule-chembl-id` | str | No | ID молекулы |
| `target-chembl-id` | str | Yes | ID мишени |
| `assay-chembl-id` | str | Yes | ID эксперимента |
| `standard-type` | str | Yes | Тип метрики (IC50, Ki) |
| `standard-value` | float | Yes | Значение активности |
| `standard-units` | str | Yes | Единицы измерения |
| `pchembl-value` | float | Yes | -log10(IC50) |
| `canonical-smiles` | str | Yes | SMILES молекулы |
| `content-hash` | str | No | SHA256 хэш записи |

##### Лиганд-эффективность

| Поле | Описание |
|------|----------|
| `ligand-efficiency-bei` | Binding Efficiency Index |
| `ligand-efficiency-le` | Ligand Efficiency |
| `ligand-efficiency-lle` | Lipophilic Ligand Efficiency |
| `ligand-efficiency-sei` | Surface Efficiency Index |

---

#### chembl_molecule

**Primary Key**: `molecule-chembl-id`
**Назначение**: Химические соединения и их свойства

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `molecule-type` | `[Small molecule]` | Drug-like молекулы |
| `structure-type` | `[MOL]` | Структурированные соединения |
| `inorganic-flag` | `["0"]` | Только органические |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `molecule-chembl-id` | str | No | ChEMBL Molecule ID |
| `pref-name` | str | Yes | Предпочтительное название |
| `molecule-type` | str | Yes | Тип молекулы |
| `max-phase` | float | Yes | Фаза клинических испытаний (0-4) |
| `structure-canonical-smiles` | str | Yes | Каноническая SMILES |
| `structure-standard-inchi` | str | Yes | InChI |
| `structure-standard-inchi-key` | str | Yes | InChIKey |

##### Физико-химические свойства

| Поле | Описание |
|------|----------|
| `property-alogp` | Расчётный logP |
| `property-mw-freebase` | Молекулярная масса |
| `property-hba` | Hydrogen Bond Acceptors |
| `property-hbd` | Hydrogen Bond Donors |
| `property-psa` | Polar Surface Area |
| `property-rtb` | Rotatable Bonds |
| `property-ro5-violations` | Нарушения правила Lipinski |

---

#### chembl_assay

**Primary Key**: `assay-chembl-id`
**Назначение**: Биологические эксперименты

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `assay-type` | `[B, F]` | Binding, Functional |
| `confidence-score` | `["8", "9"]` | Высокая уверенность (шкала 0-9) |
| `relationship-type` | `[D]` | Direct interaction only |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `assay-chembl-id` | str | No | ChEMBL Assay ID |
| `target-chembl-id` | str | Yes | ID мишени |
| `assay-type` | str | Yes | Тип эксперимента |
| `description` | str | Yes | Описание |
| `confidence-score` | float | Yes | Уровень уверенности |
| `bao-format` | str | Yes | BAO Format ID |
| `assay-organism` | str | Yes | Организм |

---

#### chembl_target

**Primary Key**: `target-chembl-id`
**Назначение**: Биологические мишени (белки)

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `target-type` | `[SINGLE PROTEIN]` | Единичные белки |
| `component-accessions` | length: 1 | Один UniProt accession |
| `component-types` | contains: `[PROTEIN]` | Тип компонента — белок |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `target-chembl-id` | str | No | ChEMBL Target ID |
| `pref-name` | str | Yes | Название |
| `target-type` | str | Yes | Тип мишени |
| `organism` | str | Yes | Организм |
| `tax-id` | float | Yes | NCBI Taxonomy ID |
| `component-accessions` | list[str] | Yes | UniProt accessions |

---

#### chembl_target_component

**Primary Key**: `component-id`
**Назначение**: Компоненты мишеней (белковые последовательности)

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `component-type` | `[PROTEIN]` | Только белки |
| required | `accession` | Наличие UniProt accession |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `component-id` | float | No | Component ID |
| `accession` | str | Yes | UniProt accession |
| `component-type` | str | Yes | Тип компонента |
| `organism` | str | Yes | Организм |
| `protein-classifications` | str | Yes | JSON классификации |

---

#### chembl_publication

**Primary Key**: `document-chembl-id`
**Назначение**: Научные публикации из ChEMBL API (silver-table/gold-table: `chembl_publication`)

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `doc-type` | `[PUBLICATION]` | Только публикации |
| `year` | `> 1950` | Современные публикации |
| required | `document-chembl-id, doc-type, title` | Базовые метаданные (PubMed ID/DOI могут отсутствовать) |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `document-chembl-id` | str | No | ChEMBL Document ID |
| `pubmed-id` | float | Yes | PubMed ID |
| `doi` | str | Yes | DOI |
| `title` | str | Yes | Заголовок |
| `journal` | str | Yes | Журнал |
| `year` | float | Yes | Год публикации |
| `authors` | str | Yes | Авторы |

---

#### chembl_compound_record

**Primary Key**: `record-id`
**Назначение**: Связь молекула-документ

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| required | `molecule-chembl-id, document-chembl-id` | Полнота связей |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `record-id` | float | No | Record ID |
| `molecule-chembl-id` | str | No | ChEMBL Molecule ID |
| `document-chembl-id` | str | No | ChEMBL Document ID |
| `compound-key` | str | Yes | Название в публикации |
| `compound-name` | str | Yes | Полное название |

---

#### chembl_cell_line

**Primary Key**: `cell-chembl-id`
**Назначение**: Клеточные линии

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| required | `cell-name` | Наличие названия |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `cell-chembl-id` | str | No | ChEMBL Cell Line ID |
| `cell-name` | str | No | Название |
| `cell-description` | str | Yes | Описание |
| `cell-source-tissue` | str | Yes | Ткань-источник |
| `cell-source-organism` | str | Yes | Организм |
| `cellosaurus-id` | str | Yes | Cellosaurus ID |

---

### PubChem

#### pubchem_compound

**Primary Key**: `cid`
**Назначение**: Химические соединения PubChem

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| required | `cid, molecular-formula` | Минимальные данные |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity-id` | str | No | Уникальный ID |
| `cid` | str | No | PubChem Compound ID |
| `molecular-formula` | str | Yes | Молекулярная формула |
| `molecular-weight` | str | Yes | Молекулярная масса |
| `canonical-smiles` | str | Yes | Каноническая SMILES |
| `isomeric-smiles` | str | Yes | Изомерная SMILES |
| `inchi` | str | Yes | InChI |
| `inchikey` | str | Yes | InChIKey |
| `iupac-name` | str | Yes | IUPAC название |

---

### UniProt

#### uniprot_protein

**Primary Key**: `accession`
**Назначение**: Белки UniProt

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| `reviewed` | `["true"]` | Только Swiss-Prot (reviewed) |
| required | `accession, entry-name, organism` | Полнота данных |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity-id` | str | No | Уникальный ID |
| `accession` | str | No | UniProt Accession |
| `entry-name` | str | Yes | Entry name |
| `protein-name` | str | Yes | Название белка |
| `gene-names` | list[str] | Yes | Названия генов |
| `organism-id` | float | Yes | NCBI Taxonomy ID |
| `sequence-length` | float | Yes | Длина последовательности |

---

### PubMed

#### pubmed_publication

**Primary Key**: `pmid`
**Назначение**: Публикации PubMed

##### Gold-фильтры

| Фильтр | Значения | Обоснование |
|--------|----------|-------------|
| required | `pmid, title` | Минимальные метаданные |

##### Ключевые поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `entity-id` | str | No | Уникальный ID |
| `pmid` | str | No | PubMed ID |
| `doi` | str | Yes | DOI |
| `pmc-id` | str | Yes | PubMed Central ID |
| `title` | str | Yes | Заголовок |
| `abstract` | str | Yes | Абстракт |
| `journal` | str | Yes | Журнал |
| `authors` | list[str] | Yes | Авторы |
| `pub-year` | float | Yes | Год публикации |
| `mesh-terms` | list[str] | Yes | MeSH термины |
| `keywords` | list[str] | Yes | Ключевые слова |

---

## Системные поля

Все Gold-таблицы содержат следующие метаданные:

| Поле | Alias | Тип | Nullable | Описание |
|------|-------|-----|----------|----------|
| `entity-id` | — | str | No | Глобальный уникальный ID |
| `content-hash` | — | str | No | SHA256 хэш содержимого |
| `-run-id` | run-id | str | No | ID запуска пайплайна |
| `-run-type` | run-type | str | No | Тип запуска (incremental/backfill) |
| `-source-batch-id` | source-batch-id | str | Yes | ID исходного batch |
| `-ingestion-ts` | ingestion-ts | str | No | Timestamp загрузки (ISO 8601) |
| `-index` | index | int | No | Порядковый номер в batch |

### Content Hash

Формула вычисления:
```python
sha256(provider + canonical-json(record))
```

**Нормализация перед хэшированием:**
- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → ISO `YYYY-MM-DD`
- Strings → `strip()`
- **Исключаются**: `-ingestion-ts`, `-run-id`, `-run-type`, `-dq-*`

---

## Режимы записи

| Режим | Enum | Поведение | Идемпотентность |
|-------|------|-----------|-----------------|
| **OVERWRITE** | `GoldWriteMode.OVERWRITE` | Полная замена таблицы | Да |
| **APPEND** | `GoldWriteMode.APPEND` | Добавление записей | Нет (возможны дубликаты) |
| **SCD2** | `GoldWriteMode.SCD2` | Slowly Changing Dimensions Type 2 | Да (upsert) |

### SCD2 конфигурация

При использовании SCD2 добавляются поля:

| Поле | Тип | Описание |
|------|-----|----------|
| `valid-from` | datetime | Начало действия версии |
| `valid-to` | datetime | Окончание (NULL = текущая) |
| `is-current` | bool | Текущая версия |
| `version` | int | Номер версии |

---

## Примеры запросов

### Polars

```python
import polars as pl
from deltalake import DeltaTable

# Загрузка Gold-таблицы
dt = DeltaTable("data/output/gold/chembl_activity")
df = pl.from-arrow(dt.to-pyarrow-table())

# Фильтрация активных IC50 для конкретной мишени
activities = df.filter(
    (pl.col("target-chembl-id") == "CHEMBL1234") &
    (pl.col("standard-type") == "IC50") &
    (pl.col("standard-value") < 100)  # nM
).select([
    "molecule-chembl-id",
    "standard-value",
    "pchembl-value",
    "canonical-smiles"
])
```

### SQL (DuckDB)

```sql
-- Подключение к Delta Lake
INSTALL delta;
LOAD delta;

-- Топ-10 молекул по активности для мишени
SELECT
    molecule-chembl-id,
    standard-value,
    pchembl-value,
    canonical-smiles
FROM delta-scan('data/output/gold/chembl_activity')
WHERE target-chembl-id = 'CHEMBL1234'
  AND standard-type = 'IC50'
ORDER BY standard-value ASC
LIMIT 10;
```

### Связывание таблиц

```sql
-- Молекулы с активностью и свойствами
SELECT
    a.molecule-chembl-id,
    a.target-chembl-id,
    a.standard-value AS ic50-nm,
    m.property-alogp,
    m.property-mw-freebase AS mw,
    m.structure-canonical-smiles
FROM delta-scan('data/output/gold/chembl_activity') a
JOIN delta-scan('data/output/gold/chembl_molecule') m
  ON a.molecule-chembl-id = m.molecule-chembl-id
WHERE a.standard-type = 'IC50'
  AND a.standard-value < 100;
```

### Анализ по мишеням

```sql
-- Статистика активности по мишеням
SELECT
    t.pref-name AS target-name,
    t.organism,
    COUNT(*) AS activity-count,
    AVG(a.pchembl-value) AS avg-pchembl,
    MIN(a.standard-value) AS best-ic50-nm
FROM delta-scan('data/output/gold/chembl_activity') a
JOIN delta-scan('data/output/gold/chembl_target') t
  ON a.target-chembl-id = t.target-chembl-id
WHERE a.standard-type = 'IC50'
GROUP BY t.pref-name, t.organism
ORDER BY activity-count DESC
LIMIT 20;
```

### Time-travel запросы (Delta Lake)

```python
from deltalake import DeltaTable

# Версия на определённый timestamp
dt = DeltaTable("data/output/gold/chembl_activity")
df-historical = pl.from-arrow(
    dt.load-as-version(datetime(2025, 1, 1)).to-pyarrow-table()
)

# Сравнение версий
current-count = dt.to-pyarrow-table().num-rows
previous = dt.load-as-version(dt.version() - 1)
previous-count = previous.to-pyarrow-table().num-rows
print(f"Added {current-count - previous-count} records")
```

---

## Валидация

### Pandera Schema

Все Gold-схемы определены в `src/bioetl/domain/contracts/gold/`.

```python
class ChEMBLActivityGoldSchema(pa.DataFrameModel):
    entity-id: Series[str] = pa.Field(nullable=False)
    activity-id: Series[str] = pa.Field(nullable=False)
    molecule-chembl-id: Series[str] = pa.Field(nullable=False)
    # ... остальные поля

    class Config:
        strict = True  # REQ-DATA-009
```

### Проверка контракта

```python
from bioetl.infrastructure.schemas.gold import ChEMBLActivityGoldSchema
import polars as pl

# Загрузка и валидация
df = pl.read-delta("data/output/gold/chembl_activity")
validated = ChEMBLActivityGoldSchema.validate(df.to-pandas())
```

### Data Quality пороги

| Порог | Значение | Действие |
|-------|----------|----------|
| **Soft** | >5% DQ errors | Warning в логах |
| **Hard** | >20% DQ errors | Fail batch |

---

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
- `chembl_publication_similarity_v1.0.json`
- `chembl_publication_term_v1.0.json`
- `chembl_publication_v1.0.json`
- `chembl_molecule_v1.0.json`
- `chembl_protein_class_v1.0.json`
- `chembl_target_component_v1.0.json`
- `chembl_target_v1.0.json`
- `composite_publication_v1.0.json`
- `crossref_publication_v1.0.json`
- `openalex_publication_v1.0.json`
- `pubchem_compound_v1.0.json`
- `pubmed_publication_v1.0.json`
- `semanticscholar_publication_v1.0.json`
- `uniprot_idmapping_v1.0.json`

## Связанные документы

- [ADR-018: Gold Strict Validation](../../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-002: Medallion Architecture](../../02-architecture/decisions/ADR-002-medallion-architecture.md)
- [Data Layers](../../02-architecture/data-layers.md)
- `docs/04-reference/contracts/gold/` (JSON contract exports directory)

---

## Сводная таблица контрактов

| Provider | Entity | Primary Key | Filters | Fields |
|----------|--------|-------------|---------|--------|
| ChEMBL | activity | `activity-id` | 5 column + 1 range | ~100 |
| ChEMBL | molecule | `molecule-chembl-id` | 3 column | ~60 |
| ChEMBL | assay | `assay-chembl-id` | 3 column | ~45 |
| ChEMBL | target | `target-chembl-id` | 1 col + list filters | ~25 |
| ChEMBL | target-component | `component-id` | 1 column | ~13 |
| ChEMBL | document | `document-chembl-id` | 1 col + 1 range | ~17 |
| ChEMBL | compound-record | `record-id` | required only | ~8 |
| ChEMBL | cell-line | `cell-chembl-id` | required only | ~12 |
| PubChem | compound | `cid` | required only | ~10 |
| UniProt | protein | `accession` | 1 column | ~8 |
| PubMed | publication | `pmid` | required only | ~24 |
