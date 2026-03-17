# ChEMBL Molecule Pipeline Specification

*Version 1.2.0 | Aligned with RULES.md v5.24*

----------------------------------------------------------------------

## 1. Identification

| Parameter        | Value                                            |
| ---------------- | ------------------------------------------------ |
| **Pipeline ID**  | `chembl_molecule`                                |
| **Provider**     | ChEMBL (EBI)                                     |
| **Entity**       | molecule                                         |
| **API Endpoint** | `https://www.ebi.ac.uk/chembl/api/data/molecule` |
| **Library**      | Built-in ChEMBL adapter (httpx)                      |
| **Rate Limit**   | None (polite usage recommended)                  |
| **Health Check** | `/chembl/api/data/status`                        |
| **Auth Type**    | None (public API)                                |

----------------------------------------------------------------------

## 2. Business Context

### 2.1. Entity Purpose

Molecules represent **chemical compounds** in ChEMBL with their structural and pharmacological properties:

- **Drug discovery**: Central entity linking compounds to biological activities
- **Structure-activity relationships (SAR)**: Chemical structures with activity data
- **Clinical development**: Track compounds through clinical phases
- **Cross-database linking**: InChI Key enables mapping to PubChem, DrugBank

### 2.2. Use Cases

1. **Compound Search**: Find molecules by structure, name, or properties
1. **Drug Pipeline Analysis**: Analyze compounds by clinical phase
1. **SAR Studies**: Correlate structural features with activity profiles
1. **Toxicity Screening**: Identify compounds with black box warnings
1. **Natural Product Discovery**: Filter for natural product-derived compounds

### 2.3. Entity Relationships

```
molecule
    │
    ├──◄──FK──activity.molecule-id (1:M)
    │
    ├──◄──FK──compound-record.molecule-id (1:M)
    │
    └── molecule-hierarchy (nested)
        ├── parent-chembl-id
        └── active-chembl-id
```

### 2.4. Load Strategy

| Parameter               | Value                           |
| ----------------------- | ------------------------------- |
| **Strategy**            | `incremental` with input filter |
| **Watermark Field**     | N/A (filtered by input CSV)     |
| **Full Load Frequency** | On demand                       |
| **Estimated Volume**    | ~2.4M records total             |
| **Batch Size**          | 20 (filter batch)               |

----------------------------------------------------------------------

## 3. Extraction (Bronze Layer)

### 3.1. API Request

```python
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

adapter = ChemblAdapter(config=adapter_config)
# Filter by input CSV molecule-ids; adapter normalizes fields
results = adapter.fetch(entity="molecule", filters={"molecule-id": chembl_ids})
```

### 3.2. Complete API Fields (23 поля)

> **Примечание:** После flattening (molecule-hierarchy, molecule-properties, molecule-structures) Silver schema содержит 46 полей.

| #   | API Field             | JSON Type | Nullable | Nested | Description          | Example            |
| --- | --------------------- | --------- | -------- | ------ | -------------------- | ------------------ |
| 1   | `molecule-id`         | string    | No       | -      | Primary key          | `"CHEMBL25"`       |
| 2   | `pref-name`           | string    | Yes      | -      | Preferred name       | `"ASPIRIN"`        |
| 3   | `molecule-type`       | string    | Yes      | -      | Type                 | `"Small molecule"` |
| 4   | `max-phase`           | number    | Yes      | -      | Clinical phase       | `4`                |
| 5   | `structure-type`      | string    | Yes      | -      | Structure type       | `"MOL"`            |
| 6   | `therapeutic-flag`    | boolean   | Yes      | -      | Is therapeutic       | `true`             |
| 7   | `oral`                | boolean   | Yes      | -      | Oral delivery        | `true`             |
| 8   | `parenteral`          | boolean   | Yes      | -      | Parenteral delivery  | `false`            |
| 9   | `topical`             | boolean   | Yes      | -      | Topical delivery     | `false`            |
| 10  | `black-box-warning`   | integer   | Yes      | -      | BBW flag             | `0`                |
| 11  | `natural-product`     | integer   | Yes      | -      | Natural product flag | `0`                |
| 12  | `first-in-class`      | integer   | Yes      | -      | First in class       | `0`                |
| 13  | `prodrug`             | integer   | Yes      | -      | Prodrug flag         | `0`                |
| 14  | `inorganic-flag`      | integer   | Yes      | -      | Inorganic flag       | `0`                |
| 15  | `polymer-flag`        | integer   | Yes      | -      | Polymer flag         | `0`                |
| 16  | `first-approval`      | integer   | Yes      | -      | First approval year  | `1899`             |
| 17  | `withdrawn-flag`      | boolean   | Yes      | -      | Withdrawn flag       | `false`            |
| 18  | `molecule-hierarchy`  | object    | Yes      | Yes    | Hierarchy            | JSON               |
| 19  | `molecule-properties` | object    | Yes      | Yes    | Properties           | JSON               |
| 20  | `molecule-structures` | object    | Yes      | Yes    | Structures           | JSON               |
| 21  | `molecule-synonyms`   | array     | Yes      | Yes    | Synonyms             | JSON               |
| 22  | `cross-references`    | array     | Yes      | Yes    | Cross-refs           | JSON               |
| 23  | `atc-classifications` | array     | Yes      | Yes    | ATC codes            | JSON               |

### 3.3. Nested Structure: molecule-structures

| Field                | Type   | Description                   |
| -------------------- | ------ | ----------------------------- |
| `canonical-smiles`   | string | Canonical SMILES              |
| `standard-inchi`     | string | Standard InChI                |
| `standard-inchi-key` | string | Standard InChI Key (27 chars) |
| `molfile`            | string | MOL file content              |

### 3.4. Nested Structure: molecule-properties

| Field                | Type    | Description           |
| -------------------- | ------- | --------------------- |
| `molecular-formula`  | string  | Molecular formula     |
| `full-mwt`           | float   | Full molecular weight |
| `mw-freebase`        | float   | Freebase MW           |
| `mw-monoisotopic`    | float   | Monoisotopic MW       |
| `alogp`              | float   | ALogP                 |
| `cx-logp`            | float   | ChemAxon LogP         |
| `cx-logd`            | float   | ChemAxon LogD         |
| `psa`                | float   | Polar surface area    |
| `hba`                | integer | H-bond acceptors      |
| `hbd`                | integer | H-bond donors         |
| `rtb`                | integer | Rotatable bonds       |
| `num-ro5-violations` | integer | Rule of 5 violations  |
| `aromatic-rings`     | integer | Aromatic rings        |
| `heavy-atoms`        | integer | Heavy atoms           |
| `qed-weighted`       | float   | QED score             |

----------------------------------------------------------------------

## 4. Transformation

### 4.1. Entity ID Strategy

| Parameter           | Value                    |
| ------------------- | ------------------------ |
| **Entity ID Field** | `molecule-id`            |
| **ID Source**       | `from-api`               |
| **Format**          | ChEMBL ID (CHEMBL[0-9]+) |

### 4.2. Field Normalization

| Field                          | Normalization       | Before               | After                  |
| ------------------------------ | ------------------- | -------------------- | ---------------------- |
| `molecule-id`                  | Validate regex      | `"CHEMBL25"`         | `"CHEMBL25"`           |
| `pref-name`                    | strip().upper()     | `" aspirin "`        | `"ASPIRIN"`            |
| `max-phase`                    | Cast to float       | `"4"`                | `4.0`                  |
| `structure-standard-inchi-key` | Extract from nested | `{...}`              | `"BSYNRYMUTXBXSQ-..."` |
| Float properties               | round(10)           | `180.12345678901234` | `180.1234567890`       |
| Nested objects                 | JSON serialize      | `{...}`              | `'{"key": "value"}'`   |

### 4.3. Flattening Strategy

| Nested Path                              | Flattened Name                 | Strategy       |
| ---------------------------------------- | ------------------------------ | -------------- |
| `molecule-structures.standard-inchi-key` | `structure-standard-inchi-key` | Extract scalar |
| `molecule-hierarchy`                     | `molecule-hierarchy`           | JSON string    |
| `molecule-properties`                    | `molecule-properties`          | JSON string    |
| `molecule-structures`                    | `molecule-structures`          | JSON string    |
| `molecule-synonyms`                      | `molecule-synonyms`            | JSON string    |
| `cross-references`                       | `cross-references`             | JSON string    |
| `atc-classifications`                    | `atc-classifications`          | JSON string    |

### 4.4. Content Hash Specification

```python
# Fields included in hash (alphabetical order)
hash-fields = [
    "atc-classifications",
    "black-box-warning",
    "cross-references",
    "first-approval",
    "first-in-class",
    "inorganic-flag",
    "max-phase",
    "molecule-id",
    "molecule-hierarchy",
    "molecule-properties",
    "molecule-structures",
    "molecule-synonyms",
    "molecule-type",
    "natural-product",
    "oral",
    "parenteral",
    "polymer-flag",
    "pref-name",
    "prodrug",
    "structure-standard-inchi-key",
    "structure-type",
    "therapeutic-flag",
    "topical",
    "withdrawn-flag",
]

# Algorithm
content-hash = sha256(f"chembl{canonical-json(filtered-record)}")
```

----------------------------------------------------------------------

## 5. Validation

### 5.1. Pandera Schema

> Migration note: public Pandera contract uses canonical PK names; legacy aliases are accepted only during transition via ingestion/transform alias mapping and will be removed in the next major release.

```python
# src/bioetl/domain/schemas/chembl/molecule.py
# 52 entity-specific fields (excluding ETL metadata from ETLRecordSchema)


class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    # === Identifiers ===
    molecule-id: Series[str] = pa.Field(
        nullable=False,
        str-matches=CHEMBL-ID-PATTERN,
        description="ChEMBL ID.",
    )
    structure-standard-inchi-key: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=INCHI-KEY-REGEX-PATTERN,
        description="Standard InChI Key (27 characters, format: XXXX-YYYY-Z).",
    )

    # === Core Properties ===
    pref-name: Series[str] | None = pa.Field(nullable=True)
    max-phase: Series[float] | None = pa.Field(
        nullable=True,
        isin=[-1, 0, 0.5, 1, 2, 3, 4],
    )
    structure-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["MOL", "SEQ", "BOTH", "NONE"],
    )
    molecule-type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "Small molecule",
            "Antibody",
            "Antibody drug conjugate",
            "Protein",
            "Oligonucleotide",
            "Oligosaccharide",
            "Cell",
            "Enzyme",
            "Unknown",
            "Unclassified",
            "Inorganic small molecule",
            "Polymeric small molecule",
        ],
    )
    first-approval: Series[float] | None = pa.Field(nullable=True)

    # === Flags ===
    therapeutic-flag: Series[bool] | None = pa.Field(nullable=True)
    oral: Series[bool] | None = pa.Field(nullable=True)
    parenteral: Series[bool] | None = pa.Field(nullable=True)
    topical: Series[bool] | None = pa.Field(nullable=True)
    black-box-warning: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    natural-product: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1])
    first-in-class: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1])
    prodrug: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1])
    inorganic-flag: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1])
    polymer-flag: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    withdrawn-flag: Series[bool] | None = pa.Field(nullable=True)

    # === Other Properties ===
    chirality: Series[int] | None = pa.Field(nullable=True, isin=[-1, 0, 1, 2])
    dosed-ingredient: Series[int] | None = pa.Field(nullable=True, isin=[0, 1])
    availability-type: Series[float] | None = pa.Field(
        nullable=True, isin=[-2, -1, 0, 1, 2]
    )
    usan-year: Series[float] | None = pa.Field(nullable=True)
    usan-stem: Series[str] | None = pa.Field(nullable=True)
    usan-substem: Series[str] | None = pa.Field(nullable=True)
    usan-stem-definition: Series[str] | None = pa.Field(nullable=True)
    helm-notation: Series[str] | None = pa.Field(nullable=True)
    molecule-species: Series[str] | None = pa.Field(nullable=True)

    # === Hierarchy Fields (flattened from molecule-hierarchy) ===
    hierarchy-parent-chembl-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=CHEMBL-ID-PATTERN,
    )
    hierarchy-active-chembl-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=CHEMBL-ID-PATTERN,
    )
    hierarchy-child-chembl-id: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=CHEMBL-ID-PATTERN,
    )

    # === Property Fields (flattened from molecule-properties) ===
    property-alogp: Series[float] | None = pa.Field(nullable=True)
    property-mw-freebase: Series[float] | None = pa.Field(nullable=True)
    property-full-mwt: Series[float] | None = pa.Field(nullable=True)
    property-hba: Series[int] | None = pa.Field(nullable=True, ge=0)
    property-hbd: Series[int] | None = pa.Field(nullable=True, ge=0)
    property-psa: Series[float] | None = pa.Field(nullable=True, ge=0)
    property-rtb: Series[int] | None = pa.Field(nullable=True, ge=0)
    property-ro5-violations: Series[int] | None = pa.Field(nullable=True, ge=0, le=4)
    property-heavy-atoms: Series[int] | None = pa.Field(nullable=True, ge=0)
    property-aromatic-rings: Series[int] | None = pa.Field(nullable=True, ge=0)
    property-qed-weighted: Series[float] | None = pa.Field(nullable=True, ge=0, le=1)
    property-full-molformula: Series[str] | None = pa.Field(nullable=True)
    property-ro3-pass: Series[str] | None = pa.Field(nullable=True, isin=["Y", "N"])

    # === Structure Fields (flattened from molecule-structures) ===
    canonical-smiles: Series[str] | None = pa.Field(nullable=True)
    standard-inchi: Series[str] | None = pa.Field(nullable=True)
    inchikey: Series[str] | None = pa.Field(
        nullable=True,
        str-matches=INCHI-KEY-REGEX-PATTERN,
    )

    # === Complex Fields (JSON Strings) ===
    molecule-hierarchy: Series[str] | None = pa.Field(nullable=True)
    molecule-properties: Series[str] | None = pa.Field(nullable=True)
    molecule-structures: Series[str] | None = pa.Field(nullable=True)
    molecule-synonyms: Series[str] | None = pa.Field(nullable=True)
    cross-references: Series[str] | None = pa.Field(nullable=True)
    atc-classifications: Series[str] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### 5.2. Field Validation Matrix

| Field                          | Type  | Nullable | Constraints             | DQ Level | Failure Action |
| ------------------------------ | ----- | -------- | ----------------------- | -------- | -------------- |
| `molecule-id`                  | str   | No       | regex `^CHEMBL\d+$`     | CRITICAL | Quarantine     |
| `structure-standard-inchi-key` | str   | Yes      | InChI Key format        | WARNING  | Log            |
| `pref-name`                    | str   | Yes      | -                       | INFO     | Log            |
| `max-phase`                    | float | Yes      | isin [-1,0,0.5,1,2,3,4] | WARNING  | Log            |
| `molecule-type`                | str   | Yes      | isin [...]              | WARNING  | Log            |
| `black-box-warning`            | int   | Yes      | isin [0,1]              | WARNING  | Log            |

### 5.3. DQ Thresholds

| Threshold           | Value               | Action            |
| ------------------- | ------------------- | ----------------- |
| Soft                | 5%                  | Warning, continue |
| Hard                | 20%                 | Fail batch        |
| Critical field null | molecule-id is null | Fail immediately  |

----------------------------------------------------------------------

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
Mode: Merge on [molecule-id]
Partition: ["molecule-type"]
Retention: Permanent
```

### 6.3. Gold

```
Path: gold/chembl/molecule/
Format: Delta Lake
Mode: Overwrite
```

**Gold Filter:** Valid molecules with structure

----------------------------------------------------------------------

## 7. Dependencies

### 7.1. Upstream

| Dependency | Type | Required |
| ---------- | ---- | -------- |
| ChEMBL API | API  | Yes      |
| Input CSV  | File | Optional |

### 7.2. Downstream

| Consumer                 | Impact                      |
| ------------------------ | --------------------------- |
| `chembl_activity`        | FK reference                |
| `chembl_compound_record` | FK reference                |
| SAR analytics            | Structure-activity analysis |

### 7.3. Cross-Provider Mapping

| This Entity Field              | Maps To  | Provider | Field       |
| ------------------------------ | -------- | -------- | ----------- |
| `structure-standard-inchi-key` | PubChem  | PubChem  | `inchi-key` |
| `cross-references[drugbank]`   | DrugBank | DrugBank | ID          |

----------------------------------------------------------------------

## 8. Pipeline Configuration

```yaml
# configs/entities/chembl/molecule.yaml

pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
version: "1.2.0"
description: "Extract molecules from ChEMBL API"
business_primary_keys: ["molecule_id"]

gold_filters:
  required_fields:
    - molecule_id

sink:
  bronze:
    path: "data/output/bronze"
silver:
  path: "data/output/silver"
  primary_key: ["molecule_id"]
  partition_by: ["molecule_type"]
    csv_export:
      path: "data/output/csv/silver"
  gold:
    path: "data/output/gold"
    csv_export:
      path: "data/output/csv/gold"

input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "molecule-id"
  filter_field: "molecule-id"
  batch_size: 20
```

----------------------------------------------------------------------

## 9. Testing Requirements

- [x] Unit tests for normalization and validation
- [x] VCR integration tests
- [x] Architecture compliance tests
