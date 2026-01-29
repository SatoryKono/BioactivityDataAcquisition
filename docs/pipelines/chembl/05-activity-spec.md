# ChEMBL Activity Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.15*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_activity` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | activity |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/activity` |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None (polite usage recommended) |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Activities are the **core measurement data** in ChEMBL, representing bioactivity measurements of molecules against biological targets:

- **Bioactivity measurements**: IC50, Ki, EC50, potency, inhibition
- **Structure-Activity Relationships (SAR)**: Connect molecules to targets via measured values
- **Drug discovery data**: Quantitative data from screening and assays
- **Data quality tracking**: Standardized values with quality annotations

### 2.2. Use Cases

1. **SAR Analysis**: Analyze activity profiles for lead compounds
2. **Target Druggability**: Assess targets by activity data availability
3. **Compound Ranking**: Rank molecules by pChEMBL value
4. **Data Quality Assessment**: Filter by standardization and validity flags
5. **Literature Mining**: Link activities to source publications

### 2.3. Entity Relationships

```
activity
    │
    ├──FK──► assay.assay_chembl_id (M:1, required)
    │
    ├──FK──► molecule.molecule_chembl_id (M:1, required)
    │
    ├──FK──► target.target_chembl_id (M:1, optional)
    │
    ├──FK──► document.document_chembl_id (M:1, optional)
    │
    └── ligand_efficiency (nested object)
        ├── bei, le, lle, sei
```

### 2.4. Load Strategy

| Parameter | Value |
|-----------|-------|
| **Strategy** | `incremental` with input filter |
| **Watermark Field** | N/A (filtered by assay/molecule/target IDs) |
| **Estimated Volume** | ~20M records total |
| **Batch Size** | 20 (filter batch) |

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from chembl_webresource_client.new_client import new_client

activity = new_client.activity
# Filter by target, molecule, or assay
results = activity.filter(target_chembl_id__in=target_ids)
```

### 3.2. Complete API Fields

| # | API Field | JSON Type | Nullable | Description | Example |
|---|-----------|-----------|----------|-------------|---------|
| 1 | `activity_id` | integer | No | Primary key | `12345678` |
| 2 | `assay_chembl_id` | string | No | FK to assay | `"CHEMBL123456"` |
| 3 | `molecule_chembl_id` | string | No | FK to molecule | `"CHEMBL25"` |
| 4 | `target_chembl_id` | string | Yes | FK to target | `"CHEMBL240"` |
| 5 | `document_chembl_id` | string | Yes | FK to document | `"CHEMBL1234"` |
| 6 | `standard_type` | string | Yes | Measurement type | `"IC50"` |
| 7 | `standard_relation` | string | Yes | Relation | `"="` |
| 8 | `standard_value` | number | Yes | Standardized value | `50.0` |
| 9 | `standard_units` | string | Yes | Standardized units | `"nM"` |
| 10 | `standard_flag` | integer | Yes | Standardized flag | `1` |
| 11 | `pchembl_value` | number | Yes | -log10 molar | `7.3` |
| 12 | `data_validity_comment` | string | Yes | DQ comment | `"Potential author error"` |
| 13 | `activity_comment` | string | Yes | Text comment | `"Active"` |
| 14 | `potential_duplicate` | integer | Yes | Duplicate flag | `0` |
| 15 | `type` | string | Yes | Original type | `"IC50"` |
| 16 | `relation` | string | Yes | Original relation | `"="` |
| 17 | `value` | number | Yes | Original value | `50.0` |
| 18 | `units` | string | Yes | Original units | `"nM"` |
| 19 | `text_value` | string | Yes | Text value | `"Active"` |
| 20 | `standard_text_value` | string | Yes | Std text value | `"Active"` |
| 21 | `upper_value` | number | Yes | Upper bound | `100.0` |
| 22 | `standard_upper_value` | number | Yes | Std upper bound | `100.0` |
| 23 | `src_id` | integer | Yes | Source ID | `1` |
| 24 | `record_id` | integer | Yes | FK compound_record | `12345` |
| 25 | `toid` | integer | Yes | Test Occasion ID | `1` |
| 26 | `bao_endpoint` | string | Yes | BAO endpoint ID | `"BAO:0000190"` |
| 27 | `uo_units` | string | Yes | UO units ID | `"UO:0000065"` |
| 28 | `qudt_units` | string | Yes | QUDT units | `"nM"` |
| 29 | `ligand_efficiency` | object | Yes | Efficiency metrics | JSON |
| 30 | `activity_properties` | array | Yes | Properties | JSON |

### 3.3. Nested Structure: ligand_efficiency

| Field | Type | Description |
|-------|------|-------------|
| `bei` | float | Binding Efficiency Index |
| `le` | float | Ligand Efficiency |
| `lle` | float | Lipophilic Ligand Efficiency |
| `sei` | float | Surface Efficiency Index |

### 3.4. Denormalized Fields (from related entities)

The API also returns denormalized fields from related entities:

| Field | Source Entity | Description |
|-------|---------------|-------------|
| `canonical_smiles` | molecule.structures | SMILES string |
| `molecule_pref_name` | molecule | Molecule name |
| `parent_molecule_chembl_id` | molecule.hierarchy | Parent molecule |
| `target_pref_name` | target | Target name |
| `target_organism` | target | Organism |
| `target_tax_id` | target | Taxonomy ID |
| `assay_type` | assay | Assay type |
| `assay_description` | assay | Description |
| `bao_format` | assay | BAO format |
| `bao_label` | assay | BAO label |
| `document_journal` | document | Journal |
| `document_year` | document | Year |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `activity_id` |
| **ID Source** | `from_api` |
| **Format** | Integer (cast to string) |

### 4.2. Field Normalization

| Field | Normalization | Before | After |
|-------|---------------|--------|-------|
| `activity_id` | Cast to string | `12345678` | `"12345678"` |
| `standard_value` | round(10) | `50.123456789012` | `50.1234567890` |
| `pchembl_value` | round(2) | `7.3456` | `7.35` |
| `standard_relation` | Validate isin | `"="` | `"="` |
| `standard_units` | strip() | `" nM "` | `"nM"` |

### 4.3. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `ligand_efficiency.bei` | `ligand_efficiency_bei` | Extract scalar |
| `ligand_efficiency.le` | `ligand_efficiency_le` | Extract scalar |
| `ligand_efficiency.lle` | `ligand_efficiency_lle` | Extract scalar |
| `ligand_efficiency.sei` | `ligand_efficiency_sei` | Extract scalar |
| `activity_properties` | `activity_properties` | JSON string |

### 4.4. Content Hash Specification

```python
# Fields included in hash (primary activity data)
hash_fields = [
    "activity_id",
    "assay_chembl_id",
    "molecule_chembl_id",
    "target_chembl_id",
    "standard_type",
    "standard_relation",
    "standard_value",
    "standard_units",
    "pchembl_value",
    "data_validity_comment",
]

# Fields EXCLUDED from hash
excluded = [
    "_ingestion_ts", "_run_id", "_run_type", "_dq_*",
    # Denormalized fields (can change independently)
    "molecule_pref_name", "target_pref_name", "assay_description",
]

# Algorithm
content_hash = sha256(f"chembl{canonical_json(filtered_record)}")
```

---

## 5. Validation

### 5.1. Pandera Schema

```python
class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver layer."""

    # === Primary Key ===
    activity_id: Series[str] = pa.Field(nullable=False)

    # === Foreign Keys ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )
    target_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
    )
    document_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
    )

    # === Standardized Values ===
    standard_relation: Series[str] | None = pa.Field(
        nullable=True,
        isin=["=", "<", "<=", ">", ">="],
    )
    standard_value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
    )
    standard_units: Series[str] | None = pa.Field(nullable=True)
    standard_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "IC50", "EC50", "Ki", "Kd", "AC50", "GI50",
            "Potency", "Inhibition", "% Inhibition", "Activity",
            "Ratio", "ED50", "ID50",
        ],
    )
    standard_flag: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
    )

    # === Derived Metrics ===
    pchembl_value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=14,
    )

    # === Comments & Quality ===
    data_validity_comment: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "Potential missing data", "Potential author error",
            "Manually validated", "Potential transcription error",
            "Outside typical range", "Non standard unit for type",
            "Author confirmed error",
        ],
    )
    activity_comment: Series[str] | None = pa.Field(nullable=True)
    potential_duplicate: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
    )

    # === Ontologies ===
    bao_endpoint: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
    )

    # === Flattened Ligand Efficiency ===
    ligand_efficiency_bei: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_le: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_lle: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_sei: Series[float] | None = pa.Field(nullable=True)

    # === Denormalized Fields ===
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    molecule_pref_name: Series[str] | None = pa.Field(nullable=True)
    target_pref_name: Series[str] | None = pa.Field(nullable=True)
    target_organism: Series[str] | None = pa.Field(nullable=True)
    assay_type: Series[str] | None = pa.Field(nullable=True)
    assay_description: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field | Type | Nullable | Constraints | DQ Level |
|-------|------|----------|-------------|----------|
| `activity_id` | str | No | unique | CRITICAL |
| `assay_chembl_id` | str | No | regex `^CHEMBL\d+$` | CRITICAL |
| `molecule_chembl_id` | str | No | regex `^CHEMBL\d+$` | CRITICAL |
| `target_chembl_id` | str | Yes | regex `^CHEMBL\d+$` | WARNING |
| `standard_value` | float | Yes | >= 0 | WARNING |
| `pchembl_value` | float | Yes | [0, 14] | WARNING |
| `standard_type` | str | Yes | isin [...] | WARNING |
| `standard_relation` | str | Yes | isin ["=","<","<=",">",">="] | WARNING |

### 5.3. Cross-Field Validation Rules

| Rule Name | Fields | Condition | Failure Action |
|-----------|--------|-----------|----------------|
| `value_relation_consistency` | `standard_value`, `standard_relation` | If relation is "=" then upper_value is null | Warning |
| `pchembl_type_consistency` | `pchembl_value`, `standard_type` | pChEMBL only for binding types | Warning |

### 5.4. DQ Thresholds

| Threshold | Value | Action |
|-----------|-------|--------|
| Soft | 5% | Warning, continue |
| Hard | 20% | Fail batch |
| Critical field null | activity_id, assay_chembl_id, molecule_chembl_id | Fail immediately |

---

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
Mode: Merge on [activity_id]
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
- `standard_type IN ('IC50', 'Ki')` — Focus on binding data
- `standard_units = 'nM'` — Normalized units
- `standard_relation = '='` — Exact measurements
- `target_chembl_id IS NOT NULL` — Target required

---

## 7. Dependencies

### 7.1. Upstream

| Dependency | Type | Required |
|------------|------|----------|
| ChEMBL API | API | Yes |
| `chembl_assay` | Pipeline | Recommended |
| `chembl_molecule` | Pipeline | Recommended |
| `chembl_target` | Pipeline | Recommended |

### 7.2. Downstream

| Consumer | Impact |
|----------|--------|
| SAR analytics | Activity-based analysis |
| ML training datasets | Bioactivity prediction |
| Target prioritization | Druggability assessment |

---

## 8. Pipeline Configuration

```yaml
# configs/pipelines/chembl/activity.yaml

pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.1.0"

primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

gold_filters:
  columns:
    standard_type: [IC50, Ki]
    standard_units: [nM]
    standard_relation: ["="]
  ranges:
    standard_value:
      min: 0
      include_min: false
  required_fields:
    - standard_type
    - standard_value
    - standard_units
    - target_chembl_id

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["activity_id"]
    partition_by: []
  gold:
    path: "data/output/gold"

input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target_chembl_id"
  filter_field: "target_chembl_id"
  batch_size: 20
```

---

## 9. Testing Requirements

- [x] Unit tests for all normalizations
- [x] Validation of pchembl_value range
- [x] VCR integration tests
- [x] Architecture compliance tests
