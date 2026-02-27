# ChEMBL Protein Classification Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.22*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                                 |
| ---------------- | ----------------------------------------------------- |
| **Pipeline ID**  | `chembl_protein_class`                                |
| **Provider**     | ChEMBL (EBI)                                          |
| **Entity**       | protein-class                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/protein-class` |
| **Library**      | `chembl-webresource-client`                           |
| **Rate Limit**   | None (polite usage recommended)                       |
| **Health Check** | `/chembl/api/data/status`                             |
| **Auth Type**    | None (public API)                                     |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Protein Classification represents a **hierarchical taxonomy** of protein families used to categorize biological targets in ChEMBL. This classification system enables:

- **Target categorization**: Group targets by biological function (kinases, GPCRs, ion channels, etc.)
- **Drug discovery insights**: Identify druggable protein families
- **Cross-species analysis**: Compare protein classes across organisms
- **Ontology alignment**: Map to external classification systems

### 2.2. Use Cases

1. **Target Class Distribution**: Analyze which protein families have the most bioactivity data
1. **Drug Target Identification**: Find unexplored protein classes for novel therapeutics
1. **Hierarchical Queries**: Navigate from broad classes (Enzyme) to specific subfamilies (Kinase → Tyrosine Kinase → EGFR)

### 2.3. Entity Relationships

```
protein-class (self-referential hierarchy)
    │
    ├──FK (parent-id)──► protein-class (parent classification)
    │
    └──◄──FK──target-component.protein-class-id (M:N via junction)
              │
              └──► target (contains this protein)
```

### 2.4. Load Strategy

| Parameter               | Value                    |
| ----------------------- | ------------------------ |
| **Strategy**            | `full` (reference table) |
| **Watermark Field**     | N/A                      |
| **Full Load Frequency** | On demand or weekly      |
| **Estimated Volume**    | ~1,500 records           |
| **Batch Size**          | 500                      |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from chembl-webresource-client.new-client import new-client

protein-class = new-client.protein-class
results = protein-class.filter().only(
    [
        "protein-class-id",
        "parent-id",
        "pref-name",
        "short-name",
        "protein-class-desc",
        "definition",
        "class-level",
        "sort-order",
        "downgraded",
        "replaced-by",
    ]
)
```

### 3.2. Complete API Fields

| #   | API Field            | JSON Type | Nullable | Description                 | Example Value                     |
| --- | -------------------- | --------- | -------- | --------------------------- | --------------------------------- |
| 1   | `protein-class-id`   | integer   | No       | Primary key (internal ID)   | `1`                               |
| 2   | `parent-id`          | integer   | Yes      | FK to parent classification | `null`, `1`                       |
| 3   | `pref-name`          | string    | Yes      | Preferred name              | `"Kinase"`                        |
| 4   | `short-name`         | string    | Yes      | Short name                  | `"Kin"`                           |
| 5   | `protein-class-desc` | string    | Yes      | Full description            | `"Protein kinases"`               |
| 6   | `definition`         | string    | Yes      | Definition text             | `"Enzymes that phosphorylate..."` |
| 7   | `class-level`        | integer   | Yes      | Level in hierarchy (1-8)    | `1`, `2`, `3`                     |
| 8   | `sort-order`         | integer   | Yes      | Display sort order          | `100`                             |
| 9   | `downgraded`         | integer   | Yes      | Deprecated flag (0/1)       | `0`                               |
| 10  | `replaced-by`        | integer   | Yes      | FK to replacement record    | `null`, `456`                     |

### 3.3. Excluded Fields

| Field | Reason                  |
| ----- | ----------------------- |
| N/A   | All fields are included |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                                  |
| ------------------- | -------------------------------------- |
| **Entity ID Field** | `protein-class-id`                     |
| **ID Source**       | `from-api`                             |
| **Format**          | Integer (cast to string for entity-id) |

### 4.2. Field Normalization

| Field                | Normalization       | Before       | After      |
| -------------------- | ------------------- | ------------ | ---------- |
| `protein-class-id`   | Cast to int         | `"1"`        | `1`        |
| `parent-id`          | Cast to int or None | `"null"`     | `None`     |
| `pref-name`          | strip()             | `" Kinase "` | `"Kinase"` |
| `short-name`         | strip()             | `" Kin "`    | `"Kin"`    |
| `protein-class-desc` | strip()             | -            | -          |
| `definition`         | strip()             | -            | -          |
| `class-level`        | Cast to int         | `"1"`        | `1`        |
| `sort-order`         | Cast to int         | `"100"`      | `100`      |
| `downgraded`         | Cast to int (0/1)   | `"0"`        | `0`        |
| `replaced-by`        | Cast to int or None | `"null"`     | `None`     |

### 4.3. Content Hash Specification

```python
# Fields included in hash (alphabetical order)
hash-fields = [
    "class-level",
    "definition",
    "downgraded",
    "parent-id",
    "pref-name",
    "protein-class-desc",
    "protein-class-id",
    "replaced-by",
    "short-name",
    "sort-order",
]

# Fields EXCLUDED from hash (RULES.md §2.8.1)
excluded = ["-ingestion-ts", "-run-id", "-run-type", "-dq-*"]

# Algorithm
content-hash = sha256(f"chembl{canonical-json(filtered-record)}")
```

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

```python
# src/bioetl/domain/schemas/chembl/protein-classification.py

import pandera.pandas as pa
from pandera.typing import Series
from bioetl.domain.schemas.base import ETLRecordSchema


class ProteinClassificationSchema(ETLRecordSchema):
    """Protein Classification validation schema for Silver layer."""

    # === Primary Key ===
    protein-class-id: Series[int] = pa.Field(nullable=False, description="Primary key.")

    # === Foreign Keys ===
    parent-id: Series[int] | None = pa.Field(
        nullable=True, description="FK to parent classification."
    )
    replaced-by: Series[int] | None = pa.Field(
        nullable=True, description="FK to replacement classification."
    )

    # === Metadata ===
    pref-name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    short-name: Series[str] | None = pa.Field(nullable=True, description="Short name.")
    protein-class-desc: Series[str] | None = pa.Field(
        nullable=True, description="Description."
    )
    definition: Series[str] | None = pa.Field(nullable=True, description="Definition.")
    class-level: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="Class level.",
    )
    sort-order: Series[int] | None = pa.Field(nullable=True, description="Sort order.")

    # === Flags ===
    downgraded: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Downgraded flag.",
    )

    class Config:
        strict = True
        ordered = True
        coerce = True
```

### 5.2. Field Validation Matrix

| Field                | Type | Nullable | Constraints  | DQ Level | Failure Action |
| -------------------- | ---- | -------- | ------------ | -------- | -------------- |
| `protein-class-id`   | int  | No       | >= 1         | CRITICAL | Quarantine     |
| `parent-id`          | int  | Yes      | >= 1 or None | WARNING  | Log            |
| `replaced-by`        | int  | Yes      | >= 1 or None | WARNING  | Log            |
| `pref-name`          | str  | Yes      | -            | INFO     | Log            |
| `short-name`         | str  | Yes      | -            | INFO     | Log            |
| `protein-class-desc` | str  | Yes      | -            | INFO     | Log            |
| `definition`         | str  | Yes      | -            | INFO     | Log            |
| `class-level`        | int  | Yes      | >= 1         | WARNING  | Log            |
| `sort-order`         | int  | Yes      | -            | INFO     | Log            |
| `downgraded`         | int  | Yes      | isin [0, 1]  | WARNING  | Log            |

### 5.3. Cross-Field Validation Rules

| Rule Name           | Fields                          | Condition                               | Failure Action |
| ------------------- | ------------------------------- | --------------------------------------- | -------------- |
| `parent-self-ref`   | `parent-id`, `protein-class-id` | parent-id != protein-class-id           | Quarantine     |
| `replaced-inactive` | `downgraded`, `replaced-by`     | downgraded=1 implies replaced-by is set | Warning        |

### 5.4. DQ Thresholds

| Threshold           | Value                        | Action            |
| ------------------- | ---------------------------- | ----------------- |
| Soft                | 5%                           | Warning, continue |
| Hard                | 20%                          | Fail batch        |
| Critical field null | Any protein-class-id is null | Fail immediately  |

----------------------------------------------------------------------

## 6. Metadata Fields (RULES.md §2.4)

All records contain:

| Field              | Type     | Source                  | In Hash |
| ------------------ | -------- | ----------------------- | ------- |
| `entity-id`        | str      | protein-class-id (cast) | N/A     |
| `content-hash`     | str      | Computed                | N/A     |
| `-run-id`          | UUID     | Generated               | No      |
| `-run-type`        | Enum     | Config                  | No      |
| `-source-batch-id` | UUID     | Generated               | No      |
| `-ingestion-ts`    | datetime | Generated (UTC)         | No      |
| `-dq-warn`         | bool     | Validation              | No      |
| `-dq-error`        | bool     | Validation              | No      |
| `-index`           | int      | Generated               | No      |

----------------------------------------------------------------------

## 7. Output Schemas

### 7.1. Bronze

```
Path: bronze/v1/chembl/protein-class/{YYYY-MM-DD}/
Format: JSONL + zstd
Mode: Append-only
Retention: 90 days → Archive
```

### 7.2. Silver

```
Path: silver/chembl/protein-class/class-level={L}/
Format: Delta Lake (delta-rs)
Mode: Merge on [protein-class-id]
Partition: [class-level]
Retention: Permanent
VACUUM: Weekly, 7 days retention
```

**Silver Schema Table:**

| #   | Column               | Type      | Nullable | Description        |
| --- | -------------------- | --------- | -------- | ------------------ |
| 1   | `entity-id`          | string    | No       | = protein-class-id |
| 2   | `content-hash`       | string    | No       | SHA256 hash        |
| 3   | `protein-class-id`   | int       | No       | PK                 |
| 4   | `parent-id`          | int       | Yes      | FK to parent       |
| 5   | `replaced-by`        | int       | Yes      | FK to replacement  |
| 6   | `pref-name`          | string    | Yes      | Preferred name     |
| 7   | `short-name`         | string    | Yes      | Short name         |
| 8   | `protein-class-desc` | string    | Yes      | Description        |
| 9   | `definition`         | string    | Yes      | Definition         |
| 10  | `class-level`        | int       | Yes      | Hierarchy level    |
| 11  | `sort-order`         | int       | Yes      | Sort order         |
| 12  | `downgraded`         | int       | Yes      | Deprecated flag    |
| 13  | `-run-id`            | uuid      | No       | Pipeline run ID    |
| 14  | `-run-type`          | string    | No       | Run type           |
| 15  | `-source-batch-id`   | uuid      | Yes      | Batch context      |
| 16  | `-ingestion-ts`      | timestamp | No       | Ingestion time     |
| 17  | `-dq-warn`           | bool      | No       | DQ warning flag    |
| 18  | `-dq-error`          | bool      | No       | DQ error flag      |
| 19  | `-index`             | int       | No       | Record index       |

### 7.3. Gold

```
Path: gold/chembl/protein-class/
Format: Delta Lake
Mode: Overwrite (reference table)
```

**Gold Filter:** `downgraded = 0` AND `pref-name IS NOT NULL`

----------------------------------------------------------------------

## 8. Quarantine Handling

### 8.1. Error Codes

| Code                             | Description                  | Typical Cause        |
| -------------------------------- | ---------------------------- | -------------------- |
| `NULL-REQUIRED-PROTEIN-CLASS-ID` | PK is null                   | Source data issue    |
| `INVALID-CLASS-LEVEL`            | class-level < 1              | Schema violation     |
| `SELF-REFERENTIAL-PARENT`        | parent-id = protein-class-id | Data integrity issue |
| `INVALID-DOWNGRADED`             | downgraded not in [0,1]      | API change           |

### 8.2. Recovery Procedures

| Error Code        | Recovery                           |
| ----------------- | ---------------------------------- |
| `NULL-REQUIRED-*` | Investigate source, skip record    |
| `INVALID-*`       | Log warning, coerce to valid value |

----------------------------------------------------------------------

## 9. Dependencies

### 9.1. Upstream

| Dependency | Type | Required | Notes           |
| ---------- | ---- | -------- | --------------- |
| ChEMBL API | API  | Yes      | Source of truth |

### 9.2. Downstream

| Consumer                  | Impact                                   |
| ------------------------- | ---------------------------------------- |
| `chembl_target_component` | FK reference for protein classifications |
| `chembl_target`           | Enrichment with protein class hierarchy  |
| Analytics dashboards      | Target class distribution reports        |

----------------------------------------------------------------------

## 10. Pipeline Configuration

```yaml
# configs/entities/chembl/protein-class.yaml

pipeline-name: chembl_protein_class
provider: chembl
entity-type: protein-class
version: "1.2.0"
description: "ChEMBL Protein Classification hierarchy"

primary-keys: ["protein-class-id"]
silver-table: chembl_protein_class
gold-table: chembl_protein_class

source-file: ../../sources/chembl.yaml
batch-size: 500
checkpoint-interval: 500

gold-filters:
  required-fields:
    - pref-name
  columns:
    downgraded: ["0"]

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary-key: ["protein-class-id"]
    partition-by: ["class-level"]
    sort-by:
      columns: ["protein-class-id"]
      ascending: true
    csv-export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    sort-by:
      columns: ["class-level", "sort-order", "protein-class-id"]
      ascending: true
    csv-export:
      path: "data/output/csv/gold"

input-filter:
  enabled: false
```

----------------------------------------------------------------------

## 11. Testing Requirements

### 11.1. Unit Tests

- [x] `test-protein-class-normalization.py`
- [x] `test-protein-class-content-hash.py`
- [x] `test-protein-class-validation.py`

### 11.2. Integration Tests (VCR)

- [x] `test-protein-class-api-fetch.py`
- [x] `test-protein-class-pagination.py`
- [x] `test-protein-class-error-handling.py`

### 11.3. Architecture Tests

- [x] Schema strict mode validation
- [x] Layer import compliance

----------------------------------------------------------------------

## 12. Field Mapping CSV

See `docs/pipelines/chembl/protein-class-fields.csv` for Excel-compatible field mapping.
