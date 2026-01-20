# ChEMBL Molecule Pipeline Specification

*Version 1.1.0 | Aligned with RULES.md v5.11*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_molecule` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | molecule |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/molecule` |
| **Library** | `chembl_webresource_client` |
| **Rate Limit** | None (polite usage recommended) |
| **Health Check** | `/chembl/api/data/status.json` |
| **Auth Type** | None (public API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Molecules represent **chemical compounds** in ChEMBL with their structural and pharmacological properties:

- **Drug discovery**: Central entity linking compounds to biological activities
- **Structure-activity relationships (SAR)**: Chemical structures with activity data
- **Clinical development**: Track compounds through clinical phases
- **Cross-database linking**: InChI Key enables mapping to PubChem, DrugBank

### 2.2. Use Cases

1. **Compound Search**: Find molecules by structure, name, or properties
2. **Drug Pipeline Analysis**: Analyze compounds by clinical phase
3. **SAR Studies**: Correlate structural features with activity profiles
4. **Toxicity Screening**: Identify compounds with black box warnings
5. **Natural Product Discovery**: Filter for natural product-derived compounds

### 2.3. Entity Relationships

```
molecule
    │
    ├──◄──FK──activity.molecule_chembl_id (1:M)
    │
    ├──◄──FK──compound_record.molecule_chembl_id (1:M)
    │
    └── molecule_hierarchy (nested)
        ├── parent_chembl_id
        └── active_chembl_id
```

### 2.4. Load Strategy

| Parameter | Value |
|-----------|-------|
| **Strategy** | `incremental` with input filter |
| **Watermark Field** | N/A (filtered by input CSV) |
| **Full Load Frequency** | On demand |
| **Estimated Volume** | ~2.4M records total |
| **Batch Size** | 20 (filter batch) |

---

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from chembl_webresource_client.new_client import new_client

molecule = new_client.molecule
# Filter by input CSV molecule_chembl_ids
results = molecule.filter(molecule_chembl_id__in=chembl_ids)
```

### 3.2. Complete API Fields

| # | API Field | JSON Type | Nullable | Nested | Description | Example |
|---|-----------|-----------|----------|--------|-------------|---------|
| 1 | `molecule_chembl_id` | string | No | - | Primary key | `"CHEMBL25"` |
| 2 | `pref_name` | string | Yes | - | Preferred name | `"ASPIRIN"` |
| 3 | `molecule_type` | string | Yes | - | Type | `"Small molecule"` |
| 4 | `max_phase` | number | Yes | - | Clinical phase | `4` |
| 5 | `structure_type` | string | Yes | - | Structure type | `"MOL"` |
| 6 | `therapeutic_flag` | boolean | Yes | - | Is therapeutic | `true` |
| 7 | `oral` | boolean | Yes | - | Oral delivery | `true` |
| 8 | `parenteral` | boolean | Yes | - | Parenteral delivery | `false` |
| 9 | `topical` | boolean | Yes | - | Topical delivery | `false` |
| 10 | `black_box_warning` | integer | Yes | - | BBW flag | `0` |
| 11 | `natural_product` | integer | Yes | - | Natural product flag | `0` |
| 12 | `first_in_class` | integer | Yes | - | First in class | `0` |
| 13 | `prodrug` | integer | Yes | - | Prodrug flag | `0` |
| 14 | `inorganic_flag` | integer | Yes | - | Inorganic flag | `0` |
| 15 | `polymer_flag` | integer | Yes | - | Polymer flag | `0` |
| 16 | `first_approval` | integer | Yes | - | First approval year | `1899` |
| 17 | `withdrawn_flag` | boolean | Yes | - | Withdrawn flag | `false` |
| 18 | `molecule_hierarchy` | object | Yes | Yes | Hierarchy | JSON |
| 19 | `molecule_properties` | object | Yes | Yes | Properties | JSON |
| 20 | `molecule_structures` | object | Yes | Yes | Structures | JSON |
| 21 | `molecule_synonyms` | array | Yes | Yes | Synonyms | JSON |
| 22 | `cross_references` | array | Yes | Yes | Cross-refs | JSON |
| 23 | `atc_classifications` | array | Yes | Yes | ATC codes | JSON |

### 3.3. Nested Structure: molecule_structures

| Field | Type | Description |
|-------|------|-------------|
| `canonical_smiles` | string | Canonical SMILES |
| `standard_inchi` | string | Standard InChI |
| `standard_inchi_key` | string | Standard InChI Key (27 chars) |
| `molfile` | string | MOL file content |

### 3.4. Nested Structure: molecule_properties

| Field | Type | Description |
|-------|------|-------------|
| `molecular_formula` | string | Molecular formula |
| `full_mwt` | float | Full molecular weight |
| `mw_freebase` | float | Freebase MW |
| `mw_monoisotopic` | float | Monoisotopic MW |
| `alogp` | float | ALogP |
| `cx_logp` | float | ChemAxon LogP |
| `cx_logd` | float | ChemAxon LogD |
| `psa` | float | Polar surface area |
| `hba` | integer | H-bond acceptors |
| `hbd` | integer | H-bond donors |
| `rtb` | integer | Rotatable bonds |
| `num_ro5_violations` | integer | Rule of 5 violations |
| `aromatic_rings` | integer | Aromatic rings |
| `heavy_atoms` | integer | Heavy atoms |
| `qed_weighted` | float | QED score |

---

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter | Value |
|-----------|-------|
| **Entity ID Field** | `molecule_chembl_id` |
| **ID Source** | `from_api` |
| **Format** | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Field Normalization

| Field | Normalization | Before | After |
|-------|---------------|--------|-------|
| `molecule_chembl_id` | Validate regex | `"CHEMBL25"` | `"CHEMBL25"` |
| `pref_name` | strip().upper() | `" aspirin "` | `"ASPIRIN"` |
| `max_phase` | Cast to float | `"4"` | `4.0` |
| `structure_standard_inchi_key` | Extract from nested | `{...}` | `"BSYNRYMUTXBXSQ-..."` |
| Float properties | round(10) | `180.12345678901234` | `180.1234567890` |
| Nested objects | JSON serialize | `{...}` | `'{"key": "value"}'` |

### 4.3. Flattening Strategy

| Nested Path | Flattened Name | Strategy |
|-------------|----------------|----------|
| `molecule_structures.standard_inchi_key` | `structure_standard_inchi_key` | Extract scalar |
| `molecule_hierarchy` | `molecule_hierarchy` | JSON string |
| `molecule_properties` | `molecule_properties` | JSON string |
| `molecule_structures` | `molecule_structures` | JSON string |
| `molecule_synonyms` | `molecule_synonyms` | JSON string |
| `cross_references` | `cross_references` | JSON string |
| `atc_classifications` | `atc_classifications` | JSON string |

### 4.4. Content Hash Specification

```python
# Fields included in hash (alphabetical order)
hash_fields = [
    "atc_classifications",
    "black_box_warning",
    "cross_references",
    "first_approval",
    "first_in_class",
    "inorganic_flag",
    "max_phase",
    "molecule_chembl_id",
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "molecule_type",
    "natural_product",
    "oral",
    "parenteral",
    "polymer_flag",
    "pref_name",
    "prodrug",
    "structure_standard_inchi_key",
    "structure_type",
    "therapeutic_flag",
    "topical",
    "withdrawn_flag",
]

# Algorithm
content_hash = sha256(f"chembl{canonical_json(filtered_record)}")
```

---

## 5. Validation

### 5.1. Pandera Schema

```python
# src/bioetl/domain/schemas/chembl/molecule.py

class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    # === Identifiers ===
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )
    structure_standard_inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=INCHI_KEY_REGEX_PATTERN,  # ^[A-Z]{14}-[A-Z]{10}-[A-Z]$
        description="Standard InChI Key (27 characters).",
    )

    # === Core Properties ===
    pref_name: Series[str] | None = pa.Field(nullable=True)
    max_phase: Series[float] | None = pa.Field(
        nullable=True,
        isin=[-1, 0, 0.5, 1, 2, 3, 4],
    )
    structure_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["MOL", "SEQ", "BOTH", "NONE"],
    )
    molecule_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "Small molecule", "Antibody", "Antibody drug conjugate",
            "Protein", "Oligonucleotide", "Oligosaccharide", "Cell",
            "Enzyme", "Unknown", "Unclassified", "Inorganic small molecule",
            "Polymeric small molecule",
        ],
    )
    first_approval: Series[int] | None = pa.Field(nullable=True)

    # === Flags ===
    therapeutic_flag: Series[bool] | None = pa.Field(nullable=True)
    oral: Series[bool] | None = pa.Field(nullable=True)
    parenteral: Series[bool] | None = pa.Field(nullable=True)
    topical: Series[bool] | None = pa.Field(nullable=True)
    black_box_warning: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    natural_product: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1])
    first_in_class: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    prodrug: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    inorganic_flag: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    polymer_flag: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    withdrawn_flag: Series[bool] | None = pa.Field(nullable=True)

    # === Complex Fields (JSON Strings) ===
    molecule_hierarchy: Series[str] | None = pa.Field(nullable=True)
    molecule_properties: Series[str] | None = pa.Field(nullable=True)
    molecule_structures: Series[str] | None = pa.Field(nullable=True)
    molecule_synonyms: Series[str] | None = pa.Field(nullable=True)
    cross_references: Series[str] | None = pa.Field(nullable=True)
    atc_classifications: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field | Type | Nullable | Constraints | DQ Level | Failure Action |
|-------|------|----------|-------------|----------|----------------|
| `molecule_chembl_id` | str | No | regex `^CHEMBL\d+$` | CRITICAL | Quarantine |
| `structure_standard_inchi_key` | str | Yes | InChI Key format | WARNING | Log |
| `pref_name` | str | Yes | - | INFO | Log |
| `max_phase` | float | Yes | isin [-1,0,0.5,1,2,3,4] | WARNING | Log |
| `molecule_type` | str | Yes | isin [...] | WARNING | Log |
| `black_box_warning` | int | Yes | isin [0,1] | WARNING | Log |

### 5.3. DQ Thresholds

| Threshold | Value | Action |
|-----------|-------|--------|
| Soft | 5% | Warning, continue |
| Hard | 20% | Fail batch |
| Critical field null | molecule_chembl_id is null | Fail immediately |

---

## 6. Output Schemas

### 6.1. Bronze

```
Path: bronze/v1/chembl/molecule/{YYYY-MM-DD}/
Format: JSONL + zstd
Mode: Append-only
Retention: 90 days → Archive
```

### 6.2. Silver

```
Path: silver/chembl/molecule/
Format: Delta Lake (delta-rs)
Mode: Merge on [molecule_chembl_id]
Partition: None
Retention: Permanent
```

### 6.3. Gold

```
Path: gold/chembl/molecule/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** Valid molecules with structure

---

## 7. Dependencies

### 7.1. Upstream

| Dependency | Type | Required |
|------------|------|----------|
| ChEMBL API | API | Yes |
| Input CSV | File | Optional |

### 7.2. Downstream

| Consumer | Impact |
|----------|--------|
| `chembl_activity` | FK reference |
| `chembl_compound_record` | FK reference |
| SAR analytics | Structure-activity analysis |

### 7.3. Cross-Provider Mapping

| This Entity Field | Maps To | Provider | Field |
|-------------------|---------|----------|-------|
| `structure_standard_inchi_key` | PubChem | PubChem | `inchi_key` |
| `cross_references[drugbank]` | DrugBank | DrugBank | ID |

---

## 8. Pipeline Configuration

```yaml
# configs/pipelines/chembl/molecule.yaml

pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
version: "1.1.0"
description: "Extract molecules from ChEMBL API"

primary_keys: ["molecule_chembl_id"]
silver_table: "chembl_molecule"
gold_table: "chembl_molecule"

source_file: ../../sources/chembl.yaml

gold_filters:
  required_fields:
    - molecule_chembl_id

sink:
  bronze:
    path: "data/output/bronze"
  silver:
    path: "data/output/silver"
    primary_key: ["molecule_chembl_id"]
    partition_by: []
    csv_export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    csv_export:
      path: "data/output/csv/gold"

input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "molecule_chembl_id"
  filter_field: "molecule_chembl_id"
  batch_size: 20
```

---

## 9. Testing Requirements

- [x] Unit tests for normalization and validation
- [x] VCR integration tests
- [x] Architecture compliance tests
