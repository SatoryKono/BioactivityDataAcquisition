# ChEMBL Publication Term Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.20*

______________________________________________________________________

## 1. Identification

| Parameter       | Value                     |
| --------------- | ------------------------- |
| **Pipeline ID** | `chembl_publication_term` |
| **Provider**    | ChEMBL (EBI)              |
| **Entity**      | publication_term          |

______________________________________________________________________

## 2. Business Context

### 2.1. Entity Purpose

Normalized terms (like MeSH keywords) associated with ChEMBL publications.

______________________________________________________________________

## 3. Validation (Gold Layer)

### 3.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class ChEMBLDocumentTermGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Term in Gold layer."""

    publication_id: Series[str] = pa.Field(nullable=False)
    term: Series[str] = pa.Field(nullable=False)
    term_type: Series[str] = pa.Field(nullable=False)
    mesh_id: Series[str] = pa.Field(nullable=True)
```
