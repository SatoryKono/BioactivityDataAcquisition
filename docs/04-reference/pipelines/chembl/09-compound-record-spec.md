# ChEMBL Compound Record Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.21*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                                   |
| ---------------- | ------------------------------------------------------- |
| **Pipeline ID**  | `chembl_compound_record`                                |
| **Provider**     | ChEMBL (EBI)                                            |
| **Entity**       | compound-record                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/compound-record` |
| **Library**      | `chembl-webresource-client`                             |
| **Rate Limit**   | None                                                    |
| **Health Check** | `/chembl/api/data/status.json`                          |
| **Auth Type**    | None (public API)                                       |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Compound Records link **molecules to publications** with original naming:

- **Data provenance**: Connect molecules to source documents
- **Original naming**: Preserve compound names from publications
- **Source tracking**: Track data source databases
- **Literature references**: Enable citation-based analysis

### 2.2. Use Cases

1. **Compound Name Resolution**: Find molecules by literature names
1. **Publication Mining**: Find all compounds mentioned in a paper
1. **Source Attribution**: Track data provenance
1. **Name Normalization**: Map publication names to ChEMBL IDs

### 2.3. Entity Relationships

```
compound-record
    │
    ├──FK──► molecule.molecule-id (M:1)
    │
    ├──FK──► document.publication-id (M:1)
    │
    └──◄──FK──activity.record-id (1:M)
```

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| #   | API Field         | Type   | Nullable | Description               |
| --- | ----------------- | ------ | -------- | ------------------------- |
| 1   | `record-id`       | int    | No       | Primary key               |
| 2   | `molecule-id`     | string | No       | FK to molecule            |
| 3   | `publication-id`  | string | No       | FK to document            |
| 4   | `src-id`          | int    | No       | Source ID                 |
| 5   | `compound-key`    | string | Yes      | Compound key in document  |
| 6   | `compound-name`   | string | Yes      | Compound name in document |
| 7   | `src-compound-id` | string | Yes      | Source compound ID        |

----------------------------------------------------------------------

## 4. Validation

### 4.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class CompoundRecordSchema(ETLRecordSchema):
    """Compound Record validation schema for Silver layer."""

    # === Primary Key ===
    record-id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Foreign Keys ===
    molecule-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )
    publication-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )
    src-id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Source-specific Identifiers ===
    compound-key: Series[str] | None = pa.Field(nullable=True)
    compound-name: Series[str] | None = pa.Field(nullable=True)
    src-compound-id: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

----------------------------------------------------------------------

## 5. Pipeline Configuration

```yaml
pipeline-name: chembl_compound_record
provider: chembl
entity-type: compound-record
version: "1.2.0"

primary-keys: ["record-id"]
silver-table: "chembl_compound_record"
gold-table: "chembl_compound_record"

gold-filters:
  required-fields:
    - molecule-id
    - publication-id

input-filter:
  enabled: true
  source-path: "data/input/molecule.csv"
  column-name: "molecule-id"
  filter-field: "molecule-id"
  batch-size: 20
```

----------------------------------------------------------------------

## 6. Dependencies

### 6.1. Upstream

| Dependency           | Type     | Required    |
| -------------------- | -------- | ----------- |
| ChEMBL API           | API      | Yes         |
| `chembl_molecule`    | Pipeline | Recommended |
| `chembl_publication` | Pipeline | Recommended |

### 6.2. Downstream

| Consumer                     | Impact                   |
| ---------------------------- | ------------------------ |
| `chembl_activity`            | FK reference (record-id) |
| Compound-literature analysis | Provenance tracking      |
