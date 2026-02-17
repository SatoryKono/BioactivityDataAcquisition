# ChEMBL Publication Similarity Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.20*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_publication_similarity` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | publication_similarity |

---

## 2. Business Context

### 2.1. Entity Purpose

Represents similarity between two ChEMBL documents based on Tanimoto coefficients (using common compounds or targets).

---

## 3. Validation (Gold Layer)

### 3.1. Pandera Schema

```python
class ChEMBLDocumentSimilarityGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Similarity in Gold layer."""

    sim_id: Series[float] = pa.Field(nullable=False, coerce=True)
    doc_1: Series[float] = pa.Field(nullable=False, coerce=True)
    doc_2: Series[float] = pa.Field(nullable=False, coerce=True)
    tid_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
    mol_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
```
