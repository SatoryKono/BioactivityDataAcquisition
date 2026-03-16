# ChEMBL Target Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.24*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                          |
| ---------------- | ---------------------------------------------- |
| **Pipeline ID**  | `chembl_target`                                |
| **Provider**     | ChEMBL (EBI)                                   |
| **Entity**       | target                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/target` |
| **Library**      | Built-in ChEMBL adapter (httpx)                    |
| **Rate Limit**   | None (polite usage recommended)                |
| **Health Check** | `/chembl/api/data/status`                      |
| **Auth Type**    | None (public API)                              |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Targets represent **biological entities** that drugs interact with:

- **Drug targets**: Proteins, protein complexes, cell lines, organisms
- **Target classification**: Single proteins, protein families, complexes
- **Species context**: Organism and taxonomy information
- **Cross-database linking**: UniProt accessions for protein targets

### 2.2. Use Cases

1. **Target Identification**: Find druggable targets for diseases
1. **Target Deconvolution**: Identify off-target effects
1. **Species Translation**: Compare targets across organisms
1. **Target Class Analysis**: Analyze druggability by target type

### 2.3. Entity Relationships

```
target
    │
    ├──◄──FK──activity.target-id (1:M)
    │
    ├──◄──FK──assay.target-id (1:M)
    │
    └── target-components (nested array)
        ├── component-id
        ├── accession (UniProt)
        └── component-type
```

### 2.4. Load Strategy

| Parameter            | Value                           |
| -------------------- | ------------------------------- |
| **Strategy**         | `incremental` with input filter |
| **Watermark Field**  | N/A                             |
| **Estimated Volume** | ~15,000 records total           |
| **Batch Size**       | 20 (filter batch)               |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. Complete API Fields

| #   | API Field            | JSON Type | Nullable | Nested | Description         |
| --- | -------------------- | --------- | -------- | ------ | ------------------- |
| 1   | `target-id`          | string    | No       | -      | Primary key         |
| 2   | `target-type`        | string    | Yes      | -      | Type classification |
| 3   | `pref-name`          | string    | Yes      | -      | Preferred name      |
| 4   | `organism`           | string    | Yes      | -      | Organism name       |
| 5   | `tax-id`             | integer   | Yes      | -      | NCBI Taxonomy ID    |
| 6   | `species-group-flag` | boolean   | Yes      | -      | Species group flag  |
| 7   | `downgraded`         | boolean   | Yes      | -      | Deprecated flag     |
| 8   | `target-components`  | array     | Yes      | Yes    | Component list      |
| 9   | `cross-references`   | array     | Yes      | Yes    | External refs       |

### 3.2. Nested Structure: target-components

| Field                   | Type    | Description       |
| ----------------------- | ------- | ----------------- |
| `component-id`          | integer | Component ID      |
| `component-type`        | string  | PROTEIN/DNA/RNA   |
| `accession`             | string  | UniProt accession |
| `component-description` | string  | Description       |
| `relationship`          | string  | Relationship type |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `target-id`              |
| **ID Source**       | `from-api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Flattening Strategy

| Nested Path                           | Flattened Name         | Strategy     |
| ------------------------------------- | ---------------------- | ------------ |
| `target-components[*].accession`      | `component-accessions` | Extract list |
| `target-components[*].component-id`   | `component-ids`        | Extract list |
| `target-components[*].component-type` | `component-types`      | Extract list |
| `target-components`                   | `target-components`    | JSON string  |
| `cross-references`                    | `cross-references`     | JSON string  |

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Identifiers ===
    target-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=r"^CHEMBL\d+$",
    )

    # === Classification ===
    target-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "SINGLE PROTEIN",
            "PROTEIN COMPLEX",
            "PROTEIN FAMILY",
            "SELECTIVITY GROUP",
            "ORGANISM",
            "TISSUE",
            "CELL-LINE",
            "SUBCELLULAR",
            "UNKNOWN",
            "CHIMERIC PROTEIN",
            "PROTEIN-PROTEIN INTERACTION",
            "NUCLEIC-ACID",
            "METAL",
            "LIPID",
            "MACROMOLECULE",
            "PHENOTYPE",
            "ADMET",
        ],  # 17 target types
    )

    # === Metadata ===
    pref-name: Series[str] | None = pa.Field(nullable=True)
    tax-id: Series[int] | None = pa.Field(nullable=True)
    organism: Series[str] | None = pa.Field(nullable=True)
    species-group-flag: Series[bool] | None = pa.Field(nullable=True)
    downgraded: Series[bool] | None = pa.Field(nullable=True)

    # === Complex Fields ===
    target-components: Series[str] | None = pa.Field(nullable=True)
    cross-references: Series[str] | None = pa.Field(nullable=True)

    # === Flattened Lists ===
    component-accessions: Series[object] | None = pa.Field(nullable=True)
    component-ids: Series[object] | None = pa.Field(nullable=True)
    component-types: Series[object] | None = pa.Field(nullable=True)
    component-relationships: Series[object] | None = pa.Field(nullable=True)
    component-descriptions: Series[object] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field         | Type | Nullable | Constraints         | DQ Level |
| ------------- | ---- | -------- | ------------------- | -------- |
| `target-id`   | str  | No       | regex `^CHEMBL\d+$` | CRITICAL |
| `target-type` | str  | Yes      | isin [...]          | WARNING  |
| `tax-id`      | int  | Yes      | >= 1                | WARNING  |
| `organism`    | str  | Yes      | -                   | INFO     |

----------------------------------------------------------------------

## 6. Dependencies

### 6.1. Cross-Provider Mapping

| This Entity Field         | Maps To            | Provider | Field       |
| ------------------------- | ------------------ | -------- | ----------- |
| `component-accessions[*]` | UniProt            | UniProt  | `accession` |
| `target-id`               | UniProt ID Mapping | UniProt  | `from-id`   |

----------------------------------------------------------------------

## 7. Pipeline Configuration

```yaml
pipeline_name: chembl_target
provider: chembl
entity_type: target
version: "1.2.0"

primary_keys: ["target-id"]
silver_table: "chembl_target"
gold_table: "chembl_target"

gold_filters:
  required_fields:
    - pref-name
  columns:
    downgraded: [false]

input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target-id"
  filter_field: "target-id"
  batch_size: 20
```
