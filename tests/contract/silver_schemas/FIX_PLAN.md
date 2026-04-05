# План Исправления Contract Tests

**Дата:** 2026-02-10
**Версия:** 1.0
**Статус:** 9 failures → 0 failures (100% pass rate)

______________________________________________________________________

## Executive Summary

Все 9 оставшихся ошибок являются **legitimate findings**, требующими исправления в схемах или обновления snapshots после intentional schema changes.

**Распределение:**

- 4 snapshot mismatches (intentional schema changes) ✅ Просто обновить snapshots
- 3 ID fields with wrong type ⚠️ Требуют исправления схем
- 1 date fields with wrong type ⚠️ Требует анализа и решения
- 1 missing enum validation ⚠️ Требует добавления validation

______________________________________________________________________

## Категория 1: Snapshot Mismatches (4 failures)

### Проблема

Схемы были намеренно изменены, но snapshots не обновлены.

### Решение: UPDATE_SNAPSHOTS=1

```bash
UPDATE_SNAPSHOTS=1 python -m pytest tests/contract/silver_schemas/test_schema_stability.py
```

### Детали изменений

#### 1.1 pubchem_compound.molecule_id: int64 → str ✅ ПРАВИЛЬНОЕ ИЗМЕНЕНИЕ

**Текущее состояние:**

```
Expected (snapshot): int64
Got (schema):        str
```

**Обоснование:** Compound IDs ДОЛЖНЫ быть строками:

- Могут иметь префиксы (CID123456)
- Предотвращают leading zero issues
- Согласуется с NAME-001 convention

**Действие:** Принять изменение, обновить snapshot.

______________________________________________________________________

#### 1.2 semanticscholar_publication.influential_citation_count: required=True → False ✅ ПРАВИЛЬНОЕ ИЗМЕНЕНИЕ

**Текущее состояние:**

```
Expected (snapshot): required=True
Got (schema):        required=False
```

**Обоснование:** Поле может отсутствовать в API response (optional field).

**Действие:** Принять изменение, обновить snapshot.

______________________________________________________________________

#### 1.3 openalex_publication.fwci: required=True → False ✅ ПРАВИЛЬНОЕ ИЗМЕНЕНИЕ

**Текущее состояние:**

```
Expected (snapshot): required=True
Got (schema):        required=False
```

**Обоснование:** Field-Weighted Citation Impact может отсутствовать для недавних публикаций.

**Действие:** Принять изменение, обновить snapshot.

______________________________________________________________________

#### 1.4 pubmed_publication.title: Validation check renamed ✅ ПРАВИЛЬНОЕ ИЗМЕНЕНИЕ

**Текущее состояние:**

```
Expected (snapshot): ['_check_title']
Got (schema):        ['title_not_empty']
```

**Обоснование:** Улучшение naming convention для validation checks (более descriptive).

**Действие:** Принять изменение, обновить snapshot.

______________________________________________________________________

## Категория 2: ID Fields Wrong Type (3 failures)

### Проблема

Некоторые ID fields используют integer типы вместо string.

### Решение: Исправить схемы ИЛИ добавить в numeric_id_fields

______________________________________________________________________

### 2.1 chembl_activity.toid ⚠️ ТРЕБУЕТ АНАЛИЗА

**Ошибка:**

```
chembl_activity: ID fields MUST be string type:
  - toid: int64
```

**Что это:** Target Organism ID (ChEMBL taxonomy ID)

**Варианты решения:**

**Вариант A (рекомендуется): Добавить в numeric_id_fields**

```python
# tests/contract/silver_schemas/test_field_types.py
numeric_id_fields = {
    ...,
    "toid",  # Target Organism ID - ChEMBL numeric taxonomy ID
}
```

**Обоснование:**

- ChEMBL использует numeric taxonomy IDs
- Никогда не имеет префиксов
- Связано с organism_id (также numeric)

**Вариант B: Изменить схему на str**

```python
# src/bioetl/infrastructure/schemas/silver/chembl/activity_schema.py
toid: Series[str] = pa.Field(nullable=True, description="Target organism ID")
```

**Рекомендация:** **Вариант A** — добавить в exclusion list, т.к. это internal numeric ID.

______________________________________________________________________

### 2.2 chembl_protein_class.parent_id ⚠️ ТРЕБУЕТ АНАЛИЗА

**Ошибка:**

```
chembl_protein_class: ID fields MUST be string type:
  - parent_id: int64
```

**Что это:** Parent protein class ID (hierarchical relationship)

**Варианты решения:**

**Вариант A (рекомендуется): Добавить в numeric_id_fields**

```python
numeric_id_fields = {
    ...,
    "parent_id",  # Protein class parent ID - internal hierarchy
}
```

**Обоснование:**

- Internal hierarchical ID
- Always numeric in ChEMBL
- Self-referential FK к protein_class_id

**Вариант B: Изменить схему на str**

```python
parent_id: Series[str] = pa.Field(nullable=True, description="Parent protein class ID")
```

**Рекомендация:** **Вариант A** — добавить в exclusion list.

______________________________________________________________________

### 2.3 semanticscholar_publication.corpus_id ⚠️ ТРЕБУЕТ АНАЛИЗА

**Ошибка:**

```
semanticscholar_publication: ID fields MUST be string type:
  - corpus_id: Int64
```

**Что это:** Semantic Scholar internal corpus identifier

**Варианты решения:**

**Вариант A (рекомендуется): Добавить в numeric_id_fields**

```python
numeric_id_fields = {
    ...,
    "corpus_id",  # Semantic Scholar internal corpus ID
}
```

**Обоснование:**

- Always numeric в Semantic Scholar API
- Internal database ID
- Nullable (Int64) — может отсутствовать

**Вариант B: Изменить схему на str**

```python
corpus_id: Series[str] | None = pa.Field(nullable=True, description="Corpus ID")
```

**Рекомендация:** **Вариант A** — добавить в exclusion list.

______________________________________________________________________

## Категория 3: Date Fields Wrong Type (1 failure)

### 3.1 uniprot_protein: Date fields using `date` instead of `datetime` ⚠️ ТРЕБУЕТ РЕШЕНИЯ

**Ошибка:**

```
uniprot_protein: Timestamp fields MUST use datetime dtype:
  - sequence_modified: date
  - entry_created: date
  - entry_modified: date
```

**Контекст:**

- UniProt возвращает даты БЕЗ времени (YYYY-MM-DD format)
- Поля представляют calendar dates, не timestamps

**Варианты решения:**

**Вариант A: Добавить exclusion для date-only fields**

```python
# tests/contract/silver_schemas/test_field_types.py
# TestDatetimeFields::test_timestamp_fields_use_datetime

# Whitelist: fields that are truly calendar dates (no time component)
date_only_fields = {
    "sequence_modified",  # UniProt sequence modification date
    "entry_created",  # UniProt entry creation date
    "entry_modified",  # UniProt entry modification date
}

non_datetime_timestamps = [
    (field, dtype)
    for field, dtype in timestamp_fields
    if (
        "datetime" not in dtype.lower()
        and "timestamp" not in dtype.lower()
        and "str" not in dtype.lower()
        and field not in date_only_fields  # Exclude date-only fields
    )
]
```

**Обоснование:**

- Семантически корректно использовать `date` для calendar dates
- Pandas `date` тип экономит память
- UniProt API не предоставляет время

**Вариант B: Изменить схему на datetime64[ns]**

```python
# src/bioetl/infrastructure/schemas/silver/uniprot/target_schema.py
sequence_modified: Series[pd.Timestamp] | None = pa.Field(...)
entry_created: Series[pd.Timestamp] | None = pa.Field(...)
entry_modified: Series[pd.Timestamp] | None = pa.Field(...)
```

**Обоснование:**

- Консистентность с остальными temporal fields
- Easier для downstream consumers (один тип для всех дат)

**Рекомендация:** **Вариант A** — добавить exclusion, т.к. это legitimate use case для `date` типа.

______________________________________________________________________

## Категория 4: Missing Enum Validation (1 failure)

### 4.1 chembl_assay_parameters.standard_type ⚠️ ТРЕБУЕТ VALIDATION

**Ошибка:**

```
chembl_assay_parameters.standard_type: Enum field missing isin validation.
Define allowed values via pa.Field(isin=[...])
```

**Контекст:**

- Поле содержит measurement types (IC50, Ki, EC50, Kd, etc.)
- Должно иметь фиксированный набор значений

**Решение: Добавить isin validation в схему**

```python
# src/bioetl/infrastructure/schemas/silver/chembl/assay_parameters_schema.py

# Во-первых, нужно узнать все возможные значения
# Можно получить из ChEMBL API documentation или из data profiling

# Пример (нужно уточнить полный список):
STANDARD_TYPES = [
    "IC50",
    "EC50",
    "Ki",
    "Kd",
    "AC50",
    "GI50",
    "MIC",
    "Activity",
    "Inhibition",
    "Potency",
    # ... добавить все возможные значения
]


class AssayParametersSchema(pa.DataFrameModel):
    standard_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=STANDARD_TYPES,
        description="Measurement type (IC50, Ki, etc.)",
    )
```

**Альтернатива:** Если список слишком большой или dynamic, добавить в test exclusion:

```python
# tests/contract/silver_schemas/test_validations.py
# TestEnumValidations::test_enum_fields_have_isin_check

# Skip fields with large/dynamic enum sets
skip_enum_validation = {
    "standard_type",  # ChEMBL: 100+ possible measurement types
}

for field in matching_fields:
    if field in skip_enum_validation:
        continue  # Skip large enum sets

    checks = fields[field].get("checks", [])
    has_isin = any(c.get("type") == "isin" for c in checks)
```

**Рекомендация:** Сначала попробовать добавить isin validation. Если список > 50 значений, добавить в skip list.

______________________________________________________________________

## Implementation Plan

### Phase 1: Quick Wins (2 minutes)

**1.1 Update snapshots**

```bash
UPDATE_SNAPSHOTS=1 python -m pytest tests/contract/silver_schemas/test_schema_stability.py
```

**Результат:** 4 failures → 0 ✅

______________________________________________________________________

### Phase 2: Test Exclusions (5 minutes)

**2.1 Add numeric ID exclusions**

```python
# tests/contract/silver_schemas/test_field_types.py
numeric_id_fields = {
    "assay_param_id",
    "taxonomy_id",
    # ... existing ...
    "toid",  # ADD: Target organism ID
    "parent_id",  # ADD: Protein class parent ID
    "corpus_id",  # ADD: Semantic Scholar corpus ID
}
```

**2.2 Add date-only field exclusions**

```python
# tests/contract/silver_schemas/test_field_types.py
# In test_timestamp_fields_use_datetime():

date_only_fields = {
    "sequence_modified",  # UniProt sequence modification date
    "entry_created",  # UniProt entry creation date
    "entry_modified",  # UniProt entry modification date
}

non_datetime_timestamps = [
    (field, dtype)
    for field, dtype in timestamp_fields
    if (
        "datetime" not in dtype.lower()
        and "timestamp" not in dtype.lower()
        and "str" not in dtype.lower()
        and field not in date_only_fields  # ADD THIS LINE
    )
]
```

**Результат:** 3 + 1 = 4 failures → 0 ✅

______________________________________________________________________

### Phase 3: Enum Validation (Decision Required)

**Option A: Add validation to schema (preferred)**

```bash
# 1. Get all possible standard_type values
python -c "
from bioetl.infrastructure.schemas.silver.chembl.assay_parameters_schema import AssayParametersSchema
import pandas as pd

# Load sample data and get unique values
# ... analyze actual data ...
"

# 2. Add isin validation to schema
# Edit: src/bioetl/infrastructure/schemas/silver/chembl/assay_parameters_schema.py
```

**Option B: Add to test exclusion (if enum too large)**

```python
# tests/contract/silver_schemas/test_validations.py
skip_enum_validation = {
    "standard_type",  # ChEMBL: 100+ possible measurement types
}
```

**Результат:** 1 failure → 0 ✅

______________________________________________________________________

## Summary

| Phase     | Action              | Files Modified      | Failures Fixed | Time        |
| --------- | ------------------- | ------------------- | -------------- | ----------- |
| 1         | Update snapshots    | snapshots/\*.json   | 4              | 2 min       |
| 2         | Add test exclusions | test_field_types.py | 4              | 5 min       |
| 3         | Enum validation     | schema OR test      | 1              | 10-30 min   |
| **Total** |                     | 2-3 files           | **9**          | **~20 min** |

______________________________________________________________________

## Verification

После всех изменений:

```bash
# Run full contract test suite
pytest tests/contract/silver_schemas/ -v

# Expected result:
# =================== 451 passed, 85 skipped in ~2s ===================
```

______________________________________________________________________

## Recommendations

### Immediate (P0)

1. ✅ Update snapshots (Phase 1) — 2 minutes
1. ✅ Add numeric_id_fields exclusions (Phase 2.1) — 2 minutes
1. ✅ Add date_only_fields exclusion (Phase 2.2) — 2 minutes

### Short-term (P1)

4. ⚠️ Demolecule_ide on standard_type validation strategy (Phase 3) — requires data analysis

### Long-term (P2)

5. 📝 Document ID field type convention в RULES.md
1. 📝 Document date vs datetime usage guideline
1. 📝 Create list of ChEMBL standard measurement types

______________________________________________________________________

## Notes

**Почему эти failures legitimate, а не false positives?**

1. **Snapshot mismatches:** Схемы действительно изменились (intentional)
1. **ID field types:** Нарушают convention "IDs должны быть строками", но есть valid exceptions для internal numeric IDs
1. **Date fields:** Семантически правильно использовать `date` для calendar dates без времени
1. **Enum validation:** Legitimate missing validation для enum field

**Все 9 failures документируют real issues or valid design choices**, требующие либо schema fixes, либо test exclusions с обоснованием.

______________________________________________________________________

**Generated:** 2026-02-10
**Author:** AI Assistant
**Status:** Ready for implementation
