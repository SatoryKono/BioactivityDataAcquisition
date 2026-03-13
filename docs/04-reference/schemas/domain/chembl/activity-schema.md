# Activity Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.24*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `activity-id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/activity.json`) |
| **Update Frequency** | Weekly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Activity records represent bioactivity measurements from scientific publications and patents. Each record links a molecule to a biological target through an assay, with quantitative or qualitative activity data.

### Key Relationships
```
Activity ───► Molecule (molecule-chembl-id)
    │
    ├───► Target (target-chembl-id)
    │
    ├───► Assay (assay-chembl-id)
    │
    └───► Document (document-chembl-id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion-date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | None | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies strict filters to ensure high-quality data for analysis:

| Filter | Values | Purpose |
|--------|--------|---------|
| `standard-type` | `["IC50", "Ki"]` | Focus on affinity measurements |
| `standard-units` | `["nM"]` | Normalized units |
| `standard-relation` | `["="]` | Exact measurements only |
| `assay-type` | `["B", "F"]` | Binding and Functional assays |
| `potential-duplicate` | `["0"]` | Exclude duplicates |
| `standard-value` | `> 0` | Valid positive values |

**Required Fields for Gold**: `standard-type`, `standard-value`, `standard-units`, `target-chembl-id`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity-id` | `str` | No | — | Primary key (integer as string) | `activities[].activity-id` |

### Foreign Keys

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay-chembl-id` | `str` | No | `^CHEMBL\d+$` | FK to Assay entity | `activities[].assay-chembl-id` |
| `molecule-chembl-id` | `str` | No | `^CHEMBL\d+$` | FK to Molecule entity | `activities[].molecule-chembl-id` |
| `target-chembl-id` | `str` | Yes | `^CHEMBL\d+$` | FK to Target entity | `activities[].target-chembl-id` |
| `document-chembl-id` | `str` | Yes | `^CHEMBL\d+$` | FK to Document entity | `activities[].document-chembl-id` |
| `record-id` | `int` | Yes | — | FK to compound-record | `activities[].record-id` |
| `src-id` | `int` | Yes | — | Source database ID | `activities[].src-id` |

### Standardized Activity Values

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `standard-type` | `str` | Yes | `isin=["IC50", "EC50", "Ki", "Kd", "AC50", "GI50", "Potency", "Inhibition", "% Inhibition", "Activity", "Ratio", "ED50", "ID50"]` | Standardized measurement type | `activities[].standard-type` |
| `standard-value` | `float` | Yes | `ge=0` | Standardized numeric value | `activities[].standard-value` |
| `standard-units` | `str` | Yes | — | Standardized units (e.g., nM) | `activities[].standard-units` |
| `standard-relation` | `str` | Yes | `isin=["=", "<", "<=", ">", ">="]` | Relation operator | `activities[].standard-relation` |
| `standard-flag` | `int` | Yes | `isin=[0, 1]` | 1 if value was standardized | `activities[].standard-flag` |
| `standard-upper-value` | `float` | Yes | — | Upper bound (for ranges) | `activities[].standard-upper-value` |
| `standard-text-value` | `str` | Yes | — | Text-based measurement | `activities[].standard-text-value` |

### Original Activity Values

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `type` | `str` | Yes | — | Original measurement type | `activities[].type` |
| `value` | `float` | Yes | — | Original numeric value | `activities[].value` |
| `units` | `str` | Yes | — | Original units | `activities[].units` |
| `relation` | `str` | Yes | — | Original relation | `activities[].relation` |
| `upper-value` | `float` | Yes | — | Original upper bound | `activities[].upper-value` |
| `text-value` | `str` | Yes | — | Original text value | `activities[].text-value` |

### Derived Metrics

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pchembl-value` | `float` | Yes | `ge=0, le=14` | -log10 molar activity (comparable across types) | `activities[].pchembl-value` |

### Ligand Efficiency Metrics

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `ligand-efficiency-bei` | `float` | Yes | — | Binding Efficiency Index | `activities[].ligand-efficiency.bei` |
| `ligand-efficiency-le` | `float` | Yes | — | Ligand Efficiency | `activities[].ligand-efficiency.le` |
| `ligand-efficiency-lle` | `float` | Yes | — | Lipophilic Ligand Efficiency | `activities[].ligand-efficiency.lle` |
| `ligand-efficiency-sei` | `float` | Yes | — | Surface Efficiency Index | `activities[].ligand-efficiency.sei` |

### Molecule Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `canonical-smiles` | `str` | Yes | — | Canonical SMILES structure | `activities[].canonical-smiles` |
| `molecule-pref-name` | `str` | Yes | — | Preferred molecule name | `activities[].molecule-pref-name` |
| `parent-molecule-chembl-id` | `str` | Yes | — | Parent molecule ID (for salts) | `activities[].parent-molecule-chembl-id` |

### Target Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target-pref-name` | `str` | Yes | — | Preferred target name | `activities[].target-pref-name` |
| `target-organism` | `str` | Yes | — | Target organism (e.g., "Homo sapiens") | `activities[].target-organism` |
| `target-tax-id` | `str` | Yes | — | NCBI Taxonomy ID | `activities[].target-tax-id` |

### Assay Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay-type` | `str` | Yes | — | Assay type code (B=Binding, F=Functional) | `activities[].assay-type` |
| `assay-description` | `str` | Yes | — | Full assay description | `activities[].assay-description` |
| `assay-variant-accession` | `str` | Yes | — | UniProt accession for variants | `activities[].assay-variant-accession` |
| `assay-variant-mutation` | `str` | Yes | — | Mutation description | `activities[].assay-variant-mutation` |

### Ontology Annotations

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `bao-endpoint` | `str` | Yes | `^BAO:\d+$` | BioAssay Ontology endpoint ID | `activities[].bao-endpoint` |
| `bao-format` | `str` | Yes | — | BioAssay Ontology format ID | `activities[].bao-format` |
| `bao-label` | `str` | Yes | — | Human-readable BAO label | `activities[].bao-label` |
| `uo-units` | `str` | Yes | `^UO:\d+$` | Units Ontology ID | `activities[].uo-units` |
| `qudt-units` | `str` | Yes | — | QUDT unit URI | `activities[].qudt-units` |

### Quality Annotations

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity-comment` | `str` | Yes | — | Free-text comment | `activities[].activity-comment` |
| `data-validity-comment` | `str` | Yes | `isin=[...]` | Structured DQ comment | `activities[].data-validity-comment` |
| `potential-duplicate` | `int` | Yes | `isin=[0, 1]` | 1 if likely duplicate | `activities[].potential-duplicate` |

**Valid `data-validity-comment` values:**
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
| `action-type-action-type` | `str` | Yes | — | Action type (e.g., INHIBITOR) | `activities[].action-type.action-type` |
| `action-type-description` | `str` | Yes | — | Action description | `activities[].action-type.description` |
| `action-type-parent-type` | `str` | Yes | — | Parent action category | `activities[].action-type.parent-type` |

### Document Fields (Denormalized)

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `document-journal` | `str` | Yes | — | Journal name | `activities[].document-journal` |
| `document-year` | `float` | Yes | — | Publication year | `activities[].document-year` |

### Other Fields

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `activity-properties` | `str` | Yes | — | JSON string of additional properties | `activities[].activity-properties` |
| `toid` | `int` | Yes | — | Test Occasion ID | `activities[].toid` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= activity-id) | Yes |
| `content_hash` | `str` | No | SHA256 for SCD Type 2 | — |
| `_run_id` | `UUID` | No | Pipeline run correlation ID | No |
| `_run_type` | `Enum` | No | incremental/backfill/rebuild | No |
| `_source_batch_id` | `UUID` | Yes | Lineage reference in metadata sidecar | No |
| `_ingestion_ts` | `Timestamp` | No | Ingestion time (UTC) | No |
| `_dq_warn` | `bool` | No | DQ warning flag | No |
| `_index` | `int` | No | Record index in batch | No |

---

## Transformations

### Bronze → Silver

| Source Field | Target Field | Transformation |
|--------------|--------------|----------------|
| `activity-id` | `activity-id` | `str(value)` |
| `standard-value` | `standard-value` | `safe-float()` |
| `value` | `value` | `safe-float()` |
| `pchembl-value` | `pchembl-value` | `safe-float()` |
| `standard-flag` | `standard-flag` | `safe-int()` |
| `potential-duplicate` | `potential-duplicate` | `safe-int()` |
| `document-year` | `document-year` | `safe-int()` |
| `record-id` | `record-id` | `safe-int()` |
| `src-id` | `src-id` | `safe-int()` |
| `toid` | `toid` | `safe-int()` |
| `ligand-efficiency` | `ligand-efficiency-*` | `flatten-nested-dict()` → 4 float fields |
| `action-type` | `action-type-*` | `flatten-nested-dict()` → 3 str fields |
| `activity-properties` | `activity-properties` | `json.dumps()` if list |

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
    + canonical-json(
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
    activity-id: Series[str] = pa.Field(nullable=False)

    # Foreign Keys
    assay-chembl-id: Series[str] = pa.Field(
        nullable=False, str-matches=r"^CHEMBL\d+$"
    )
    molecule-chembl-id: Series[str] = pa.Field(
        nullable=False, str-matches=r"^CHEMBL\d+$"
    )
    target-chembl-id: Optional[Series[str]] = pa.Field(
        nullable=True, str-matches=r"^CHEMBL\d+$"
    )

    # Standardized Values
    standard-value: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0
    )
    pchembl-value: Optional[Series[float]] = pa.Field(
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
| null-rate | `activity-id` | 0% | Critical (fail batch) |
| null-rate | `molecule-chembl-id` | 0% | Critical (fail batch) |
| null-rate | `assay-chembl-id` | 0% | Critical (fail batch) |
| null-rate | `standard-value` | <5% warn, <20% fail | RULES.md §3.1.2 |
| range | `pchembl-value` | 0-14 | Quarantine |
| regex | `*-chembl-id` | `^CHEMBL\d+$` | Quarantine |
| enum | `standard-relation` | `=, <, <=, >, >=` | Quarantine |

### Entity Invariants

```python
def -validate-invariants(self) -> None:
    if not self.activity-id:
        raise ValueError("Activity ID is required")
    if not self.molecule-chembl-id:
        raise ValueError("Molecule ID is required")
    if self.pchembl-value is not None and self.pchembl-value < 0:
        raise ValueError(f"pChemBL value must be non-negative")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `activity-id` | Primary source |
| PubChem | N/A | Activities not mapped directly |
| ChEMBL Molecule | `molecule-chembl-id` | FK join |
| ChEMBL Target | `target-chembl-id` | FK join |
| UniProt | `target-components.accession` | Via Target entity |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "activity-id": 31864,
  "assay-chembl-id": "CHEMBL872937",
  "assay-description": "In vivo inhibitory activity against human Heparanase",
  "assay-type": "B",
  "assay-variant-accession": null,
  "assay-variant-mutation": null,
  "bao-endpoint": "BAO-0000190",
  "bao-format": "BAO-0000218",
  "bao-label": "organism-based format",
  "canonical-smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "data-validity-comment": null,
  "document-chembl-id": "CHEMBL1146658",
  "document-journal": "Bioorg Med Chem Lett",
  "document-year": 2004,
  "ligand-efficiency": {
    "bei": "14.06",
    "le": "0.26",
    "lle": "1.30",
    "sei": "5.56"
  },
  "molecule-chembl-id": "CHEMBL324340",
  "pchembl-value": "5.60",
  "potential-duplicate": 0,
  "qudt-units": "http://www.openphacts.org/units/Nanomolar",
  "record-id": 208970,
  "relation": "=",
  "src-id": 1,
  "standard-flag": 1,
  "standard-relation": "=",
  "standard-type": "IC50",
  "standard-units": "nM",
  "standard-value": "2500.0",
  "target-chembl-id": "CHEMBL3921",
  "target-organism": "Homo sapiens",
  "target-pref-name": "Heparanase",
  "target-tax-id": "9606",
  "type": "IC50",
  "units": "uM",
  "uo-units": "UO-0000065",
  "value": "2.5"
}
```

### Silver (Normalized)

```json
{
  "entity_id": "31864",
  "activity-id": "31864",
  "content_hash": "sha256:a1b2c3d4e5f6...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "_run_type": "incremental",
  "_source_batch_id": null,
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "assay-chembl-id": "CHEMBL872937",
  "molecule-chembl-id": "CHEMBL324340",
  "target-chembl-id": "CHEMBL3921",
  "document-chembl-id": "CHEMBL1146658",

  "standard-type": "IC50",
  "standard-value": 2500.0,
  "standard-units": "nM",
  "standard-relation": "=",
  "standard-flag": 1,

  "pchembl-value": 5.60,

  "ligand-efficiency-bei": 14.06,
  "ligand-efficiency-le": 0.26,
  "ligand-efficiency-lle": 1.30,
  "ligand-efficiency-sei": 5.56,

  "canonical-smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "target-pref-name": "Heparanase",
  "target-organism": "Homo sapiens",
  "assay-type": "B",

  "type": "IC50",
  "value": 2.5,
  "units": "uM",
  "relation": "=",

  "document-journal": "Bioorg Med Chem Lett",
  "document-year": 2004,
  "potential-duplicate": 0
}
```

### Gold (Filtered & Flattened)

Gold layer contains only records passing gold-filters:
- `standard-type` in `["IC50", "Ki"]`
- `standard-units` = `"nM"`
- `standard-relation` = `"="`
- `standard-value` > 0
- `target-chembl-id` is not null

```json
{
  "entity_id": "31864",
  "activity-id": "31864",
  "content_hash": "sha256:a1b2c3d4e5f6...",

  "molecule-chembl-id": "CHEMBL324340",
  "target-chembl-id": "CHEMBL3921",
  "assay-chembl-id": "CHEMBL872937",

  "standard-type": "IC50",
  "standard-value": 2500.0,
  "standard-units": "nM",
  "pchembl-value": 5.60,

  "canonical-smiles": "Cc1ccc2oc(-c3cccc(N4C(=O)c5ccc(C(=O)O)cc5C4=O)c3)nc2c1",
  "target-pref-name": "Heparanase",
  "target-organism": "Homo sapiens"
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
| Pipeline Config | `configs/entities/chembl/activity.yaml` |
| VCR Cassettes | `tests/fixtures/vcr/TestChemblActivityPipeline.*.yaml` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
