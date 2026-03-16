# ChEMBL Cell Line Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.24*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                             |
| ---------------- | ------------------------------------------------- |
| **Pipeline ID**  | `chembl_cell_line`                                |
| **Provider**     | ChEMBL (EBI)                                      |
| **Entity**       | cell-line                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/cell-line` |
| **Library**      | Built-in ChEMBL adapter (httpx)                       |
| **Rate Limit**   | None (polite usage recommended)                   |
| **Health Check** | `/chembl/api/data/status`                         |
| **Auth Type**    | None (public API)                                 |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Cell Lines represent **biological cell cultures** used in experimental assays. They provide crucial context for interpreting bioactivity data:

- **In vitro context**: Understanding which cell model was used for testing
- **Tissue origin**: Tracking source tissue and organism
- **Cross-reference**: Linking to external databases (Cellosaurus, CLO, EFO)
- **Cancer research**: Many cell lines are derived from tumors

### 2.2. Use Cases

1. **Assay Context Analysis**: Determine which cell lines are most commonly used for specific target types
1. **Tissue-Specific Studies**: Filter bioactivity data by cell line tissue origin
1. **Cross-Database Linking**: Map ChEMBL cell lines to Cellosaurus for detailed metadata
1. **Species Selection**: Filter by organism (human, mouse, rat cell lines)

### 2.3. Entity Relationships

```
cell-line
    │
    └──◄──FK──assay.cell-id (1:M)
              │
              └──◄──activity (via assay)
```

### 2.4. Load Strategy

| Parameter               | Value                           |
| ----------------------- | ------------------------------- |
| **Strategy**            | `incremental` with input filter |
| **Watermark Field**     | N/A (filtered by input CSV)     |
| **Full Load Frequency** | On demand                       |
| **Estimated Volume**    | ~2,500 records total            |
| **Batch Size**          | 20 (filter batch)               |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

adapter = ChemblAdapter(config=adapter_config)
# Built-in adapter handles pagination, retries, health checks
results = adapter.fetch(entity=\"cell_line\", filters={\"cell-id\": chembl_ids})
```

### 3.2. Complete API Fields

| #   | API Field                 | JSON Type | Nullable | Description              | Example Value               |
| --- | ------------------------- | --------- | -------- | ------------------------ | --------------------------- |
| 1   | `cell-id`                 | string    | No       | Primary key (ChEMBL ID)  | `"CHEMBL3307641"`           |
| 2   | `cell-name`               | string    | No       | Cell line name           | `"HeLa"`                    |
| 3   | `cell-description`        | string    | Yes      | Description              | `"Cervical adenocarcinoma"` |
| 4   | `cell-source-tissue`      | string    | Yes      | Source tissue            | `"Cervix"`                  |
| 5   | `cell-source-organism`    | string    | Yes      | Source organism          | `"Homo sapiens"`            |
| 6   | `cell-source-taxonomy-id` | integer   | Yes      | NCBI Taxonomy ID         | `9606`                      |
| 7   | `cell-type`               | string    | Yes      | Cell type classification | `"Cancer cell line"`        |
| 8   | `cellosaurus-id`          | string    | Yes      | Cellosaurus ID           | `"CVCL-0030"`               |
| 9   | `clo-id`                  | string    | Yes      | Cell Line Ontology ID    | `"CLO-0002063"`             |
| 10  | `cl-lincs-id`             | string    | Yes      | LINCS ID                 | `"LCL-1024"`                |
| 11  | `efo-id`                  | string    | Yes      | EFO ontology ID          | `"EFO-0002067"`             |

### 3.3. Excluded Fields

| Field | Reason                  |
| ----- | ----------------------- |
| N/A   | All fields are included |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `cell-id`                |
| **ID Source**       | `from-api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Field Normalization

| Field                     | Normalization  | Before            | After             |
| ------------------------- | -------------- | ----------------- | ----------------- |
| `cell-id`                 | Validate regex | `"CHEMBL3307641"` | `"CHEMBL3307641"` |
| `cell-name`               | strip()        | `" HeLa "`        | `"HeLa"`          |
| `cell-description`        | strip()        | -                 | -                 |
| `cell-source-tissue`      | strip()        | -                 | -                 |
| `cell-source-organism`    | strip()        | -                 | -                 |
| `cell-source-taxonomy-id` | Cast to int    | `"9606"`          | `9606`            |
| `cell-type`               | strip()        | -                 | -                 |
| `cellosaurus-id`          | Validate regex | `"CVCL-0030"`     | `"CVCL-0030"`     |
| `clo-id`                  | Validate regex | `"CLO-0002063"`   | `"CLO-0002063"`   |
| `cl-lincs-id`             | strip()        | -                 | -                 |
| `efo-id`                  | Validate regex | `"EFO-0002067"`   | `"EFO-0002067"`   |

### 4.3. Content Hash Specification

```python
# Fields included in hash (alphabetical order)
hash-fields = [
    "cell-id",
    "cell-description",
    "cell-name",
    "cell-source-organism",
    "cell-source-taxonomy-id",
    "cell-source-tissue",
    "cell-type",
    "cellosaurus-id",
    "cl-lincs-id",
    "clo-id",
    "efo-id",
]

# Fields EXCLUDED from hash (RULES.md §2.8.1)
excluded = ["_ingestion_ts", "_run_id", "_run_type", "_dq_*"]

# Algorithm
content-hash = sha256(f"chembl{canonical-json(filtered-record)}")
```

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
# src/bioetl/domain/schemas/chembl/cell_line.py

import pandera.pandas as pa
from pandera.typing import Series
from bioetl.domain.schemas.base import ETLRecordSchema


class CellLineSchema(ETLRecordSchema):
    """Cell Line validation schema for Silver layer."""

    # === Primary Key ===
    cell-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
        unique=True,
        description="ChEMBL ID for cell line (PK).",
    )

    # === Core Metadata ===
    cell-name: Series[str] = pa.Field(
        nullable=False,
        description="Cell line name (e.g., HeLa, MCF7).",
    )
    cell-description: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell line description.",
    )

    # === Source Information ===
    cell-source-tissue: Series[str] | None = pa.Field(
        nullable=True,
        description="Source tissue (e.g., Cervix, Breast).",
    )
    cell-source-organism: Series[str] | None = pa.Field(
        nullable=True,
        description="Source organism (e.g., Homo sapiens).",
    )
    cell-source-taxonomy-id: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="NCBI Taxonomy ID for source organism.",
    )

    # === Cell Type Classification ===
    cell-type: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell type classification.",
    )

    # === External Identifiers ===
    cellosaurus-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CVCL-[A-Z0-9]+$",
        description="Cellosaurus ID.",
    )
    clo-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CLO-\d+$",
        description="Cell Line Ontology ID.",
    )
    cl-lincs-id: Series[str] | None = pa.Field(
        nullable=True,
        description="LINCS ID.",
    )
    efo-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^EFO-\d+$",
        description="EFO ontology ID.",
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field                     | Type | Nullable | Constraints                 | DQ Level | Failure Action |
| ------------------------- | ---- | -------- | --------------------------- | -------- | -------------- |
| `cell-id`                 | str  | No       | regex `^CHEMBL\d+$`, unique | CRITICAL | Quarantine     |
| `cell-name`               | str  | No       | -                           | CRITICAL | Quarantine     |
| `cell-description`        | str  | Yes      | -                           | INFO     | Log            |
| `cell-source-tissue`      | str  | Yes      | -                           | INFO     | Log            |
| `cell-source-organism`    | str  | Yes      | -                           | INFO     | Log            |
| `cell-source-taxonomy-id` | int  | Yes      | >= 1                        | WARNING  | Log            |
| `cell-type`               | str  | Yes      | -                           | INFO     | Log            |
| `cellosaurus-id`          | str  | Yes      | regex `^CVCL-[A-Z0-9]+$`    | WARNING  | Log            |
| `clo-id`                  | str  | Yes      | regex `^CLO-\d+$`           | WARNING  | Log            |
| `cl-lincs-id`             | str  | Yes      | -                           | INFO     | Log            |
| `efo-id`                  | str  | Yes      | regex `^EFO-\d+$`           | WARNING  | Log            |

### 5.3. Cross-Field Validation Rules

| Rule Name                     | Fields                                            | Condition                                         | Failure Action |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------------- | -------------- |
| `tax-id-organism-consistency` | `cell-source-taxonomy-id`, `cell-source-organism` | If tax-id=9606, organism should contain "sapiens" | Warning        |

### 5.4. DQ Thresholds

| Threshold           | Value                        | Action            |
| ------------------- | ---------------------------- | ----------------- |
| Soft                | 5%                           | Warning, continue |
| Hard                | 20%                          | Fail batch        |
| Critical field null | cell-id or cell-name is null | Fail immediately  |

----------------------------------------------------------------------

## 6. Metadata Fields (RULES.md §2.4)

All records contain:

| Field              | Type     | Source          | In Hash |
| ------------------ | -------- | --------------- | ------- |
| `entity_id`        | str      | cell-id         | N/A     |
| `content_hash`     | str      | Computed        | N/A     |
| `_run_id`          | UUID     | Generated       | No      |
| `_run_type`        | Enum     | Config          | No      |
| `_source_batch_id` | UUID     | Generated       | No      |
| `_ingestion_ts`    | datetime | Generated (UTC) | No      |
| `_dq_warn`         | bool     | Validation      | No      |
| `_dq_error`        | bool     | Validation      | No      |
| `_index`           | int      | Generated       | No      |

----------------------------------------------------------------------

## 7. Output Schemas

### 7.1. Bronze

```
Path: bronze/v1/chembl/cell-line/{YYYY-MM-DD}/
Format: JSONL + zstd
Mode: Append-only
Retention: 90 days → Archive
```

### 7.2. Silver

```
Path: silver/chembl/cell-line/
Format: Delta Lake (delta-rs)
Mode: Merge on [cell-id]
Partition: None
Retention: Permanent
VACUUM: Weekly, 7 days retention
```

**Silver Schema Table:**

| #     | Column                    | Type    | Nullable | Description      |
| ----- | ------------------------- | ------- | -------- | ---------------- |
| 1     | `entity_id`               | string  | No       | = cell-id        |
| 2     | `content_hash`            | string  | No       | SHA256 hash      |
| 3     | `cell-id`                 | string  | No       | PK               |
| 4     | `cell-name`               | string  | No       | Cell line name   |
| 5     | `cell-description`        | string  | Yes      | Description      |
| 6     | `cell-source-tissue`      | string  | Yes      | Source tissue    |
| 7     | `cell-source-organism`    | string  | Yes      | Source organism  |
| 8     | `cell-source-taxonomy-id` | int     | Yes      | NCBI Taxonomy ID |
| 9     | `cell-type`               | string  | Yes      | Cell type        |
| 10    | `cellosaurus-id`          | string  | Yes      | Cellosaurus ID   |
| 11    | `clo-id`                  | string  | Yes      | CLO ID           |
| 12    | `cl-lincs-id`             | string  | Yes      | LINCS ID         |
| 13    | `efo-id`                  | string  | Yes      | EFO ID           |
| 14-22 | System fields             | various | various  | See §6           |

### 7.3. Gold

```
Path: gold/chembl/cell-line/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** `cell-name IS NOT NULL`

----------------------------------------------------------------------

## 8. Quarantine Handling

### 8.1. Error Codes

| Code                           | Description                   | Typical Cause      |
| ------------------------------ | ----------------------------- | ------------------ |
| `NULL-REQUIRED-CELL-CHEMBL-ID` | PK is null                    | Source data issue  |
| `NULL-REQUIRED-CELL-NAME`      | Name is null                  | Incomplete record  |
| `INVALID-CHEMBL-ID-FORMAT`     | ID doesn't match regex        | API change         |
| `INVALID-CELLOSAURUS-ID`       | Cellosaurus ID format invalid | Data quality issue |

### 8.2. Recovery Procedures

| Error Code        | Recovery                        |
| ----------------- | ------------------------------- |
| `NULL-REQUIRED-*` | Investigate source, skip record |
| `INVALID-*`       | Log warning, set field to null  |

----------------------------------------------------------------------

## 9. Dependencies

### 9.1. Upstream

| Dependency | Type | Required | Notes                          |
| ---------- | ---- | -------- | ------------------------------ |
| ChEMBL API | API  | Yes      | Source of truth                |
| Input CSV  | File | Optional | Filter for specific cell lines |

### 9.2. Downstream

| Consumer                       | Impact                   |
| ------------------------------ | ------------------------ |
| `chembl_assay`                 | FK reference (cell-id)   |
| Cell line enrichment analytics | Tissue/organism analysis |

### 9.3. Cross-Provider Mapping

| This Entity Field | Maps To     | Provider    | Field     |
| ----------------- | ----------- | ----------- | --------- |
| `cellosaurus-id`  | Cellosaurus | ExPASy      | Accession |
| `clo-id`          | CLO         | OBO Foundry | ID        |
| `efo-id`          | EFO         | EMBL-EBI    | ID        |

----------------------------------------------------------------------

## 10. Pipeline Configuration

```yaml
# configs/entities/chembl/cell_line.yaml

pipeline_name: chembl_cell_line
provider: chembl
entity_type: cell-line
version: "1.2.0"
description: "Extract cell lines from ChEMBL API"

primary_keys: ["cell-id"]
silver_table: "chembl_cell_line"
gold_table: "chembl_cell_line"

source_file: ../../sources/chembl.yaml

gold_filters:
  required_fields:
    - cell-name

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["cell-id"]
    partition_by: []
    sort_by:
      columns: ["cell-id"]
      ascending: true
    csv_export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    sort_by:
      columns: ["cell-id", "cell-name"]
      ascending: true
    csv_export:
      path: "data/output/csv/gold"

input_filter:
  enabled: true
  source_path: "data/input/cell.csv"
  column_name: "cell-id"
  filter_field: "cell-id"
  batch_size: 20
```

----------------------------------------------------------------------

## 11. Testing Requirements

### 11.1. Unit Tests

- [x] `tests/unit/application/pipelines/test_cell_line_transformer.py`

### 11.2. Integration Tests (VCR)

- [x] `tests/integration/pipelines/test_chembl_cell_line.py`

### 11.3. Architecture Tests

- [x] Schema strict mode validation
- [x] Layer import compliance

----------------------------------------------------------------------

## 12. Field Mapping CSV

See `docs/04-reference/pipelines/chembl/cell-line-fields.csv` for Excel-compatible field mapping.
