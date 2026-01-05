# Target Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.9*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `target_chembl_id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/target.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Target records represent biological targets including single proteins, protein complexes, protein families, cell lines, tissues, and organisms. Each target can be linked to activities through assays and contains information about component proteins with UniProt accessions.

### Key Relationships
```
Target ◄─── Activity (target_chembl_id)
    │
    ├───► Target Component (component_id)
    │       │
    │       └───► UniProt (accession)
    │
    └───► Assay (target_chembl_id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion_date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `target_type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for single proteins with UniProt mappings:

| Filter | Values | Purpose |
|--------|--------|---------|
| `target_type` | `["SINGLE PROTEIN"]` | Focus on single proteins |
| `component_accessions` | length = 1 | Single component |
| `component_ids` | length >= 1 | Has component ID |
| `component_types` | contains `["PROTEIN"]` | Protein components |

**Required Fields for Gold**: `pref_name`, `organism`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target_chembl_id` | `str` | No | `^CHEMBL\d+$` | ChEMBL target identifier | `targets[].target_chembl_id` |

### Core Metadata

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pref_name` | `str` | Yes | — | Preferred target name | `targets[].pref_name` |
| `organism` | `str` | Yes | — | Organism (e.g., "Homo sapiens") | `targets[].organism` |
| `tax_id` | `int` | Yes | — | NCBI Taxonomy ID | `targets[].tax_id` |
| `species_group_flag` | `bool` | Yes | — | Species group indicator | `targets[].species_group_flag` |

### Classification

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target_type` | `str` | Yes | `isin=[...]` | Target type classification | `targets[].target_type` |

**Valid `target_type` values:**
- `SINGLE PROTEIN` - Single protein target
- `PROTEIN FAMILY` - Group of related proteins
- `PROTEIN COMPLEX` - Multi-subunit protein
- `PROTEIN COMPLEX GROUP` - Group of complexes
- `SELECTIVITY GROUP` - Selectivity panel
- `CHIMERIC PROTEIN` - Fusion protein
- `CELL-LINE` - Cell line target
- `TISSUE` - Tissue target
- `ORGANISM` - Whole organism
- `MACROMOLECULE` - DNA/RNA targets
- `SMALL MOLECULE` - Small molecule target
- `LIPID` - Lipid target
- `METAL` - Metal target
- `UNKNOWN` - Unknown type

### Complex Fields (JSON Serialized)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `target_components` | `str` | Yes | Component proteins/sequences (JSON) | `targets[].target_components` |
| `cross_references` | `str` | Yes | External database links (JSON) | `targets[].cross_references` |

### Flattened Component Fields

These fields are extracted from the `target_components` array for easier querying:

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `component_accessions` | `list[str]` | Yes | UniProt accessions | `target_components[].accession` |
| `component_ids` | `list[int]` | Yes | Component IDs | `target_components[].component_id` |
| `component_types` | `list[str]` | Yes | Component types (PROTEIN, etc.) | `target_components[].component_type` |
| `component_relationships` | `list[str]` | Yes | Relationship types | `target_components[].relationship` |
| `component_descriptions` | `list[str]` | Yes | Component descriptions | `target_components[].component_description` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= target_chembl_id) | Yes |
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
| `target_chembl_id` | `target_chembl_id` | Direct |
| `tax_id` | `tax_id` | `safe_int()` |
| `target_components` | `target_components` | `json.dumps()` |
| `target_components[*].accession` | `component_accessions` | Extract to list |
| `target_components[*].component_id` | `component_ids` | Extract to list |
| `target_components[*].component_type` | `component_types` | Extract to list |
| `cross_references` | `cross_references` | `json.dumps()` |

---

## Validation Rules

### Pandera Schema

```python
class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    target_chembl_id: Series[str] = pa.Field(
        nullable=False, str_matches=r"^CHEMBL\d+$"
    )
    target_type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=[
            "SINGLE PROTEIN", "PROTEIN FAMILY", "PROTEIN COMPLEX",
            "CELL-LINE", "TISSUE", "ORGANISM", ...
        ]
    )
    tax_id: Optional[Series[int]] = pa.Field(nullable=True)

    # List fields
    component_accessions: Optional[Series[object]] = pa.Field(nullable=True)
    component_ids: Optional[Series[object]] = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def _validate_invariants(self) -> None:
    if not self.target_chembl_id:
        raise ValueError("Target ChEMBL ID is required")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `target_chembl_id` | Primary source |
| UniProt | `component_accessions[]` | Via flattened components |
| NCBI Taxonomy | `tax_id` | Direct mapping |
| Gene Ontology | `cross_references[src="GO"]` | Via cross_references |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "target_chembl_id": "CHEMBL3921",
  "pref_name": "Heparanase",
  "target_type": "SINGLE PROTEIN",
  "organism": "Homo sapiens",
  "tax_id": 9606,
  "species_group_flag": false,
  "target_components": [
    {
      "accession": "Q9Y251",
      "component_id": 4553,
      "component_type": "PROTEIN",
      "component_description": "Heparanase",
      "relationship": "SINGLE PROTEIN"
    }
  ],
  "cross_references": [
    {"xref_id": "Q9Y251", "xref_name": "UniProt", "xref_src": "UniProt"},
    {"xref_id": "GO:0005576", "xref_name": "extracellular region", "xref_src": "GO"}
  ]
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL3921",
  "target_chembl_id": "CHEMBL3921",
  "content_hash": "sha256:def456...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440001",
  "_run_type": "incremental",
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "pref_name": "Heparanase",
  "target_type": "SINGLE PROTEIN",
  "organism": "Homo sapiens",
  "tax_id": 9606,
  "species_group_flag": false,

  "target_components": "[{\"accession\": \"Q9Y251\", ...}]",
  "cross_references": "[{\"xref_id\": \"Q9Y251\", ...}]",

  "component_accessions": ["Q9Y251"],
  "component_ids": [4553],
  "component_types": ["PROTEIN"],
  "component_relationships": ["SINGLE PROTEIN"],
  "component_descriptions": ["Heparanase"]
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/target.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_structures.py` |
| Pipeline Config | `configs/pipelines/chembl/target.yaml` |
| Target Component Schema | `src/bioetl/domain/schemas/chembl/target_component.py` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
