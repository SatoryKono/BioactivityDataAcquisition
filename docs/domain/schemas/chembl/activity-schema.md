# Activity Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.9*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `activity_id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/activity.json`) |
| **Update Frequency** | Weekly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Activity records represent bioactivity measurements from scientific publications and patents. Each record links a molecule to a biological target through an assay, with quantitative or qualitative activity data.

### Key Relationships
```
Activity ───► Molecule (molecule_chembl_id)
    │
    ├───► Target (target_chembl_id)
    │
    ├───► Assay (assay_chembl_id)
    │
    └───► Document (document_chembl_id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion_date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | None | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies strict filters to ensure high-quality data for analysis:

| Filter | Values | Purpose |
|--------|--------|---------|
| `standard_type` | `["IC50", "Ki"]` | Focus on affinity measurements |
| `standard_units` | `["nM"]` | Normalized units |
| `standard_relation` | `["="]` | Exact measurements only |
| `assay_type` | `["B", "F"]` | Binding and Functional assays |
| `potential_duplicate` | `["0"]` | Exclude duplicates |
| `standard_value` | `> 0` | Valid positive values |

**Required Fields for Gold**: `standard_type`, `standard_value`, `standard_units`, `target_chembl_id`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity_id` | `str` | No | — | Primary key (integer as string) | `activities[].activity_id` |

### Foreign Keys

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay_chembl_id` | `str` | No | `^CHEMBL\d+$` | FK to Assay entity | `activities[].assay_chembl_id` |
| `molecule_chembl_id` | `str` | No | `^CHEMBL\d+$` | FK to Molecule entity | `activities[].molecule_chembl_id` |
| `target_chembl_id` | `str` | Yes | `^CHEMBL\d+$` | FK to Target entity | `activities[].target_chembl_id` |
| `document_chembl_id` | `str` | Yes | `^CHEMBL\d+$` | FK to Document entity | `activities[].document_chembl_id` |
| `record_id` | `int` | Yes | — | FK to compound_record | `activities[].record_id` |
| `src_id` | `int` | Yes | — | Source database ID | `activities[].src_id` |

### Standardized Activity Values

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `standard_type` | `str` | Yes | `isin=["IC50", "EC50", "Ki", "Kd", "AC50", "GI50", "Potency", "Inhibition", "% Inhibition", "Activity", "Ratio", "ED50", "ID50"]` | Standardized measurement type | `activities[].standard_type` |
| `standard_value` | `float` | Yes | `ge=0` | Standardized numeric value | `activities[].standard_value` |
| `standard_units` | `str` | Yes | — | Standardized units (e.g., nM) | `activities[].standard_units` |
| `standard_relation` | `str` | Yes | `isin=["=", "<", "<=", ">", ">="]` | Relation operator | `activities[].standard_relation` |
| `standard_flag` | `int` | Yes | `isin=[0, 1]` | 1 if value was standardized | `activities[].standard_flag` |
| `standard_upper_value` | `float` | Yes | — | Upper bound (for ranges) | `activities[].standard_upper_value` |
| `standard_text_value` | `str` | Yes | — | Text-based measurement | `activities[].standard_text_value` |

### Original Activity Values

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `type` | `str` | Yes | — | Original measurement type | `activities[].type` |
| `value` | `float` | Yes | — | Original numeric value | `activities[].value` |
| `units` | `str` | Yes | — | Original units | `activities[].units` |
| `relation` | `str` | Yes | — | Original relation | `activities[].relation` |
| `upper_value` | `float` | Yes | — | Original upper bound | `activities[].upper_value` |
| `text_value` | `str` | Yes | — | Original text value | `activities[].text_value` |

### Derived Metrics

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pchembl_value` | `float` | Yes | `ge=0, le=14` | -log10 molar activity (comparable across types) | `activities[].pchembl_value` |

### Ligand Efficiency Metrics

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `ligand_efficiency_bei` | `float` | Yes | — | Binding Efficiency Index | `activities[].ligand_efficiency.bei` |
| `ligand_efficiency_le` | `float` | Yes | — | Ligand Efficiency | `activities[].ligand_efficiency.le` |
| `ligand_efficiency_lle` | `float` | Yes | — | Lipophilic Ligand Efficiency | `activities[].ligand_efficiency.lle` |
| `ligand_efficiency_sei` | `float` | Yes | — | Surface Efficiency Index | `activities[].ligand_efficiency.sei` |

### Molecule Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `canonical_smiles` | `str` | Yes | — | Canonical SMILES structure | `activities[].canonical_smiles` |
| `molecule_pref_name` | `str` | Yes | — | Preferred molecule name | `activities[].molecule_pref_name` |
| `parent_molecule_chembl_id` | `str` | Yes | — | Parent molecule ID (for salts) | `activities[].parent_molecule_chembl_id` |

### Target Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target_pref_name` | `str` | Yes | — | Preferred target name | `activities[].target_pref_name` |
| `target_organism` | `str` | Yes | — | Target organism (e.g., "Homo sapiens") | `activities[].target_organism` |
| `target_tax_id` | `str` | Yes | — | NCBI Taxonomy ID | `activities[].target_tax_id` |

### Assay Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay_type` | `str` | Yes | — | Assay type code (B=Binding, F=Functional) | `activities[].assay_type` |
| `assay_description` | `str` | Yes | — | Full assay description | `activities[].assay_description` |
| `assay_variant_accession` | `str` | Yes | — | UniProt accession for variants | `activities[].assay_variant_accession` |
| `assay_variant_mutation` | `str` | Yes | — | Mutation description | `activities[].assay_variant_mutation` |

### Ontology Annotations

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `bao_endpoint` | `str` | Yes | `^BAO:\d+$` | BioAssay Ontology endpoint ID | `activities[].bao_endpoint` |
| `bao_format` | `str` | Yes | — | BioAssay Ontology format ID | `activities[].bao_format` |
| `bao_label` | `str` | Yes | — | Human-readable BAO label | `activities[].bao_label` |
| `uo_units` | `str` | Yes | `^UO:\d+$` | Units Ontology ID | `activities[].uo_units` |
| `qudt_units` | `str` | Yes | — | QUDT unit URI | `activities[].qudt_units` |

### Quality Annotations

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity_comment` | `str` | Yes | — | Free-text comment | `activities[].activity_comment` |
| `data_validity_comment` | `str` | Yes | `isin=[...]` | Structured DQ comment | `activities[].data_validity_comment` |
| `potential_duplicate` | `int` | Yes | `isin=[0, 1]` | 1 if likely duplicate | `activities[].potential_duplicate` |

**Valid `data_validity_comment` values:**
- `"Potential missing data"`
- `"Potential author error"`
- `"Manually validated"`
- `"Potential transcription error"`
- `"Outside typical range"`
- `"Non standard unit for type"`
- `"Author confirmed error"`

### Action Type (Flattened)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `action_type_action_type` | `str` | Yes | — | Action type (e.g., INHIBITOR) | `activities[].action_type.action_type` |
| `action_type_description` | `str` | Yes | — | Action description | `activities[].action_type.description` |
| `action_type_parent_type` | `str` | Yes | — | Parent action category | `activities[].action_type.parent_type` |

### Document Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `document_journal` | `str` | Yes | — | Journal name | `activities[].document_journal` |
| `document_year` | `float` | Yes | — | Publication year | `activities[].document_year` |

### Other Fields

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity_properties` | `str` | Yes | — | JSON string of additional properties | `activities[].activity_properties` |
| `toid` | `int` | Yes | — | Test Occasion ID | `activities[].toid` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= activity_id) | Yes |
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
| `activity_id` | `activity_id` | `str(value)` |
| `standard_value` | `standard_value` | `safe_float()` |
| `value` | `value` | `safe_float()` |
| `pchembl_value` | `pchembl_value` | `safe_float()` |
| `standard_flag` | `standard_flag` | `safe_int()` |
| `potential_duplicate` | `potential_duplicate` | `safe_int()` |
| `document_year` | `document_year` | `safe_int()` |
| `record_id` | `record_id` | `safe_int()` |
| `src_id` | `src_id` | `safe_int()` |
| `toid` | `toid` | `safe_int()` |
| `ligand_efficiency` | `ligand_efficiency_*` | `flatten_nested_dict()` → 4 float fields |
| `action_type` | `action_type_*` | `flatten_nested_dict()` → 3 str fields |
| `activity_properties` | `activity_properties` | `json.dumps()` if list |

### Normalization Rules (RULES.md §2.8.1)

| Data Type | Normalization |
|-----------|---------------|
| **Floats** | `round(val, 10)` |
| **Dates** | ISO `YYYY-MM-DD` |
| **Strings** | `strip()` |
| **NaN/Inf** | → `null` |

### Content Hash Calculation

```python
sha256(
    provider="chembl"
    + canonical_json(
        record,
        exclude=["_run_id", "_run_type", "_source_batch_id", "_ingestion_ts", "_dq_warn", "_index"]
    )
)
```

---

## Validation Rules

### Pandera Schema

```python
class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver layer."""

    # Primary Key
    activity_id: Series[str] = pa.Field(nullable=False)

    # Foreign Keys
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False, str_matches=r"^CHEMBL\d+$"
    )
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False, str_matches=r"^CHEMBL\d+$"
    )
    target_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True, str_matches=r"^CHEMBL\d+$"
    )

    # Standardized Values
    standard_value: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0
    )
    pchembl_value: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0, le=14
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### DQ Checks

| Check | Column | Threshold | Action |
|-------|--------|-----------|--------|
| null_rate | `activity_id` | 0% | Critical (fail batch) |
| null_rate | `molecule_chembl_id` | 0% | Critical (fail batch) |
| null_rate | `assay_chembl_id` | 0% | Critical (fail batch) |
| null_rate | `standard_value` | <5% warn, <20% fail | RULES.md §3.1.2 |
| range | `pchembl_value` | 0-14 | Quarantine |
| regex | `*_chembl_id` | `^CHEMBL\d+$` | Quarantine |
| enum | `standard_relation` | `=, <, <=, >, >=` | Quarantine |

### Entity Invariants

```python
def _validate_invariants(self) -> None:
    if not self.activity_id:
        raise ValueError("Activity ID is required")
    if not self.molecule_chembl_id:
        raise ValueError("Molecule ID is required")
    if self.pchembl_value is not None and self.pchembl_value < 0:
        raise ValueError(f"pChemBL value must be non-negative")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `activity_id` | Primary source |
| PubChem | N/A | Activities not mapped directly |
| ChEMBL Molecule | `molecule_chembl_id` | FK join |
| ChEMBL Target | `target_chembl_id` | FK join |
| UniProt | `target_components.accession` | Via Target entity |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "activity_id": 31864,
  "assay_chembl_id": "CHEMBL872937",
  "assay_description": "In vivo inhibitory activity against human Heparanase",
  "assay_type": "B",
  "assay_variant_accession": null,
  "assay_variant_mutation": null,
  "bao_endpoint": "BAO_0000190",
  "bao_format": "BAO_0000218",
  "bao_label": "organism-based format",
  "canonical_smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "data_validity_comment": null,
  "document_chembl_id": "CHEMBL1146658",
  "document_journal": "Bioorg Med Chem Lett",
  "document_year": 2004,
  "ligand_efficiency": {
    "bei": "14.06",
    "le": "0.26",
    "lle": "1.30",
    "sei": "5.56"
  },
  "molecule_chembl_id": "CHEMBL324340",
  "pchembl_value": "5.60",
  "potential_duplicate": 0,
  "qudt_units": "http://www.openphacts.org/units/Nanomolar",
  "record_id": 208970,
  "relation": "=",
  "src_id": 1,
  "standard_flag": 1,
  "standard_relation": "=",
  "standard_type": "IC50",
  "standard_units": "nM",
  "standard_value": "2500.0",
  "target_chembl_id": "CHEMBL3921",
  "target_organism": "Homo sapiens",
  "target_pref_name": "Heparanase",
  "target_tax_id": "9606",
  "type": "IC50",
  "units": "uM",
  "uo_units": "UO_0000065",
  "value": "2.5"
}
```

### Silver (Normalized)

```json
{
  "entity_id": "31864",
  "activity_id": "31864",
  "content_hash": "sha256:a1b2c3d4e5f6...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "_run_type": "incremental",
  "_source_batch_id": null,
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "assay_chembl_id": "CHEMBL872937",
  "molecule_chembl_id": "CHEMBL324340",
  "target_chembl_id": "CHEMBL3921",
  "document_chembl_id": "CHEMBL1146658",

  "standard_type": "IC50",
  "standard_value": 2500.0,
  "standard_units": "nM",
  "standard_relation": "=",
  "standard_flag": 1,

  "pchembl_value": 5.60,

  "ligand_efficiency_bei": 14.06,
  "ligand_efficiency_le": 0.26,
  "ligand_efficiency_lle": 1.30,
  "ligand_efficiency_sei": 5.56,

  "canonical_smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "target_pref_name": "Heparanase",
  "target_organism": "Homo sapiens",
  "assay_type": "B",

  "type": "IC50",
  "value": 2.5,
  "units": "uM",
  "relation": "=",

  "document_journal": "Bioorg Med Chem Lett",
  "document_year": 2004,
  "potential_duplicate": 0
}
```

### Gold (Filtered & Flattened)

Gold layer contains only records passing gold_filters:
- `standard_type` in `["IC50", "Ki"]`
- `standard_units` = `"nM"`
- `standard_relation` = `"="`
- `standard_value` > 0
- `target_chembl_id` is not null

```json
{
  "entity_id": "31864",
  "activity_id": "31864",
  "content_hash": "sha256:a1b2c3d4e5f6...",

  "molecule_chembl_id": "CHEMBL324340",
  "target_chembl_id": "CHEMBL3921",
  "assay_chembl_id": "CHEMBL872937",

  "standard_type": "IC50",
  "standard_value": 2500.0,
  "standard_units": "nM",
  "pchembl_value": 5.60,

  "canonical_smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "target_pref_name": "Heparanase",
  "target_organism": "Homo sapiens"
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/activity.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_activity.py` |
| Base Schema | `src/bioetl/domain/schemas/base.py` |
| Transformer | `src/bioetl/application/pipelines/chembl/activity_transformer.py` |
| Pipeline Config | `configs/pipelines/chembl/activity.yaml` |
| VCR Cassettes | `tests/fixtures/vcr/TestChemblActivityPipeline.*.yaml` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
