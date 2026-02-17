# ChEMBL Compound Record Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.20*

______________________________________________________________________

## 1. Identification

| Parameter        | Value                                                   |
| ---------------- | ------------------------------------------------------- |
| **Pipeline ID**  | `chembl_compound_record`                                |
| **Provider**     | ChEMBL (EBI)                                            |
| **Entity**       | compound_record                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/compound_record` |
| **Library**      | `chembl_webresource_client`                             |
| **Rate Limit**   | None                                                    |
| **Health Check** | `/chembl/api/data/status.json`                          |
| **Auth Type**    | None (public API)                                       |

______________________________________________________________________

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
compound_record
    │
    ├──FK──► molecule.molecule_id (M:1)
    │
    ├──FK──► document.publication_id (M:1)
    │
    └──◄──FK──activity.record_id (1:M)
```

______________________________________________________________________

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| #   | API Field         | Type   | Nullable | Description               |
| --- | ----------------- | ------ | -------- | ------------------------- |
| 1   | `record_id`       | int    | No       | Primary key               |
| 2   | `molecule_id`     | string | No       | FK to molecule            |
| 3   | `publication_id`  | string | No       | FK to document            |
| 4   | `src_id`          | int    | No       | Source ID                 |
| 5   | `compound_key`    | string | Yes      | Compound key in document  |
| 6   | `compound_name`   | string | Yes      | Compound name in document |
| 7   | `src_compound_id` | string | Yes      | Source compound ID        |

______________________________________________________________________

## 4. Validation

### 4.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class CompoundRecordSchema(ETLRecordSchema):
    """Compound Record validation schema for Silver layer."""

    # === Primary Key ===
    record_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Foreign Keys ===
    molecule_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )
    publication_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )
    src_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
    )

    # === Source-specific Identifiers ===
    compound_key: Series[str] | None = pa.Field(nullable=True)
    compound_name: Series[str] | None = pa.Field(nullable=True)
    src_compound_id: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

______________________________________________________________________

## 5. Pipeline Configuration

```yaml
pipeline_name: chembl_compound_record
provider: chembl
entity_type: compound_record
version: "1.2.0"

primary_keys: ["record_id"]
silver_table: "chembl_compound_record"
gold_table: "chembl_compound_record"

gold_filters:
  required_fields:
    - molecule_id
    - publication_id

input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "molecule_id"
  filter_field: "molecule_id"
  batch_size: 20
```

______________________________________________________________________

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
| `chembl_activity`            | FK reference (record_id) |
| Compound-literature analysis | Provenance tracking      |
