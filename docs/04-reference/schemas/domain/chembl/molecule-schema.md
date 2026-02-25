# Molecule Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.22*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `molecule-chembl-id` (Business Key) |
| **Content Hash** | `content-hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/molecule.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Molecule records represent chemical compounds including small molecules, proteins, antibodies, and oligonucleotides. Each record contains structural information, calculated properties, clinical development status, and regulatory annotations.

### Key Relationships
```
Molecule ◄─── Activity (molecule-chembl-id)
    │
    └──► Parent Molecule (hierarchy-parent-chembl-id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion-date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `molecule-type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for high-quality drug-like molecules:

| Filter | Values | Purpose |
|--------|--------|---------|
| `molecule-type` | `["Small molecule"]` | Focus on small molecules |
| `structure-type` | `["MOL"]` | Molecules with structures |
| `inorganic-flag` | `["0"]` | Organic compounds only |

**Required Fields for Gold**: `molecule-chembl-id`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `molecule-chembl-id` | `str` | No | `^CHEMBL\d+$` | ChEMBL molecule identifier | `molecules[].molecule-chembl-id` |

### Core Properties

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pref-name` | `str` | Yes | — | Preferred name (INN, USAN) | `molecules[].pref-name` |
| `molecule-type` | `str` | Yes | `isin=[...]` | Molecule type classification | `molecules[].molecule-type` |
| `structure-type` | `str` | Yes | `isin=["MOL","SEQ","BOTH","NONE"]` | Structure data type | `molecules[].structure-type` |
| `max-phase` | `float` | Yes | `isin=[-1,0,0.5,1,2,3,4]` | Maximum clinical phase reached | `molecules[].max-phase` |
| `first-approval` | `int` | Yes | — | Year of first regulatory approval | `molecules[].first-approval` |

**Valid `molecule-type` values:**
- `Small molecule`, `Inorganic small molecule`, `Polymeric small molecule`
- `Antibody`, `Antibody drug conjugate`, `Protein`
- `Oligonucleotide`, `Oligosaccharide`, `Cell`, `Enzyme`
- `Unknown`, `Unclassified`

### Administration Route Flags

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `oral` | `bool` | Yes | — | Approved for oral administration | `molecules[].oral` |
| `parenteral` | `bool` | Yes | — | Approved for parenteral (injection) | `molecules[].parenteral` |
| `topical` | `bool` | Yes | — | Approved for topical application | `molecules[].topical` |

### Regulatory & Safety Flags

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `therapeutic-flag` | `bool` | Yes | — | Has therapeutic application | `molecules[].therapeutic-flag` |
| `black-box-warning` | `int` | Yes | `isin=[0,1]` | FDA black box warning | `molecules[].black-box-warning` |
| `withdrawn-flag` | `bool` | Yes | — | Withdrawn from market | `molecules[].withdrawn-flag` |
| `first-in-class` | `int` | Yes | `isin=[0,1]` | First-in-class mechanism | `molecules[].first-in-class` |

### Chemical Classification Flags

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `natural-product` | `int` | Yes | `isin=[-1,0,1]` | Natural product origin | `molecules[].natural-product` |
| `prodrug` | `int` | Yes | `isin=[0,1]` | Prodrug that requires activation | `molecules[].prodrug` |
| `inorganic-flag` | `int` | Yes | `isin=[0,1]` | Inorganic compound | `molecules[].inorganic-flag` |
| `polymer-flag` | `int` | Yes | `isin=[0,1]` | Polymer | `molecules[].polymer-flag` |

### Complex Fields (JSON Serialized)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `molecule-hierarchy` | `str` | Yes | Parent/child relationships (JSON) | `molecules[].molecule-hierarchy` |
| `molecule-properties` | `str` | Yes | Calculated molecular properties (JSON) | `molecules[].molecule-properties` |
| `molecule-structures` | `str` | Yes | SMILES, InChI structures (JSON) | `molecules[].molecule-structures` |
| `molecule-synonyms` | `str` | Yes | Alternative names (JSON) | `molecules[].molecule-synonyms` |
| `cross-references` | `str` | Yes | External database links (JSON) | `molecules[].cross-references` |
| `atc-classifications` | `str` | Yes | WHO ATC codes (JSON) | `molecules[].atc-classifications` |

### Flattened Hierarchy Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `hierarchy-parent-chembl-id` | `str` | Yes | Parent molecule (for salts) | `molecule-hierarchy.parent-chembl-id` |
| `hierarchy-active-chembl-id` | `str` | Yes | Active moiety | `molecule-hierarchy.active-chembl-id` |

### Flattened Property Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `property-alogp` | `float` | Yes | Calculated ALogP | `molecule-properties.alogp` |
| `property-mw-freebase` | `float` | Yes | Molecular weight (freebase) | `molecule-properties.mw-freebase` |
| `property-full-mwt` | `float` | Yes | Full molecular weight | `molecule-properties.full-mwt` |
| `property-hba` | `int` | Yes | H-bond acceptor count | `molecule-properties.hba` |
| `property-hbd` | `int` | Yes | H-bond donor count | `molecule-properties.hbd` |
| `property-psa` | `float` | Yes | Polar surface area | `molecule-properties.psa` |
| `property-rtb` | `int` | Yes | Rotatable bond count | `molecule-properties.rtb` |
| `property-ro5-violations` | `int` | Yes | Lipinski Rule of 5 violations | `molecule-properties.num-ro5-violations` |
| `property-heavy-atoms` | `int` | Yes | Heavy atom count | `molecule-properties.heavy-atoms` |
| `property-aromatic-rings` | `int` | Yes | Aromatic ring count | `molecule-properties.aromatic-rings` |
| `property-qed-weighted` | `float` | Yes | QED drug-likeness score | `molecule-properties.qed-weighted` |

### Flattened Structure Fields

> **Note**: As of v5.10.0, structure fields use unified naming without the `structure-` prefix
> for consistency with PubChem. See migration guide below.

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `canonical-smiles` | `str` | Yes | Canonical SMILES representation | `molecule-structures.canonical-smiles` |
| `standard-inchi` | `str` | Yes | Standard InChI representation | `molecule-structures.standard-inchi` |
| `inchi-key` | `str` | Yes | Standard InChI Key | `molecule-structures.standard-inchi-key` |

#### Migration from v5.9.x

The following field names have been renamed:
- `structure-canonical-smiles` → `canonical-smiles`
- `structure-standard-inchi` → `standard-inchi`
- `structure-standard-inchi-key` → `inchi-key`

Use the migration script: `scripts/migrations/rename-structure-fields.py`

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity-id` | `str` | No | Business key (= molecule-chembl-id) | Yes |
| `content-hash` | `str` | No | SHA256 for SCD Type 2 | — |
| `-run-id` | `UUID` | No | Pipeline run correlation ID | No |
| `-run-type` | `Enum` | No | incremental/backfill/rebuild | No |
| `-source-batch-id` | `UUID` | Yes | FK to lineage-log | No |
| `-ingestion-ts` | `Timestamp` | No | Ingestion time (UTC) | No |
| `-dq-warn` | `bool` | No | DQ warning flag | No |
| `-index` | `int` | No | Record index in batch | No |

---

## Transformations

### Bronze → Silver

| Source Field | Target Field | Transformation |
|--------------|--------------|----------------|
| `molecule-chembl-id` | `molecule-chembl-id` | Direct |
| `max-phase` | `max-phase` | `safe-float()` |
| `first-approval` | `first-approval` | `safe-int()` |
| `molecule-hierarchy` | `molecule-hierarchy` | `json.dumps()` |
| `molecule-hierarchy.parent-chembl-id` | `hierarchy-parent-chembl-id` | Flatten |
| `molecule-properties` | `molecule-properties` | `json.dumps()` |
| `molecule-properties.*` | `property-*` | Flatten & convert |
| `molecule-structures` | `molecule-structures` | `json.dumps()` |
| `molecule-structures.canonical-smiles` | `canonical-smiles` | Flatten (no prefix) |
| `molecule-structures.standard-inchi` | `standard-inchi` | Flatten (no prefix) |
| `molecule-structures.standard-inchi-key` | `inchi-key` | Flatten + rename |

---

## Validation Rules

### Pandera Schema

```python
class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    molecule-chembl-id: Series[str] = pa.Field(
        nullable=False, str-matches=r"^CHEMBL\d+$"
    )
    max-phase: Optional[Series[float]] = pa.Field(
        nullable=True, isin=[-1, 0, 0.5, 1, 2, 3, 4]
    )
    structure-type: Optional[Series[str]] = pa.Field(
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
    if not self.molecule-chembl-id:
        raise ValueError("Molecule ChEMBL ID is required")
    if self.max-phase is not None and not (0 <= self.max-phase <= 4):
        raise ValueError(f"max-phase must be 0-4, got {self.max-phase}")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `molecule-chembl-id` | Primary source |
| PubChem | `cross-references[src="PubChem"]` | Via cross-references |
| DrugBank | `cross-references[src="DrugBank"]` | Via cross-references |
| ChEBI | `cross-references[src="ChEBI"]` | Via cross-references |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "molecule-chembl-id": "CHEMBL25",
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
    "molecule-chembl-id": "CHEMBL25",
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
    "canonical-smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "standard-inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
    "standard-inchi-key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
  }
}
```

### Silver (Normalized)

```json
{
  "entity-id": "CHEMBL25",
  "molecule-chembl-id": "CHEMBL25",
  "content-hash": "sha256:abc123...",
  "-run-id": "550e8400-e29b-41d4-a716-446655440000",
  "-run-type": "incremental",
  "-ingestion-ts": "2024-01-15T10:30:00Z",
  "-dq-warn": false,
  "-index": 0,

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

  "canonical-smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "standard-inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
  "inchi-key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/molecule.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl-structures.py` |
| Pipeline Config | `configs/pipelines/chembl/molecule.yaml` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-01-06 | **BREAKING**: Renamed structure fields for PubChem consistency |
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
