# ChEMBL Target Component Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.21*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                                    |
| ---------------- | -------------------------------------------------------- |
| **Pipeline ID**  | `chembl_target_component`                                |
| **Provider**     | ChEMBL (EBI)                                             |
| **Entity**       | target-component                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/target-component` |
| **Library**      | `chembl-webresource-client`                              |
| **Rate Limit**   | None                                                     |
| **Health Check** | `/chembl/api/data/status.json`                           |
| **Auth Type**    | None (public API)                                        |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Target Components represent **subunits of biological targets**:

- **Protein subunits**: Individual proteins in a complex
- **UniProt mapping**: Direct link to UniProt accessions
- **Sequence data**: Amino acid sequences
- **Stoichiometry**: Component ratios in complexes

### 2.2. Use Cases

1. **UniProt Integration**: Map ChEMBL targets to UniProt
1. **Complex Analysis**: Understand multi-protein targets
1. **Sequence Analysis**: Access protein sequences
1. **Cross-Database Linking**: Bridge to UniProt annotations

### 2.3. Entity Relationships

```
target-component
    │
    ├──FK──► target.tid (M:1)
    │
    ├──FK──► component-sequences.component-id (M:1)
    │
    └──► uniprot.accession (via accession field)
```

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| #   | API Field       | Type   | Nullable | Description               |
| --- | --------------- | ------ | -------- | ------------------------- |
| 1   | `targcomp-id`   | int    | No       | Primary key               |
| 2   | `tid`           | int    | No       | FK to target              |
| 3   | `component-id`  | int    | No       | FK to component-sequences |
| 4   | `relationship`  | string | Yes      | Relationship type         |
| 5   | `stoichiometry` | int    | Yes      | Stoichiometry             |
| 6   | `homologue`     | int    | Yes      | Homologue flag            |

----------------------------------------------------------------------

## 4. Validation

### 4.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class TargetComponentSchema(ETLRecordSchema):
    """Target Component validation schema for Silver layer."""

    # === Primary Key ===
    targcomp-id: Series[int] = pa.Field(
        nullable=False,
    )

    # === Foreign Keys ===
    tid: Series[int] = pa.Field(
        nullable=False,
    )
    component-id: Series[int] = pa.Field(
        nullable=False,
    )

    # === Metadata ===
    relationship: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "SINGLE PROTEIN",
            "PROTEIN SUBUNIT",
            "RNA",
            "INTERACTING PROTEIN",
        ],
    )
    stoichiometry: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
    )
    homologue: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1, 2],
    )

    class Config:
        strict = True
        ordered = True
        coerce = True
```

----------------------------------------------------------------------

## 5. Cross-Provider Mapping

| This Entity Field            | Maps To | Provider | Field       |
| ---------------------------- | ------- | -------- | ----------- |
| UniProt accession (via join) | UniProt | UniProt  | `accession` |

----------------------------------------------------------------------

## 6. Pipeline Configuration

```yaml
pipeline-name: chembl_target_component
provider: chembl
entity-type: target-component
version: "1.2.0"

primary-keys: ["targcomp-id"]
silver-table: "chembl_target_component"
gold-table: "chembl_target_component"

gold-filters:
  required-fields:
    - tid
    - component-id

input-filter:
  enabled: true
  source-path: "data/input/target.csv"
  column-name: "target-id"
  filter-field: "target-id"
  batch-size: 20
```
