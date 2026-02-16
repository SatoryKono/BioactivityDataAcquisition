# ChEMBL Target Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.19*

______________________________________________________________________

## 1. Identification

| Parameter        | Value                                          |
| ---------------- | ---------------------------------------------- |
| **Pipeline ID**  | `chembl_target`                                |
| **Provider**     | ChEMBL (EBI)                                   |
| **Entity**       | target                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/target` |
| **Library**      | `chembl_webresource_client`                    |
| **Rate Limit**   | None (polite usage recommended)                |
| **Health Check** | `/chembl/api/data/status`                      |
| **Auth Type**    | None (public API)                              |

______________________________________________________________________

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
    ├──◄──FK──activity.target_chembl_id (1:M)
    │
    ├──◄──FK──assay.target_chembl_id (1:M)
    │
    └── target_components (nested array)
        ├── component_id
        ├── accession (UniProt)
        └── component_type
```

### 2.4. Load Strategy

| Parameter            | Value                           |
| -------------------- | ------------------------------- |
| **Strategy**         | `incremental` with input filter |
| **Watermark Field**  | N/A                             |
| **Estimated Volume** | ~15,000 records total           |
| **Batch Size**       | 20 (filter batch)               |

______________________________________________________________________

## 3. Extraction (Bronze Layer)

### 3.1. Complete API Fields

| #   | API Field            | JSON Type | Nullable | Nested | Description         |
| --- | -------------------- | --------- | -------- | ------ | ------------------- |
| 1   | `target_chembl_id`   | string    | No       | -      | Primary key         |
| 2   | `target_type`        | string    | Yes      | -      | Type classification |
| 3   | `pref_name`          | string    | Yes      | -      | Preferred name      |
| 4   | `organism`           | string    | Yes      | -      | Organism name       |
| 5   | `tax_id`             | integer   | Yes      | -      | NCBI Taxonomy ID    |
| 6   | `species_group_flag` | boolean   | Yes      | -      | Species group flag  |
| 7   | `downgraded`         | boolean   | Yes      | -      | Deprecated flag     |
| 8   | `target_components`  | array     | Yes      | Yes    | Component list      |
| 9   | `cross_references`   | array     | Yes      | Yes    | External refs       |

### 3.2. Nested Structure: target_components

| Field                   | Type    | Description       |
| ----------------------- | ------- | ----------------- |
| `component_id`          | integer | Component ID      |
| `component_type`        | string  | PROTEIN/DNA/RNA   |
| `accession`             | string  | UniProt accession |
| `component_description` | string  | Description       |
| `relationship`          | string  | Relationship type |

______________________________________________________________________

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `target_chembl_id`       |
| **ID Source**       | `from_api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Flattening Strategy

| Nested Path                           | Flattened Name         | Strategy     |
| ------------------------------------- | ---------------------- | ------------ |
| `target_components[*].accession`      | `component_accessions` | Extract list |
| `target_components[*].component_id`   | `component_ids`        | Extract list |
| `target_components[*].component_type` | `component_types`      | Extract list |
| `target_components`                   | `target_components`    | JSON string  |
| `cross_references`                    | `cross_references`     | JSON string  |

______________________________________________________________________

## 5. Validation

### 5.1. Pandera Schema

```python
class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Identifiers ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
    )

    # === Classification ===
    target_type: Series[str] | None = pa.Field(
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
    pref_name: Series[str] | None = pa.Field(nullable=True)
    tax_id: Series[int] | None = pa.Field(nullable=True)
    organism: Series[str] | None = pa.Field(nullable=True)
    species_group_flag: Series[bool] | None = pa.Field(nullable=True)
    downgraded: Series[bool] | None = pa.Field(nullable=True)

    # === Complex Fields ===
    target_components: Series[str] | None = pa.Field(nullable=True)
    cross_references: Series[str] | None = pa.Field(nullable=True)

    # === Flattened Lists ===
    component_accessions: Series[object] | None = pa.Field(nullable=True)
    component_ids: Series[object] | None = pa.Field(nullable=True)
    component_types: Series[object] | None = pa.Field(nullable=True)
    component_relationships: Series[object] | None = pa.Field(nullable=True)
    component_descriptions: Series[object] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field              | Type | Nullable | Constraints         | DQ Level |
| ------------------ | ---- | -------- | ------------------- | -------- |
| `target_chembl_id` | str  | No       | regex `^CHEMBL\d+$` | CRITICAL |
| `target_type`      | str  | Yes      | isin [...]          | WARNING  |
| `tax_id`           | int  | Yes      | >= 1                | WARNING  |
| `organism`         | str  | Yes      | -                   | INFO     |

______________________________________________________________________

## 6. Dependencies

### 6.1. Cross-Provider Mapping

| This Entity Field         | Maps To            | Provider | Field       |
| ------------------------- | ------------------ | -------- | ----------- |
| `component_accessions[*]` | UniProt            | UniProt  | `accession` |
| `target_chembl_id`        | UniProt ID Mapping | UniProt  | `from_id`   |

______________________________________________________________________

## 7. Pipeline Configuration

```yaml
pipeline_name: chembl_target
provider: chembl
entity_type: target
version: "1.2.0"

primary_keys: ["target_chembl_id"]
silver_table: "chembl_target"
gold_table: "chembl_target"

gold_filters:
  required_fields:
    - pref_name
  columns:
    downgraded: [false]

input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target_chembl_id"
  filter_field: "target_chembl_id"
  batch_size: 20
```
