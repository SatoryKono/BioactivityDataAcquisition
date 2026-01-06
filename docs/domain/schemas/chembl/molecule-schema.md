# Molecule Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.10*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `molecule_chembl_id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/molecule.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Molecule records represent chemical compounds including small molecules, proteins, antibodies, and oligonucleotides. Each record contains structural information, calculated properties, clinical development status, and regulatory annotations.

### Key Relationships
```
Molecule ◄─── Activity (molecule_chembl_id)
    │
    └──► Parent Molecule (hierarchy_parent_chembl_id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion_date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `molecule_type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for high-quality drug-like molecules:

| Filter | Values | Purpose |
|--------|--------|---------|
| `molecule_type` | `["Small molecule"]` | Focus on small molecules |
| `structure_type` | `["MOL"]` | Molecules with structures |
| `inorganic_flag` | `["0"]` | Organic compounds only |

**Required Fields for Gold**: `molecule_chembl_id`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `molecule_chembl_id` | `str` | No | `^CHEMBL\d+$` | ChEMBL molecule identifier | `molecules[].molecule_chembl_id` |

### Core Properties

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pref_name` | `str` | Yes | — | Preferred name (INN, USAN) | `molecules[].pref_name` |
| `molecule_type` | `str` | Yes | `isin=[...]` | Molecule type classification | `molecules[].molecule_type` |
| `structure_type` | `str` | Yes | `isin=["MOL","SEQ","BOTH","NONE"]` | Structure data type | `molecules[].structure_type` |
| `max_phase` | `float` | Yes | `isin=[-1,0,0.5,1,2,3,4]` | Maximum clinical phase reached | `molecules[].max_phase` |
| `first_approval` | `int` | Yes | — | Year of first regulatory approval | `molecules[].first_approval` |

**Valid `molecule_type` values:**
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
| `therapeutic_flag` | `bool` | Yes | — | Has therapeutic application | `molecules[].therapeutic_flag` |
| `black_box_warning` | `int` | Yes | `isin=[0,1]` | FDA black box warning | `molecules[].black_box_warning` |
| `withdrawn_flag` | `bool` | Yes | — | Withdrawn from market | `molecules[].withdrawn_flag` |
| `first_in_class` | `int` | Yes | `isin=[0,1]` | First-in-class mechanism | `molecules[].first_in_class` |

### Chemical Classification Flags

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `natural_product` | `int` | Yes | `isin=[-1,0,1]` | Natural product origin | `molecules[].natural_product` |
| `prodrug` | `int` | Yes | `isin=[0,1]` | Prodrug that requires activation | `molecules[].prodrug` |
| `inorganic_flag` | `int` | Yes | `isin=[0,1]` | Inorganic compound | `molecules[].inorganic_flag` |
| `polymer_flag` | `int` | Yes | `isin=[0,1]` | Polymer | `molecules[].polymer_flag` |

### Complex Fields (JSON Serialized)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `molecule_hierarchy` | `str` | Yes | Parent/child relationships (JSON) | `molecules[].molecule_hierarchy` |
| `molecule_properties` | `str` | Yes | Calculated molecular properties (JSON) | `molecules[].molecule_properties` |
| `molecule_structures` | `str` | Yes | SMILES, InChI structures (JSON) | `molecules[].molecule_structures` |
| `molecule_synonyms` | `str` | Yes | Alternative names (JSON) | `molecules[].molecule_synonyms` |
| `cross_references` | `str` | Yes | External database links (JSON) | `molecules[].cross_references` |
| `atc_classifications` | `str` | Yes | WHO ATC codes (JSON) | `molecules[].atc_classifications` |

### Flattened Hierarchy Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `hierarchy_parent_chembl_id` | `str` | Yes | Parent molecule (for salts) | `molecule_hierarchy.parent_chembl_id` |
| `hierarchy_active_chembl_id` | `str` | Yes | Active moiety | `molecule_hierarchy.active_chembl_id` |

### Flattened Property Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `property_alogp` | `float` | Yes | Calculated ALogP | `molecule_properties.alogp` |
| `property_mw_freebase` | `float` | Yes | Molecular weight (freebase) | `molecule_properties.mw_freebase` |
| `property_full_mwt` | `float` | Yes | Full molecular weight | `molecule_properties.full_mwt` |
| `property_hba` | `int` | Yes | H-bond acceptor count | `molecule_properties.hba` |
| `property_hbd` | `int` | Yes | H-bond donor count | `molecule_properties.hbd` |
| `property_psa` | `float` | Yes | Polar surface area | `molecule_properties.psa` |
| `property_rtb` | `int` | Yes | Rotatable bond count | `molecule_properties.rtb` |
| `property_ro5_violations` | `int` | Yes | Lipinski Rule of 5 violations | `molecule_properties.num_ro5_violations` |
| `property_heavy_atoms` | `int` | Yes | Heavy atom count | `molecule_properties.heavy_atoms` |
| `property_aromatic_rings` | `int` | Yes | Aromatic ring count | `molecule_properties.aromatic_rings` |
| `property_qed_weighted` | `float` | Yes | QED drug-likeness score | `molecule_properties.qed_weighted` |

### Flattened Structure Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `structure_canonical_smiles` | `str` | Yes | Canonical SMILES | `molecule_structures.canonical_smiles` |
| `structure_standard_inchi` | `str` | Yes | Standard InChI | `molecule_structures.standard_inchi` |
| `structure_standard_inchi_key` | `str` | Yes | Standard InChI Key | `molecule_structures.standard_inchi_key` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= molecule_chembl_id) | Yes |
| `content_hash` | `str` | No | SHA256 for SCD Type 2 | — |
| `_run_id` | `UUID` | No | Pipeline run correlation ID | No |
| `_run_type` | `Enum` | No | incremental/backfill/rebuild | No |
| `_source_batch_id` | `UUID` | Yes | FK to lineage_log | No |
| `_ingestion_ts` | `Timestamp` | No | Ingestion time (UTC) | No |
| `_dq_warn` | `bool` | No | DQ warning flag | No |
| `_index` | `int` | No | Record index in batch | No |

---

## Transformations

### Bronze → Silver

| Source Field | Target Field | Transformation |
|--------------|--------------|----------------|
| `molecule_chembl_id` | `molecule_chembl_id` | Direct |
| `max_phase` | `max_phase` | `safe_float()` |
| `first_approval` | `first_approval` | `safe_int()` |
| `molecule_hierarchy` | `molecule_hierarchy` | `json.dumps()` |
| `molecule_hierarchy.parent_chembl_id` | `hierarchy_parent_chembl_id` | Flatten |
| `molecule_properties` | `molecule_properties` | `json.dumps()` |
| `molecule_properties.*` | `property_*` | Flatten & convert |
| `molecule_structures` | `molecule_structures` | `json.dumps()` |
| `molecule_structures.*` | `structure_*` | Flatten |

---

## Validation Rules

### Pandera Schema

```python
class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False, str_matches=r"^CHEMBL\d+$"
    )
    max_phase: Optional[Series[float]] = pa.Field(
        nullable=True, isin=[-1, 0, 0.5, 1, 2, 3, 4]
    )
    structure_type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=["MOL", "SEQ", "BOTH", "NONE"]
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def _validate_invariants(self) -> None:
    if not self.molecule_chembl_id:
        raise ValueError("Molecule ChEMBL ID is required")
    if self.max_phase is not None and not (0 <= self.max_phase <= 4):
        raise ValueError(f"max_phase must be 0-4, got {self.max_phase}")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `molecule_chembl_id` | Primary source |
| PubChem | `cross_references[src="PubChem"]` | Via cross_references |
| DrugBank | `cross_references[src="DrugBank"]` | Via cross_references |
| ChEBI | `cross_references[src="ChEBI"]` | Via cross_references |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "molecule_chembl_id": "CHEMBL25",
  "pref_name": "ASPIRIN",
  "molecule_type": "Small molecule",
  "structure_type": "MOL",
  "max_phase": 4,
  "first_approval": 1950,
  "oral": true,
  "parenteral": false,
  "topical": true,
  "black_box_warning": 0,
  "therapeutic_flag": true,
  "molecule_hierarchy": {
    "molecule_chembl_id": "CHEMBL25",
    "parent_chembl_id": "CHEMBL25"
  },
  "molecule_properties": {
    "alogp": 1.31,
    "full_mwt": 180.16,
    "hba": 4,
    "hbd": 1,
    "psa": 63.6,
    "rtb": 3,
    "num_ro5_violations": 0,
    "qed_weighted": 0.56
  },
  "molecule_structures": {
    "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "standard_inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
    "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
  }
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL25",
  "molecule_chembl_id": "CHEMBL25",
  "content_hash": "sha256:abc123...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "_run_type": "incremental",
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "pref_name": "ASPIRIN",
  "molecule_type": "Small molecule",
  "structure_type": "MOL",
  "max_phase": 4.0,
  "first_approval": 1950,

  "oral": true,
  "parenteral": false,
  "topical": true,
  "black_box_warning": 0,
  "therapeutic_flag": true,

  "hierarchy_parent_chembl_id": "CHEMBL25",
  "property_alogp": 1.31,
  "property_full_mwt": 180.16,
  "property_hba": 4,
  "property_hbd": 1,
  "property_psa": 63.6,
  "property_rtb": 3,
  "property_ro5_violations": 0,
  "property_qed_weighted": 0.56,

  "structure_canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "structure_standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/molecule.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_structures.py` |
| Pipeline Config | `configs/pipelines/chembl/molecule.yaml` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
