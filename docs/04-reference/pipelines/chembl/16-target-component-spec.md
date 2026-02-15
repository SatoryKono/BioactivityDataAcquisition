# ChEMBL Target Component Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.18*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_target_component` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | target_component |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/target_component` |

---

## 2. Business Context

### 2.1. Entity Purpose

Target Components are the individual proteins, DNA, or RNA sequences that make up a ChEMBL Target (especially for complexes).

---

## 3. Validation (Gold Layer)

### 3.1. Pandera Schema

```python
class ChEMBLTargetComponentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target Component in Gold layer."""

    component_id: Series[float] = pa.Field(nullable=False, coerce=True)
    accession: Series[str] = pa.Field(nullable=True)
    component_type: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(nullable=True, coerce=True)
```
