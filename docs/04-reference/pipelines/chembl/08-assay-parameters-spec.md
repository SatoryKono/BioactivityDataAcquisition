# ChEMBL Assay Parameters Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.21*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                                  |
| ---------------- | ------------------------------------------------------ |
| **Pipeline ID**  | `chembl_assay_parameters`                              |
| **Provider**     | ChEMBL (EBI)                                           |
| **Entity**       | assay-parameters                                       |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/assay` (nested) |
| **Library**      | `chembl-webresource-client`                            |
| **Rate Limit**   | None                                                   |
| **Health Check** | `/chembl/api/data/status.json`                         |
| **Auth Type**    | None (public API)                                      |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Assay Parameters describe **experimental conditions** for assays:

- **Concentrations**: Compound concentrations used
- **Time points**: Incubation times
- **Conditions**: pH, temperature, media
- **Controls**: Reference compounds

### 2.2. Use Cases

1. **Protocol Reproducibility**: Understand exact experimental conditions
1. **Condition Filtering**: Find assays with specific parameters
1. **Standardization**: Compare normalized vs original values
1. **Quality Control**: Validate experimental setups

### 2.3. Entity Relationships

```
assay-parameters
    │
    └──FK──► assay.assay-id (M:1)
```

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| #   | API Field             | Type   | Nullable | Description           |
| --- | --------------------- | ------ | -------- | --------------------- |
| 1   | `assay-param-id`      | int    | No       | Primary key           |
| 2   | `assay-id`            | string | No       | FK to assay           |
| 3   | `type`                | string | No       | Parameter type        |
| 4   | `relation`            | string | Yes      | Relation operator     |
| 5   | `value`               | float  | Yes      | Numeric value         |
| 6   | `units`               | string | Yes      | Original units        |
| 7   | `text-value`          | string | Yes      | Text value            |
| 8   | `comments`            | string | Yes      | Comments              |
| 9   | `standard-type`       | string | Yes      | Standardized type     |
| 10  | `standard-relation`   | string | Yes      | Standardized relation |
| 11  | `standard-value`      | float  | Yes      | Standardized value    |
| 12  | `standard-units`      | string | Yes      | Standardized units    |
| 13  | `standard-text-value` | string | Yes      | Standardized text     |

----------------------------------------------------------------------

## 4. Validation

### 4.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class AssayParametersSchema(ETLRecordSchema):
    """AssayParameters validation schema for Silver layer."""

    # === Primary Key ===
    assay-param-id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Foreign Key ===
    assay-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )

    # === Parameter Type ===
    type: Series[str] = pa.Field(nullable=False)

    # === Raw Values ===
    relation: Series[str] | None = pa.Field(nullable=True)
    value: Series[float] | None = pa.Field(nullable=True)
    units: Series[str] | None = pa.Field(nullable=True)
    text-value: Series[str] | None = pa.Field(nullable=True)
    comments: Series[str] | None = pa.Field(nullable=True)

    # === Standardized Values ===
    standard-type: Series[str] | None = pa.Field(nullable=True)
    standard-relation: Series[str] | None = pa.Field(nullable=True)
    standard-value: Series[float] | None = pa.Field(nullable=True)
    standard-units: Series[str] | None = pa.Field(nullable=True)
    standard-text-value: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

----------------------------------------------------------------------

## 5. Pipeline Configuration

```yaml
pipeline-name: chembl_assay_parameters
provider: chembl
entity-type: assay-parameters
version: "1.2.0"

primary-keys: ["assay-param-id"]
silver-table: "chembl_assay_parameters"
gold-table: "chembl_assay_parameters"

gold-filters:
  required-fields:
    - type

input-filter:
  enabled: true
  source-path: "data/input/assay.csv"
  column-name: "assay-id"
  filter-field: "assay-id"
  batch-size: 20
```
