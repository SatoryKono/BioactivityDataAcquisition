# ChEMBL Subcellular Fraction Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.20*

----------------------------------------------------------------------

## 1. Identification

| Parameter         | Value                                         |
| ----------------- | --------------------------------------------- |
| **Pipeline ID**   | `chembl-subcellular-fraction`                 |
| **Provider**      | ChEMBL (EBI)                                  |
| **Entity**        | subcellular-fraction                          |
| **Source Entity** | assay                                         |
| **Strategy**      | Derived Entity (Extracted from Assay records) |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Subcellular Fractions represent specific **cellular compartments** (like mitochondria, nucleus, or microsomes) used in assays:

- **Biological Context**: Normalizes compartmental data across different assays.
- **Reference Table**: Provides a unique list of fractions used in the database for filtering and analysis.

### 2.2. Use Cases

1. **Compartmental Analysis**: Study drug effects specifically on mitochondrial or microsomal enzymes.
1. **Assay Enrichment**: Group assays by the subcellular fraction used in the experiment.

----------------------------------------------------------------------

## 3. Extraction & Transformation

This is a **derived entity** created by extracting unique values from the `assay-subcellular-fraction` field in the `chembl-assay` pipeline.

### 3.1. Fields

| #   | Field                  | Type    | Nullable | Description                          |
| --- | ---------------------- | ------- | -------- | ------------------------------------ |
| 1   | `subcellular-fraction` | string  | No       | Primary key (normalized name)        |
| 2   | `assay-count`          | integer | Yes      | Number of assays using this fraction |
| 3   | `example-assay-id`     | string  | Yes      | Reference to an example assay        |

----------------------------------------------------------------------

## 4. Validation

### 4.1. Pandera Schema

```python
class ChEMBLSubcellularFractionGoldSchema(pa.DataFrameModel):
    """Gold schema for ChEMBL Subcellular Fraction entity."""

    # Primary key
    subcellular-fraction: Series[str] = pa.Field(
        nullable=False,
        str-length={"min-value": 1, "max-value": 200},
    )

    # Statistics
    assay-count: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
    )

    # Example reference
    example-assay-id: Series[str] | None = pa.Field(
        nullable=True,
    )

    class Config:
        strict = True
```

----------------------------------------------------------------------

## 5. Pipeline Configuration

```yaml
pipeline-name: chembl-subcellular-fraction
provider: chembl
entity-type: subcellular-fraction
version: "1.0.0"

primary-keys: ["subcellular-fraction"]
silver-table: "chembl-subcellular-fraction"
gold-table: "chembl-subcellular-fraction"
```
