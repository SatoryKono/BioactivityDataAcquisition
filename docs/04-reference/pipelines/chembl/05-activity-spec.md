# ChEMBL Activity Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.23*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                            |
| ---------------- | ------------------------------------------------ |
| **Pipeline ID**  | `chembl_activity`                                |
| **Provider**     | ChEMBL (EBI)                                     |
| **Entity**       | activity                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/activity` |
| **Library**      | `chembl-webresource-client`                      |
| **Rate Limit**   | None (polite usage recommended)                  |
| **Health Check** | `/chembl/api/data/status`                        |
| **Auth Type**    | None (public API)                                |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Activities are the **core measurement data** in ChEMBL, representing bioactivity measurements of molecules against biological targets:

- **Bioactivity measurements**: IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50, EC50, potency, inhibition
- **Structure-Activity Relationships (SAR)**: Connect molecules to targets via measured values
- **Drug discovery data**: Quantitative data from screening and assays
- **Data quality tracking**: Standardized values with quality annotations

### 2.2. Use Cases

1. **SAR Analysis**: Analyze activity profiles for lead compounds
1. **Target Druggability**: Assess targets by activity data availability
1. **Compound Ranking**: Rank molecules by pChEMBL value
1. **Data Quality Assessment**: Filter by standardization and validity flags
1. **Literature Mining**: Link activities to source publications

### 2.3. Entity Relationships

```
activity
    │
    ├──FK──► assay.assay-id (M:1, required)
    │
    ├──FK──► molecule.molecule-id (M:1, required)
    │
    ├──FK──► target.target-id (M:1, optional)
    │
    ├──FK──► document.publication-id (M:1, optional)
    │
    └── ligand-efficiency (nested object)
        ├── bei, le, lle, sei
```

### 2.4. Load Strategy

| Parameter            | Value                                       |
| -------------------- | ------------------------------------------- |
| **Strategy**         | `incremental` with input filter             |
| **Watermark Field**  | N/A (filtered by assay/molecule/target IDs) |
| **Estimated Volume** | ~20M records total                          |
| **Batch Size**       | 20 (filter batch)                           |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from chembl-webresource-client.new-client import new-client

activity = new-client.activity
# Filter by target, molecule, or assay
results = activity.filter(target-id--in=target-ids)
```

### 3.2. Complete API Fields

| #   | API Field               | JSON Type | Nullable | Description        | Example                    |
| --- | ----------------------- | --------- | -------- | ------------------ | -------------------------- |
| 1   | `activity-id`           | integer   | No       | Primary key        | `12345678`                 |
| 2   | `assay-id`              | string    | No       | FK to assay        | `"CHEMBL123456"`           |
| 3   | `molecule-id`           | string    | No       | FK to molecule     | `"CHEMBL25"`               |
| 4   | `target-id`             | string    | Yes      | FK to target       | `"CHEMBL240"`              |
| 5   | `publication-id`        | string    | Yes      | FK to document     | `"CHEMBL1234"`             |
| 6   | `standard-type`         | string    | Yes      | Measurement type   | `"IC50"`                   |
| 7   | `standard-relation`     | string    | Yes      | Relation           | `"="`                      |
| 8   | `standard-value`        | number    | Yes      | Standardized value | `50.0`                     |
| 9   | `standard-units`        | string    | Yes      | Standardized units | `"nM"`                     |
| 10  | `standard-flag`         | integer   | Yes      | Standardized flag  | `1`                        |
| 11  | `pchembl-value`         | number    | Yes      | -log10 molar       | `7.3`                      |
| 12  | `data-validity-comment` | string    | Yes      | DQ comment         | `"Potential author error"` |
| 13  | `activity-comment`      | string    | Yes      | Text comment       | `"Active"`                 |
| 14  | `potential-duplicate`   | integer   | Yes      | Duplicate flag     | `0`                        |
| 15  | `type`                  | string    | Yes      | Original type      | `"IC50"`                   |
| 16  | `relation`              | string    | Yes      | Original relation  | `"="`                      |
| 17  | `value`                 | number    | Yes      | Original value     | `50.0`                     |
| 18  | `units`                 | string    | Yes      | Original units     | `"nM"`                     |
| 19  | `text-value`            | string    | Yes      | Text value         | `"Active"`                 |
| 20  | `standard-text-value`   | string    | Yes      | Std text value     | `"Active"`                 |
| 21  | `upper-value`           | number    | Yes      | Upper bound        | `100.0`                    |
| 22  | `standard-upper-value`  | number    | Yes      | Std upper bound    | `100.0`                    |
| 23  | `src-id`                | integer   | Yes      | Source ID          | `1`                        |
| 24  | `record-id`             | integer   | Yes      | FK compound-record | `12345`                    |
| 25  | `toid`                  | integer   | Yes      | Test Occasion ID   | `1`                        |
| 26  | `bao-endpoint`          | string    | Yes      | BAO endpoint ID    | `"BAO:0000190"`            |
| 27  | `uo-units`              | string    | Yes      | UO units ID        | `"UO:0000065"`             |
| 28  | `qudt-units`            | string    | Yes      | QUDT units         | `"nM"`                     |
| 29  | `ligand-efficiency`     | object    | Yes      | Efficiency metrics | JSON                       |
| 30  | `activity-properties`   | array     | Yes      | Properties         | JSON                       |

### 3.3. Nested Structure: ligand-efficiency

| Field | Type  | Description                  |
| ----- | ----- | ---------------------------- |
| `bei` | float | Binding Efficiency Index     |
| `le`  | float | Ligand Efficiency            |
| `lle` | float | Lipophilic Ligand Efficiency |
| `sei` | float | Surface Efficiency Index     |

### 3.4. Denormalized Fields (from related entities)

The API also returns denormalized fields from related entities:

| Field                | Source Entity       | Description     |
| -------------------- | ------------------- | --------------- |
| `canonical-smiles`   | molecule.structures | SMILES string   |
| `molecule-pref-name` | molecule            | Molecule name   |
| `parent-molecule-id` | molecule.hierarchy  | Parent molecule |
| `target-pref-name`   | target              | Target name     |
| `target-organism`    | target              | Organism        |
| `target-tax-id`      | target              | Taxonomy ID     |
| `assay-type`         | assay               | Assay type      |
| `assay-description`  | assay               | Description     |
| `bao-format`         | assay               | BAO format      |
| `bao-label`          | assay               | BAO label       |
| `document-journal`   | document            | Journal         |
| `document-year`      | document            | Year            |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `activity-id`            |
| **ID Source**       | `from-api`               |
| **Format**          | Integer (cast to string) |

### 4.2. Field Normalization

| Field               | Normalization  | Before            | After           |
| ------------------- | -------------- | ----------------- | --------------- |
| `activity-id`       | Cast to string | `12345678`        | `"12345678"`    |
| `standard-value`    | round(10)      | `50.123456789012` | `50.1234567890` |
| `pchembl-value`     | round(2)       | `7.3456`          | `7.35`          |
| `standard-relation` | Validate isin  | `"="`             | `"="`           |
| `standard-units`    | strip()        | `" nM "`          | `"nM"`          |

### 4.3. Flattening Strategy

| Nested Path             | Flattened Name          | Strategy       |
| ----------------------- | ----------------------- | -------------- |
| `ligand-efficiency.bei` | `ligand-efficiency-bei` | Extract scalar |
| `ligand-efficiency.le`  | `ligand-efficiency-le`  | Extract scalar |
| `ligand-efficiency.lle` | `ligand-efficiency-lle` | Extract scalar |
| `ligand-efficiency.sei` | `ligand-efficiency-sei` | Extract scalar |
| `activity-properties`   | `activity-properties`   | JSON string    |

### 4.4. Content Hash Specification

```python
# Fields included in hash (primary activity data)
hash-fields = [
    "activity-id",
    "assay-id",
    "molecule-id",
    "target-id",
    "standard-type",
    "standard-relation",
    "standard-value",
    "standard-units",
    "pchembl-value",
    "data-validity-comment",
]

# Fields EXCLUDED from hash
excluded = [
    "-ingestion-ts",
    "-run-id",
    "-run-type",
    "-dq-*",
    # Denormalized fields (can change independently)
    "molecule-pref-name",
    "target-pref-name",
    "assay-description",
]

# Algorithm
content-hash = sha256(f"chembl{canonical-json(filtered-record)}")
```

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver layer."""

    # === Primary Key ===
    activity-id: Series[str] = pa.Field(nullable=False)

    # === Foreign Keys ===
    assay-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )
    molecule-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )
    target-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CHEMBL\d+$",
    )
    publication-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^CHEMBL\d+$",
    )

    # === Standardized Values ===
    standard-relation: Series[str] | None = pa.Field(
        nullable=True,
        isin=["=", "<", "<=", ">", ">="],
    )
    standard-value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
    )
    standard-units: Series[str] | None = pa.Field(nullable=True)
    standard-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "IC50",
            "EC50",
            "Ki",
            "Kd",
            "AC50",
            "GI50",
            "Potency",
            "Inhibition",
            "% Inhibition",
            "Activity",
            "Ratio",
            "ED50",
            "ID50",
        ],
    )
    standard-flag: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
    )

    # === Derived Metrics ===
    pchembl-value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=14,
    )

    # === Comments & Quality ===
    data-validity-comment: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "Potential missing data",
            "Potential author error",
            "Manually validated",
            "Potential transcription error",
            "Outside typical range",
            "Non standard unit for type",
            "Author confirmed error",
        ],
    )
    activity-comment: Series[str] | None = pa.Field(nullable=True)
    potential-duplicate: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
    )

    # === Ontologies ===
    bao-endpoint: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=r"^BAO:\d+$",
    )

    # === Flattened Ligand Efficiency ===
    ligand-efficiency-bei: Series[float] | None = pa.Field(nullable=True)
    ligand-efficiency-le: Series[float] | None = pa.Field(nullable=True)
    ligand-efficiency-lle: Series[float] | None = pa.Field(nullable=True)
    ligand-efficiency-sei: Series[float] | None = pa.Field(nullable=True)

    # === Denormalized Fields ===
    canonical-smiles: Series[str] | None = pa.Field(nullable=True)
    molecule-pref-name: Series[str] | None = pa.Field(nullable=True)
    target-pref-name: Series[str] | None = pa.Field(nullable=True)
    target-organism: Series[str] | None = pa.Field(nullable=True)
    assay-type: Series[str] | None = pa.Field(nullable=True)
    assay-description: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field               | Type  | Nullable | Constraints                    | DQ Level |
| ------------------- | ----- | -------- | ------------------------------ | -------- |
| `activity-id`       | str   | No       | unique                         | CRITICAL |
| `assay-id`          | str   | No       | regex `^CHEMBL\d+$`            | CRITICAL |
| `molecule-id`       | str   | No       | regex `^CHEMBL\d+$`            | CRITICAL |
| `target-id`         | str   | Yes      | regex `^CHEMBL\d+$`            | WARNING  |
| `standard-value`    | float | Yes      | >= 0                           | WARNING  |
| `pchembl-value`     | float | Yes      | [0, 14]                        | WARNING  |
| `standard-type`     | str   | Yes      | isin [...]                     | WARNING  |
| `standard-relation` | str   | Yes      | isin ["=","\<","\<=",">",">="] | WARNING  |

### 5.3. Cross-Field Validation Rules

| Rule Name                    | Fields                                | Condition                                   | Failure Action |
| ---------------------------- | ------------------------------------- | ------------------------------------------- | -------------- |
| `value-relation-consistency` | `standard-value`, `standard-relation` | If relation is "=" then upper-value is null | Warning        |
| `pchembl-type-consistency`   | `pchembl-value`, `standard-type`      | pChEMBL only for binding types              | Warning        |

### 5.4. DQ Thresholds

| Threshold           | Value                              | Action            |
| ------------------- | ---------------------------------- | ----------------- |
| Soft                | 5%                                 | Warning, continue |
| Hard                | 20%                                | Fail batch        |
| Critical field null | activity-id, assay-id, molecule-id | Fail immediately  |

----------------------------------------------------------------------

## 6. Output Schemas

### 6.1. Bronze

```
Path: bronze/v1/chembl/activity/{YYYY-MM-DD}/
Format: JSONL + zstd
Mode: Append-only
Retention: 90 days → Archive
```

### 6.2. Silver

```
Path: silver/chembl/activity/
Format: Delta Lake (delta-rs)
Mode: Merge on [activity-id]
Partition: None
Retention: Permanent
```

### 6.3. Gold

```
Path: gold/chembl/activity/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filters:**

- `standard-type IN ('IC50', 'Ki')` — Focus on binding data
- `standard-units IN ('nM', 'uM', 'mM', 'pM', 'M', 'ug.mL-1', 'mg.kg-1')` — 7 standardized units
- `standard-relation = '='` — Exact measurements
- `target-id IS NOT NULL` — Target required

----------------------------------------------------------------------

## 7. Dependencies

### 7.1. Upstream

| Dependency        | Type     | Required    |
| ----------------- | -------- | ----------- |
| ChEMBL API        | API      | Yes         |
| `chembl_assay`    | Pipeline | Recommended |
| `chembl_molecule` | Pipeline | Recommended |
| `chembl_target`   | Pipeline | Recommended |

### 7.2. Downstream

| Consumer              | Impact                  |
| --------------------- | ----------------------- |
| SAR analytics         | Activity-based analysis |
| ML training datasets  | Bioactivity prediction  |
| Target prioritization | Druggability assessment |

----------------------------------------------------------------------

## 8. Pipeline Configuration

```yaml
# configs/entities/chembl/activity.yaml

pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"

primary_keys: ["activity-id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

gold_filters:
  columns:
    standard-type: [IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50]
    standard-units: [nM, uM, mM, pM, M, ug.mL-1, mg.kg-1]
    standard-relation: ["="]
  ranges:
    standard-value:
      min: 0
      include-min: false
  required_fields:
    - standard-type
    - standard-value
    - standard-units
    - target-id

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["activity-id"]
    partition_by: []
  gold:
    path: "data/output/gold"

input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target-id"
  filter_field: "target-id"
  batch_size: 20
```

----------------------------------------------------------------------

## 9. Testing Requirements

- [x] Unit tests for all normalizations
- [x] Validation of pchembl-value range
- [x] VCR integration tests
- [x] Architecture compliance tests
