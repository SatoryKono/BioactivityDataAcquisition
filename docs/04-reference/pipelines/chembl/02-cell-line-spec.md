# ChEMBL Cell Line Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.19*

______________________________________________________________________

## 1. Identification

| Parameter        | Value                                             |
| ---------------- | ------------------------------------------------- |
| **Pipeline ID**  | `chembl_cell_line`                                |
| **Provider**     | ChEMBL (EBI)                                      |
| **Entity**       | cell_line                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/cell_line` |
| **Library**      | `chembl_webresource_client`                       |
| **Rate Limit**   | None (polite usage recommended)                   |
| **Health Check** | `/chembl/api/data/status`                         |
| **Auth Type**    | None (public API)                                 |

______________________________________________________________________

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
cell_line
    │
    └──◄──FK──assay.cell_id (1:M)
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

______________________________________________________________________

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from chembl_webresource_client.new_client import new_client

cell_line = new_client.cell_line
# Filter by input CSV cell_ids
results = cell_line.filter(cell_id__in=chembl_ids)
```

### 3.2. Complete API Fields

| #   | API Field                 | JSON Type | Nullable | Description              | Example Value               |
| --- | ------------------------- | --------- | -------- | ------------------------ | --------------------------- |
| 1   | `cell_id`                 | string    | No       | Primary key (ChEMBL ID)  | `"CHEMBL3307641"`           |
| 2   | `cell_name`               | string    | No       | Cell line name           | `"HeLa"`                    |
| 3   | `cell_description`        | string    | Yes      | Description              | `"Cervical adenocarcinoma"` |
| 4   | `cell_source_tissue`      | string    | Yes      | Source tissue            | `"Cervix"`                  |
| 5   | `cell_source_organism`    | string    | Yes      | Source organism          | `"Homo sapiens"`            |
| 6   | `cell_source_taxonomy_id` | integer   | Yes      | NCBI Taxonomy ID         | `9606`                      |
| 7   | `cell_type`               | string    | Yes      | Cell type classification | `"Cancer cell line"`        |
| 8   | `cellosaurus_id`          | string    | Yes      | Cellosaurus ID           | `"CVCL_0030"`               |
| 9   | `clo_id`                  | string    | Yes      | Cell Line Ontology ID    | `"CLO_0002063"`             |
| 10  | `cl_lincs_id`             | string    | Yes      | LINCS ID                 | `"LCL-1024"`                |
| 11  | `efo_id`                  | string    | Yes      | EFO ontology ID          | `"EFO_0002067"`             |

### 3.3. Excluded Fields

| Field | Reason                  |
| ----- | ----------------------- |
| N/A   | All fields are included |

______________________________________________________________________

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `cell_id`                |
| **ID Source**       | `from_api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Field Normalization

| Field                     | Normalization  | Before            | After             |
| ------------------------- | -------------- | ----------------- | ----------------- |
| `cell_id`                 | Validate regex | `"CHEMBL3307641"` | `"CHEMBL3307641"` |
| `cell_name`               | strip()        | `" HeLa "`        | `"HeLa"`          |
| `cell_description`        | strip()        | -                 | -                 |
| `cell_source_tissue`      | strip()        | -                 | -                 |
| `cell_source_organism`    | strip()        | -                 | -                 |
| `cell_source_taxonomy_id` | Cast to int    | `"9606"`          | `9606`            |
| `cell_type`               | strip()        | -                 | -                 |
| `cellosaurus_id`          | Validate regex | `"CVCL_0030"`     | `"CVCL_0030"`     |
| `clo_id`                  | Validate regex | `"CLO_0002063"`   | `"CLO_0002063"`   |
| `cl_lincs_id`             | strip()        | -                 | -                 |
| `efo_id`                  | Validate regex | `"EFO_0002067"`   | `"EFO_0002067"`   |

### 4.3. Content Hash Specification

```python
# Fields included in hash (alphabetical order)
hash_fields = [
    "cell_id",
    "cell_description",
    "cell_name",
    "cell_source_organism",
    "cell_source_taxonomy_id",
    "cell_source_tissue",
    "cell_type",
    "cellosaurus_id",
    "cl_lincs_id",
    "clo_id",
    "efo_id",
]

# Fields EXCLUDED from hash (RULES.md §2.8.1)
excluded = ["_ingestion_ts", "_run_id", "_run_type", "_dq_*"]

# Algorithm
content_hash = sha256(f"chembl{canonical_json(filtered_record)}")
```

______________________________________________________________________

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
    cell_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        unique=True,
        description="ChEMBL ID for cell line (PK).",
    )

    # === Core Metadata ===
    cell_name: Series[str] = pa.Field(
        nullable=False,
        description="Cell line name (e.g., HeLa, MCF7).",
    )
    cell_description: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell line description.",
    )

    # === Source Information ===
    cell_source_tissue: Series[str] | None = pa.Field(
        nullable=True,
        description="Source tissue (e.g., Cervix, Breast).",
    )
    cell_source_organism: Series[str] | None = pa.Field(
        nullable=True,
        description="Source organism (e.g., Homo sapiens).",
    )
    cell_source_taxonomy_id: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="NCBI Taxonomy ID for source organism.",
    )

    # === Cell Type Classification ===
    cell_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell type classification.",
    )

    # === External Identifiers ===
    cellosaurus_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CVCL_[A-Z0-9]+$",
        description="Cellosaurus ID.",
    )
    clo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CLO_\d+$",
        description="Cell Line Ontology ID.",
    )
    cl_lincs_id: Series[str] | None = pa.Field(
        nullable=True,
        description="LINCS ID.",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^EFO_\d+$",
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
| `cell_id`                 | str  | No       | regex `^CHEMBL\d+$`, unique | CRITICAL | Quarantine     |
| `cell_name`               | str  | No       | -                           | CRITICAL | Quarantine     |
| `cell_description`        | str  | Yes      | -                           | INFO     | Log            |
| `cell_source_tissue`      | str  | Yes      | -                           | INFO     | Log            |
| `cell_source_organism`    | str  | Yes      | -                           | INFO     | Log            |
| `cell_source_taxonomy_id` | int  | Yes      | >= 1                        | WARNING  | Log            |
| `cell_type`               | str  | Yes      | -                           | INFO     | Log            |
| `cellosaurus_id`          | str  | Yes      | regex `^CVCL_[A-Z0-9]+$`    | WARNING  | Log            |
| `clo_id`                  | str  | Yes      | regex `^CLO_\d+$`           | WARNING  | Log            |
| `cl_lincs_id`             | str  | Yes      | -                           | INFO     | Log            |
| `efo_id`                  | str  | Yes      | regex `^EFO_\d+$`           | WARNING  | Log            |

### 5.3. Cross-Field Validation Rules

| Rule Name                     | Fields                                            | Condition                                         | Failure Action |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------------- | -------------- |
| `tax_id_organism_consistency` | `cell_source_taxonomy_id`, `cell_source_organism` | If tax_id=9606, organism should contain "sapiens" | Warning        |

### 5.4. DQ Thresholds

| Threshold           | Value                        | Action            |
| ------------------- | ---------------------------- | ----------------- |
| Soft                | 5%                           | Warning, continue |
| Hard                | 20%                          | Fail batch        |
| Critical field null | cell_id or cell_name is null | Fail immediately  |

______________________________________________________________________

## 6. Metadata Fields (RULES.md §2.4)

All records contain:

| Field              | Type     | Source          | In Hash |
| ------------------ | -------- | --------------- | ------- |
| `entity_id`        | str      | cell_id         | N/A     |
| `content_hash`     | str      | Computed        | N/A     |
| `_run_id`          | UUID     | Generated       | No      |
| `_run_type`        | Enum     | Config          | No      |
| `_source_batch_id` | UUID     | Generated       | No      |
| `_ingestion_ts`    | datetime | Generated (UTC) | No      |
| `_dq_warn`         | bool     | Validation      | No      |
| `_dq_error`        | bool     | Validation      | No      |
| `_index`           | int      | Generated       | No      |

______________________________________________________________________

## 7. Output Schemas

### 7.1. Bronze

```
Path: bronze/v1/chembl/cell_line/{YYYY-MM-DD}/
Format: JSONL + zstd
Mode: Append-only
Retention: 90 days → Archive
```

### 7.2. Silver

```
Path: silver/chembl/cell_line/
Format: Delta Lake (delta-rs)
Mode: Merge on [cell_id]
Partition: None
Retention: Permanent
VACUUM: Weekly, 7 days retention
```

**Silver Schema Table:**

| #     | Column                    | Type    | Nullable | Description      |
| ----- | ------------------------- | ------- | -------- | ---------------- |
| 1     | `entity_id`               | string  | No       | = cell_id        |
| 2     | `content_hash`            | string  | No       | SHA256 hash      |
| 3     | `cell_id`                 | string  | No       | PK               |
| 4     | `cell_name`               | string  | No       | Cell line name   |
| 5     | `cell_description`        | string  | Yes      | Description      |
| 6     | `cell_source_tissue`      | string  | Yes      | Source tissue    |
| 7     | `cell_source_organism`    | string  | Yes      | Source organism  |
| 8     | `cell_source_taxonomy_id` | int     | Yes      | NCBI Taxonomy ID |
| 9     | `cell_type`               | string  | Yes      | Cell type        |
| 10    | `cellosaurus_id`          | string  | Yes      | Cellosaurus ID   |
| 11    | `clo_id`                  | string  | Yes      | CLO ID           |
| 12    | `cl_lincs_id`             | string  | Yes      | LINCS ID         |
| 13    | `efo_id`                  | string  | Yes      | EFO ID           |
| 14-22 | System fields             | various | various  | See §6           |

### 7.3. Gold

```
Path: gold/chembl/cell_line/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** `cell_name IS NOT NULL`

______________________________________________________________________

## 8. Quarantine Handling

### 8.1. Error Codes

| Code                           | Description                   | Typical Cause      |
| ------------------------------ | ----------------------------- | ------------------ |
| `NULL_REQUIRED_CELL_CHEMBL_ID` | PK is null                    | Source data issue  |
| `NULL_REQUIRED_CELL_NAME`      | Name is null                  | Incomplete record  |
| `INVALID_CHEMBL_ID_FORMAT`     | ID doesn't match regex        | API change         |
| `INVALID_CELLOSAURUS_ID`       | Cellosaurus ID format invalid | Data quality issue |

### 8.2. Recovery Procedures

| Error Code        | Recovery                        |
| ----------------- | ------------------------------- |
| `NULL_REQUIRED_*` | Investigate source, skip record |
| `INVALID_*`       | Log warning, set field to null  |

______________________________________________________________________

## 9. Dependencies

### 9.1. Upstream

| Dependency | Type | Required | Notes                          |
| ---------- | ---- | -------- | ------------------------------ |
| ChEMBL API | API  | Yes      | Source of truth                |
| Input CSV  | File | Optional | Filter for specific cell lines |

### 9.2. Downstream

| Consumer                       | Impact                   |
| ------------------------------ | ------------------------ |
| `chembl_assay`                 | FK reference (cell_id)   |
| Cell line enrichment analytics | Tissue/organism analysis |

### 9.3. Cross-Provider Mapping

| This Entity Field | Maps To     | Provider    | Field     |
| ----------------- | ----------- | ----------- | --------- |
| `cellosaurus_id`  | Cellosaurus | ExPASy      | Accession |
| `clo_id`          | CLO         | OBO Foundry | ID        |
| `efo_id`          | EFO         | EMBL-EBI    | ID        |

______________________________________________________________________

## 10. Pipeline Configuration

```yaml
# configs/pipelines/chembl/cell_line.yaml

pipeline_name: chembl_cell_line
provider: chembl
entity_type: cell_line
version: "1.2.0"
description: "Extract cell lines from ChEMBL API"

primary_keys: ["cell_id"]
silver_table: "chembl_cell_line"
gold_table: "chembl_cell_line"

source_file: ../../sources/chembl.yaml

gold_filters:
  required_fields:
    - cell_name

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["cell_id"]
    partition_by: []
    sort_by:
      columns: ["cell_id"]
      ascending: true
    csv_export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    sort_by:
      columns: ["cell_id", "cell_name"]
      ascending: true
    csv_export:
      path: "data/output/csv/gold"

input_filter:
  enabled: true
  source_path: "data/input/cell.csv"
  column_name: "cell_id"
  filter_field: "cell_id"
  batch_size: 20
```

______________________________________________________________________

## 11. Testing Requirements

### 11.1. Unit Tests

- [x] `test_cell_line_normalization.py`
- [x] `test_cell_line_content_hash.py`
- [x] `test_cell_line_validation.py`

### 11.2. Integration Tests (VCR)

- [x] `test_cell_line_api_fetch.py`
- [x] `test_cell_line_filter_batch.py`
- [x] `test_cell_line_error_handling.py`

### 11.3. Architecture Tests

- [x] Schema strict mode validation
- [x] Layer import compliance

______________________________________________________________________

## 12. Field Mapping CSV

See `docs/pipelines/chembl/cell-line-fields.csv` for Excel-compatible field mapping.
