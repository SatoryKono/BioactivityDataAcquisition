# ChEMBL Protein Class Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.19*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_protein_class` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | protein_class |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/protein_class` |
| **Library** | `chembl_webresource_client` |

---

## 2. Business Context

### 2.1. Entity Purpose

Hierarchical classification of protein targets (enzyme classes, receptor types, etc.). It allows for broad biological categorization of drug targets.

### 2.2. Relationships

```
protein_class
    │
    └──◄──FK──target_component.protein_classification_id
```

---

## 3. Validation (Gold Layer)

### 3.1. Pandera Schema

```python
class ChEMBLProteinClassGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Protein Classification in Gold layer."""

    # Primary identifier
    protein_class_id: Series[float] = pa.Field(nullable=False, ge=1, coerce=True)

    # Hierarchy
    parent_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    class_level: Series[float] = pa.Field(nullable=True, ge=1, le=8, coerce=True)

    # Classification data
    pref_name: Series[str] = pa.Field(nullable=True)
    short_name: Series[str] = pa.Field(nullable=True)
    protein_class_desc: Series[str] = pa.Field(nullable=True)
    definition: Series[str] = pa.Field(nullable=True)
```
