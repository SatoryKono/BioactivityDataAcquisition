# ChEMBL Assay Parameters Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.17*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_assay_parameters` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | assay_parameters |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/assay` (nested) |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Assay Parameters describe **experimental conditions** for assays:

- **Concentrations**: Compound concentrations used
- **Time points**: Incubation times
- **Conditions**: pH, temperature, media
- **Controls**: Reference compounds

### 2.2. Use Cases

1. **Protocol Reproducibility**: Understand exact experimental conditions
2. **Condition Filtering**: Find assays with specific parameters
3. **Standardization**: Compare normalized vs original values
4. **Quality Control**: Validate experimental setups

### 2.3. Entity Relationships

```
assay_parameters
    │
    └──FK──► assay.assay_chembl_id (M:1)
```

---

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| # | API Field | Type | Nullable | Description |
|---|-----------|------|----------|-------------|
| 1 | `assay_param_id` | int | No | Primary key |
| 2 | `assay_chembl_id` | string | No | FK to assay |
| 3 | `type` | string | No | Parameter type |
| 4 | `relation` | string | Yes | Relation operator |
| 5 | `value` | float | Yes | Numeric value |
| 6 | `units` | string | Yes | Original units |
| 7 | `text_value` | string | Yes | Text value |
| 8 | `comments` | string | Yes | Comments |
| 9 | `standard_type` | string | Yes | Standardized type |
| 10 | `standard_relation` | string | Yes | Standardized relation |
| 11 | `standard_value` | float | Yes | Standardized value |
| 12 | `standard_units` | string | Yes | Standardized units |
| 13 | `standard_text_value` | string | Yes | Standardized text |

---

## 4. Validation

### 4.1. Pandera Schema

```python
class AssayParametersSchema(ETLRecordSchema):
    """AssayParameters validation schema for Silver layer."""

    # === Primary Key ===
    assay_param_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Foreign Key ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )

    # === Parameter Type ===
    type: Series[str] = pa.Field(nullable=False)

    # === Raw Values ===
    relation: Series[str] | None = pa.Field(nullable=True)
    value: Series[float] | None = pa.Field(nullable=True)
    units: Series[str] | None = pa.Field(nullable=True)
    text_value: Series[str] | None = pa.Field(nullable=True)
    comments: Series[str] | None = pa.Field(nullable=True)

    # === Standardized Values ===
    standard_type: Series[str] | None = pa.Field(nullable=True)
    standard_relation: Series[str] | None = pa.Field(nullable=True)
    standard_value: Series[float] | None = pa.Field(nullable=True)
    standard_units: Series[str] | None = pa.Field(nullable=True)
    standard_text_value: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

---

## 5. Pipeline Configuration

```yaml
pipeline_name: chembl_assay_parameters
provider: chembl
entity_type: assay_parameters
version: "1.1.0"

primary_keys: ["assay_param_id"]
silver_table: "chembl_assay_parameters"
gold_table: "chembl_assay_parameters"

gold_filters:
  required_fields:
    - type

input_filter:
  enabled: true
  source_path: "data/input/assay.csv"
  column_name: "assay_chembl_id"
  filter_field: "assay_chembl_id"
  batch_size: 20
```
