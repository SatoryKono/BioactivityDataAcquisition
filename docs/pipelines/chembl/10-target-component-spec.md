# ChEMBL Target Component Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.10*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_target_component` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | target_component |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/target_component` |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Target Components represent **subunits of biological targets**:

- **Protein subunits**: Individual proteins in a complex
- **UniProt mapping**: Direct link to UniProt accessions
- **Sequence data**: Amino acid sequences
- **Stoichiometry**: Component ratios in complexes

### 2.2. Use Cases

1. **UniProt Integration**: Map ChEMBL targets to UniProt
2. **Complex Analysis**: Understand multi-protein targets
3. **Sequence Analysis**: Access protein sequences
4. **Cross-Database Linking**: Bridge to UniProt annotations

### 2.3. Entity Relationships

```
target_component
    │
    ├──FK──► target.tid (M:1)
    │
    ├──FK──► component_sequences.component_id (M:1)
    │
    └──► uniprot.accession (via accession field)
```

---

## 3. Extraction (Bronze Layer)

### 3.1. API Fields

| # | API Field | Type | Nullable | Description |
|---|-----------|------|----------|-------------|
| 1 | `targcomp_id` | int | No | Primary key |
| 2 | `tid` | int | No | FK to target |
| 3 | `component_id` | int | No | FK to component_sequences |
| 4 | `relationship` | string | Yes | Relationship type |
| 5 | `stoichiometry` | int | Yes | Stoichiometry |
| 6 | `homologue` | int | Yes | Homologue flag |

---

## 4. Validation

### 4.1. Pandera Schema

```python
class TargetComponentSchema(ETLRecordSchema):
    """Target Component validation schema for Silver layer."""

    # === Primary Key ===
    targcomp_id: Series[int] = pa.Field(
        nullable=False,
    )

    # === Foreign Keys ===
    tid: Series[int] = pa.Field(
        nullable=False,
    )
    component_id: Series[int] = pa.Field(
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

---

## 5. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| UniProt accession (via join) | UniProt | UniProt | `accession` |

---

## 6. Pipeline Configuration

```yaml
pipeline_name: chembl_target_component
provider: chembl
entity_type: target_component
version: "1.1.0"

primary_keys: ["targcomp_id"]
silver_table: "chembl_target_component"
gold_table: "chembl_target_component"

gold_filters:
  required_fields:
    - tid
    - component_id

input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target_chembl_id"
  filter_field: "target_chembl_id"
  batch_size: 20
```
