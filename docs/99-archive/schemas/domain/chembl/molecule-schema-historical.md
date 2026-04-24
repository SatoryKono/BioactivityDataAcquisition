______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-24'

______________________________________________________________________

**⚠️ HISTORICAL CONTENT - ARCHIVED**

This page has been moved to the archive section and is no longer part of the active reference surface.

# Molecule Schema (ChEMBL) - Historical

**Current Schema**: [ChEMBL molecule provider reference](../../../providers/chembl/molecule.md)

**Current Config**: `configs/entities/chembl/molecule.yaml`

## Migration Notes

- **Status**: This schema page was moved to archive on 2026-04-24 as part of Issue #3092
- **Reason**: Historical deep schema pages create ambiguity with current canonical contracts
- **Replacement**: Use provider reference and entity config for current schema expectations

## Historical Context

## Overview

| Attribute            | Value                                         |
| -------------------- | --------------------------------------------- |
| **Entity ID**        | `molecule_id` (Business Key)                  |
| **Content Hash**     | `content_hash` (SHA256 for SCD Type 2)        |
| **Source**           | ChEMBL API (`/chembl/api/data/molecule.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle)              |
| **Schema Version**   | 1.0.0 (ChEMBL 34 aligned)                     |

### Purpose

Molecule records represent chemical compounds including small molecules, proteins, antibodies, and oligonucleotides. Each record contains structural information, calculated properties, clinical development status, and regulatory annotations.

### Key Relationships

```
Molecule ◄─── Activity (molecule_id)
    │
    └──► Parent Molecule (hierarchy-parent-chembl-id)
```

______________________________________________________________________

## Medallion Representation

| Layer  | Format     | Validation       | Partition Key    | Retention |
| ------ | ---------- | ---------------- | ---------------- | --------- |
| Bronze | JSONL+zstd | None             | `ingestion-date` | 90 days   |
| Silver | Delta Lake | Pandera (soft)   | `molecule-type`  | Permanent |
| Gold   | Delta Lake | Pandera (strict) | None             | Permanent |

### Gold Layer Filtering

Gold layer applies filters for high-quality drug-like molecules:

| Filter           | Values               | Purpose                   |
| ---------------- | -------------------- | ------------------------- |
| `molecule-type`  | `["Small molecule"]` | Focus on small molecules  |
| `structure-type` | `["MOL"]`            | Molecules with structures |
| `inorganic-flag` | `["0"]`              | Organic compounds only    |

**Required Fields for Gold**: `molecule_id`

______________________________________________________________________

## Field Schemas

### Primary Key

| Field         | Type  | Nullable | Constraints   | Description                | Source                    |
| ------------- | ----- | -------- | ------------- | -------------------------- | ------------------------- |
| `molecule_id` | `str` | No       | `^CHEMBL\d+$` | ChEMBL molecule identifier | `molecules[].molecule_id` |

### Core Properties

| Field            | Type    | Nullable | Constraints                        | Description                       | Source                       |
| ---------------- | ------- | -------- | ---------------------------------- | --------------------------------- | ---------------------------- |
| `pref-name`      | `str`   | Yes      | —                                  | Preferred name (INN, USAN)        | `molecules[].pref-name`      |
| `molecule-type`  | `str`   | Yes      | `isin=[...]`                       | Molecule type classification      | `molecules[].molecule-type`  |
| `structure-type` | `str`   | Yes      | `isin=["MOL","SEQ","BOTH","NONE"]` | Structure data type               | `molecules[].structure-type` |
| `max-phase`      | `float` | Yes      | `isin=[-1,0,0.5,1,2,3,4]`          | Maximum clinical phase reached    | `molecules[].max-phase`      |
| `first-approval` | `int`   | Yes      | —                                  | Year of first regulatory approval | `molecules[].first-approval` |

**Valid `molecule-type` values:**

- `Small molecule`, `Inorganic small molecule`, `Polymeric small molecule`
- `Antibody`, `Antibody drug conjugate`, `Protein`
- `Oligonucleotide`, `Oligosaccharide`, `Cell`, `Enzyme`
- `Unknown`, `Unclassified`

### Administration Route Flags

| Field        | Type   | Nullable | Constraints | Description                         | Source                   |
| ------------ | ------ | -------- | ----------- | ----------------------------------- | ------------------------ |
| `oral`       | `bool` | Yes      | —           | Approved for oral administration    | `molecules[].oral`       |
| `parenteral` | `bool` | Yes      | —           | Approved for parenteral (injection) | `molecules[].parenteral` |
| `topical`    | `bool` | Yes      | —           | Approved for topical application    | `molecules[].topical`    |

### Regulatory & Safety Flags

| Field               | Type   | Nullable | Constraints  | Description                 | Source                          |
| ------------------- | ------ | -------- | ------------ | --------------------------- | ------------------------------- |
| `therapeutic-flag`  | `bool` | Yes      | —            | Has therapeutic application | `molecules[].therapeutic-flag`  |
| `black-box-warning` | `int`  | Yes      | `isin=[0,1]` | FDA black box warning       | `molecules[].black-box-warning` |
| `withdrawn-flag`    | `bool` | Yes      | —            | Withdrawn from market       | `molecules[].withdrawn-flag`    |
| `first-in-class`    | `int`  | Yes      | `isin=[0,1]` | First-in-class mechanism    | `molecules[].first-in-class`    |

### Chemical Classification Flags

| Field             | Type  | Nullable | Constraints     | Description                      | Source                        |
| ----------------- | ----- | -------- | --------------- | -------------------------------- | ----------------------------- |
| `natural-product` | `int` | Yes      | `isin=[-1,0,1]` | Natural product origin           | `molecules[].natural-product` |
| `prodrug`         | `int` | Yes      | `isin=[0,1]`    | Prodrug that requires activation | `molecules[].prodrug`         |
| `inorganic-flag`  | `int` | Yes      | `isin=[0,1]`    | Inorganic compound               | `molecules[].inorganic-flag`  |
| `polymer-flag`    | `int` | Yes      | `isin=[0,1]`    | Polymer                          | `molecules[].polymer-flag`    |

### Complex Fields (JSON Serialized)

| Field                 | Type  | Nullable | Description                            | Source                            |
| --------------------- | ----- | -------- | -------------------------------------- | --------------------------------- |
| `molecule-hierarchy`  | `str` | Yes      | Parent/child relationships (JSON)      | `molecules[].molecule-hierarchy`  |
| `molecule-properties` | `str` | Yes      | Calculated molecular properties (JSON) | `molecules[].molecule-properties` |
| `molecule-structures` | `str` | Yes      | SMILES, InChI structures (JSON)        | `molecules[].molecule-structures` |
| `molecule-synonyms`   | `str` | Yes      | Alternative names (JSON)               | `molecules[].molecule-synonyms`   |
| `cross-references`    | `str` | Yes      | External database links (JSON)         | `molecules[].cross-references`    |
| `atc-classifications` | `str` | Yes      | WHO ATC codes (JSON)                   | `molecules[].atc-classifications` |

### Flattened Hierarchy Fields

| Field                        | Type  | Nullable | Description                 | Source                                |
| ---------------------------- | ----- | -------- | --------------------------- | ------------------------------------- |
| `hierarchy-parent-chembl-id` | `str` | Yes      | Parent molecule (for salts) | `molecule-hierarchy.parent-chembl-id` |
| `hierarchy-active-chembl-id` | `str` | Yes      | Active moiety               | `molecule-hierarchy.active-chembl-id` |

### Flattened Property Fields

| Field                     | Type    | Nullable | Description                   | Source                                   |
| ------------------------- | ------- | -------- | ----------------------------- | ---------------------------------------- |
| `property-alogp`          | `float` | Yes      | Calculated ALogP              | `molecule-properties.alogp`              |
| `property-mw-freebase`    | `float` | Yes      | Molecular weight (freebase)   | `molecule-properties.mw-freebase`        |
| `property-full-mwt`       | `float` | Yes      | Full molecular weight         | `molecule-properties.full-mwt`           |
| `property-hba`            | `int`   | Yes      | H-bond acceptor count         | `molecule-properties.hba`                |
| `property-hbd`            | `int`   | Yes      | H-bond donor count            | `molecule-properties.hbd`                |
| `property-psa`            | `float` | Yes      | Polar surface area            | `molecule-properties.psa`                |
| `property-rtb`            | `int`   | Yes      | Rotatable bond count          | `molecule-properties.rtb`                |
| `property-ro5-violations` | `int`   | Yes      | Lipinski Rule of 5 violations | `molecule-properties.num-ro5-violations` |
| `property-heavy-atoms`    | `int`   | Yes      | Heavy atom count              | `molecule-properties.heavy-atoms`        |
| `property-aromatic-rings` | `int`   | Yes      | Aromatic ring count           | `molecule-properties.aromatic-rings`     |
| `property-qed-weighted`   | `float` | Yes      | QED drug-likeness score       | `molecule-properties.qed-weighted`       |

### Flattened Structure Fields

> **Note**: As of v5.10.0, structure fields use unified naming without the `structure-` prefix
> for consistency with PubChem. See migration guide below.

| Field              | Type  | Nullable | Description                     | Source                                   |
| ------------------ | ----- | -------- | ------------------------------- | ---------------------------------------- |
| `canonical_smiles` | `str` | Yes      | Canonical SMILES representation | `molecule-structures.canonical_smiles`   |
| `standard-inchi`   | `str` | Yes      | Standard InChI representation   | `molecule-structures.standard-inchi`     |
| `inchi-key`        | `str` | Yes      | Standard InChI Key              | `molecule-structures.standard-inchi-key` |

#### Migration from v5.9.x

The following field names have been renamed:

- `structure-canonical_smiles` → `canonical_smiles`
- `structure-standard-inchi` → `standard-inchi`
- `structure-standard-inchi-key` → `inchi-key`

For legacy datasets created before v5.10.x, structure field renames were handled by
a historical archive-only migration workflow. This is not part of the standard
operational path for new deployments.

______________________________________________________________________

## System Fields (Persisted-Row Contract)

| Field          | Type   | Nullable | Purpose                      | Included in Content Hash |
| -------------- | ------ | -------- | ---------------------------- | ------------------------ |
| `entity_id`    | `str`  | No       | Business key (= molecule_id) | Yes                      |
| `content_hash` | `str`  | No       | SHA256 for SCD Type 2        | —                        |
| `_dq_warn`     | `bool` | No       | DQ warning flag              | No                       |
| `_index`       | `int`  | No       | Record index in batch        | No                       |

Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,
`_ingestion_ts`) is not part of the physical Silver/Gold row contract for
current ChEMBL molecule publication. These anchors are emitted through sidecar
metadata, lineage fragments, run manifest, run ledger, and related audit
artifacts.

______________________________________________________________________

## Transformations

### Bronze → Silver

| Source Field                             | Target Field                 | Transformation      |
| ---------------------------------------- | ---------------------------- | ------------------- |
| `molecule_id`                            | `molecule_id`                | Direct              |
| `max-phase`                              | `max-phase`                  | `safe-float()`      |
| `first-approval`                         | `first-approval`             | `safe-int()`        |
| `molecule-hierarchy`                     | `molecule-hierarchy`         | `json.dumps()`      |
| `molecule-hierarchy.parent-chembl-id`    | `hierarchy-parent-chembl-id` | Flatten             |
| `molecule-properties`                    | `molecule-properties`        | `json.dumps()`      |
| `molecule-properties.*`                  | `property-*`                 | Flatten & convert   |
| `molecule-structures`                    | `molecule-structures`        | `json.dumps()`      |
| `molecule-structures.canonical_smiles`   | `canonical_smiles`           | Flatten (no prefix) |
| `molecule-structures.standard-inchi`     | `standard-inchi`             | Flatten (no prefix) |
| `molecule-structures.standard-inchi-key` | `inchi-key`                  | Flatten + rename    |

______________________________________________________________________

## Validation Rules

### Pandera Schema

```python
class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    molecule_id: Series[str] = pa.Field(nullable=False, str - matches=r"^CHEMBL\d+$")
    max - phase: Optional[Series[float]] = pa.Field(
        nullable=True, isin=[-1, 0, 0.5, 1, 2, 3, 4]
    )
    structure - type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=["MOL", "SEQ", "BOTH", "NONE"]
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def -validate-invariants(self) -> None:
    if not self.molecule_id:
        raise ValueError("Molecule ChEMBL ID is required")
    if self.max-phase is not None and not (0 <= self.max-phase <= 4):
        raise ValueError(f"max-phase must be 0-4, got {self.max-phase}")
```

______________________________________________________________________

## Cross-Source Mapping

| Source   | ID Field                           | Mapping Strategy     |
| -------- | ---------------------------------- | -------------------- |
| ChEMBL   | `molecule_id`                      | Primary source       |
| PubChem  | `cross-references[src="PubChem"]`  | Via cross-references |
| DrugBank | `cross-references[src="DrugBank"]` | Via cross-references |
| ChEBI    | `cross-references[src="ChEBI"]`    | Via cross-references |

______________________________________________________________________

## Example Records

### Bronze (Raw API Response)

```json
{
  "molecule_id": "CHEMBL25",
  "pref-name": "ASPIRIN",
  "molecule-type": "Small molecule",
  "structure-type": "MOL",
  "max-phase": 4,
  "first-approval": 1950,
  "oral": true,
  "parenteral": false,
  "topical": true,
  "black-box-warning": 0,
  "therapeutic-flag": true,
  "molecule-hierarchy": {
    "molecule_id": "CHEMBL25",
    "parent-chembl-id": "CHEMBL25"
  },
  "molecule-properties": {
    "alogp": 1.31,
    "full-mwt": 180.16,
    "hba": 4,
    "hbd": 1,
    "psa": 63.6,
    "rtb": 3,
    "num-ro5-violations": 0,
    "qed-weighted": 0.56
  },
  "molecule-structures": {
    "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "standard-inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
    "standard-inchi-key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
  }
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL25",
  "molecule_id": "CHEMBL25",
  "content_hash": "sha256:abc123...",
  "_dq_warn": false,
  "_index": 0,

  "pref-name": "ASPIRIN",
  "molecule-type": "Small molecule",
  "structure-type": "MOL",
  "max-phase": 4.0,
  "first-approval": 1950,

  "oral": true,
  "parenteral": false,
  "topical": true,
  "black-box-warning": 0,
  "therapeutic-flag": true,

  "hierarchy-parent-chembl-id": "CHEMBL25",
  "property-alogp": 1.31,
  "property-full-mwt": 180.16,
  "property-hba": 4,
  "property-hbd": 1,
  "property-psa": 63.6,
  "property-rtb": 3,
  "property-ro5-violations": 0,
  "property-qed-weighted": 0.56,

  "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "standard-inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
  "inchi-key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
}
```

______________________________________________________________________

## Related Artifacts

| Artifact        | Path                                              |
| --------------- | ------------------------------------------------- |
| Pandera Schema  | `src/bioetl/domain/schemas/chembl/molecule.py`    |
| Domain Entity   | `src/bioetl/domain/entities/chembl_structures.py` |
| Pipeline Config | `configs/entities/chembl/molecule.yaml`           |

______________________________________________________________________

## Changelog

| Version | Date       | Changes                                                        |
| ------- | ---------- | -------------------------------------------------------------- |
| 1.1.0   | 2026-01-06 | **BREAKING**: Renamed structure fields for PubChem consistency |
| 1.0.0   | 2024-12-28 | Initial schema documentation                                   |

______________________________________________________________________

*Build reliably. Document honestly. Ask boldly.*
