# ChEMBL Publication Term Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.18*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_publication_term` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | publication_term |

---

## 2. Business Context

### 2.1. Entity Purpose

Normalized terms (like MeSH keywords) associated with ChEMBL publications.

---

## 3. Validation (Gold Layer)

### 3.1. Pandera Schema

```python
class ChEMBLDocumentTermGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Term in Gold layer."""

    document_chembl_id: Series[str] = pa.Field(nullable=False)
    term: Series[str] = pa.Field(nullable=False)
    term_type: Series[str] = pa.Field(nullable=False)
    mesh_id: Series[str] = pa.Field(nullable=True)
```
