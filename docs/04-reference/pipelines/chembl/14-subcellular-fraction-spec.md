# ChEMBL Subcellular Fraction Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.19*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_subcellular_fraction` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | subcellular_fraction |
| **Source Entity** | assay |
| **Strategy** | Derived Entity (Extracted from Assay records) |

---

## 2. Business Context

### 2.1. Entity Purpose

Subcellular Fractions represent specific **cellular compartments** (like mitochondria, nucleus, or microsomes) used in assays:

- **Biological Context**: Normalizes compartmental data across different assays.
- **Reference Table**: Provides a unique list of fractions used in the database for filtering and analysis.

### 2.2. Use Cases

1. **Compartmental Analysis**: Study drug effects specifically on mitochondrial or microsomal enzymes.
2. **Assay Enrichment**: Group assays by the subcellular fraction used in the experiment.

---

## 3. Extraction & Transformation

This is a **derived entity** created by extracting unique values from the `assay_subcellular_fraction` field in the `chembl_assay` pipeline.

### 3.1. Fields

| # | Field | Type | Nullable | Description |
|---|-------|------|----------|-------------|
| 1 | `subcellular_fraction` | string | No | Primary key (normalized name) |
| 2 | `assay_count` | integer | Yes | Number of assays using this fraction |
| 3 | `example_assay_chembl_id` | string | Yes | Reference to an example assay |

---

## 4. Validation

### 4.1. Pandera Schema

```python
class ChEMBLSubcellularFractionGoldSchema(pa.DataFrameModel):
    """Gold schema for ChEMBL Subcellular Fraction entity."""

    # Primary key
    subcellular_fraction: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
    )

    # Statistics
    assay_count: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
    )

    # Example reference
    example_assay_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
    )

    class Config:
        strict = True
```

---

## 5. Pipeline Configuration

```yaml
pipeline_name: chembl_subcellular_fraction
provider: chembl
entity_type: subcellular_fraction
version: "1.0.0"

primary_keys: ["subcellular_fraction"]
silver_table: "chembl_subcellular_fraction"
gold_table: "chembl_subcellular_fraction"
```
