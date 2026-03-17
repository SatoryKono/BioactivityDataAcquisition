# Target Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.24*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `target_id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/target.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Target records represent biological targets including single proteins, protein complexes, protein families, cell lines, tissues, and organisms. Each target can be linked to activities through assays and contains information about component proteins with UniProt accessions.

### Key Relationships
```
Target ◄─── Activity (target_id)
    │
    ├───► Target Component (component-id)
    │       │
    │       └───► UniProt (accession)
    │
    └───► Assay (target_id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion-date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `target-type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for single proteins with UniProt mappings:

| Filter | Values | Purpose |
|--------|--------|---------|
| `target-type` | `["SINGLE PROTEIN"]` | Focus on single proteins |
| `component_accessions` | length = 1 | Single component |
| `component-ids` | length >= 1 | Has component ID |
| `component-types` | contains `["PROTEIN"]` | Protein components |

**Required Fields for Gold**: `pref-name`, `organism`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target_id` | `str` | No | `^CHEMBL\d+$` | ChEMBL target identifier | `targets[].target_id` |

### Core Metadata

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `pref-name` | `str` | Yes | — | Preferred target name | `targets[].pref-name` |
| `organism` | `str` | Yes | — | Organism (e.g., "Homo sapiens") | `targets[].organism` |
| `tax-id` | `int` | Yes | — | NCBI Taxonomy ID | `targets[].tax-id` |
| `species-group-flag` | `bool` | Yes | — | Species group indicator | `targets[].species-group-flag` |

### Classification

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target-type` | `str` | Yes | `isin=[...]` | Target type classification | `targets[].target-type` |

**Valid `target-type` values:**
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
| `target-components` | `str` | Yes | Component proteins/sequences (JSON) | `targets[].target-components` |
| `cross-references` | `str` | Yes | External database links (JSON) | `targets[].cross-references` |

### Flattened Component Fields

These fields are extracted from the `target-components` array for easier querying:

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `component_accessions` | `list[str]` | Yes | UniProt accessions | `target-components[].accession` |
| `component-ids` | `list[int]` | Yes | Component IDs | `target-components[].component-id` |
| `component-types` | `list[str]` | Yes | Component types (PROTEIN, etc.) | `target-components[].component-type` |
| `component-relationships` | `list[str]` | Yes | Relationship types | `target-components[].relationship` |
| `component-descriptions` | `list[str]` | Yes | Component descriptions | `target-components[].component-description` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= target_id) | Yes |
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
| `target_id` | `target_id` | Direct |
| `tax-id` | `tax-id` | `safe-int()` |
| `target-components` | `target-components` | `json.dumps()` |
| `target-components[*].accession` | `component_accessions` | Extract to list |
| `target-components[*].component-id` | `component-ids` | Extract to list |
| `target-components[*].component-type` | `component-types` | Extract to list |
| `cross-references` | `cross-references` | `json.dumps()` |

---

## Validation Rules

### Pandera Schema

```python
class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    target_id: Series[str] = pa.Field(
        nullable=False, str-matches=r"^CHEMBL\d+$"
    )
    target-type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=[
            "SINGLE PROTEIN", "PROTEIN FAMILY", "PROTEIN COMPLEX",
            "CELL-LINE", "TISSUE", "ORGANISM", ...
        ]
    )
    tax-id: Optional[Series[int]] = pa.Field(nullable=True)

    # List fields
    component_accessions: Optional[Series[object]] = pa.Field(nullable=True)
    component-ids: Optional[Series[object]] = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def -validate-invariants(self) -> None:
    if not self.target_id:
        raise ValueError("Target ChEMBL ID is required")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `target_id` | Primary source |
| UniProt | `component_accessions[]` | Via flattened components |
| NCBI Taxonomy | `tax-id` | Direct mapping |
| Gene Ontology | `cross-references[src="GO"]` | Via cross-references |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "target_id": "CHEMBL3921",
  "pref-name": "Heparanase",
  "target-type": "SINGLE PROTEIN",
  "organism": "Homo sapiens",
  "tax-id": 9606,
  "species-group-flag": false,
  "target-components": [
    {
      "accession": "Q9Y251",
      "component-id": 4553,
      "component-type": "PROTEIN",
      "component-description": "Heparanase",
      "relationship": "SINGLE PROTEIN"
    }
  ],
  "cross-references": [
    {"xref-id": "Q9Y251", "xref-name": "UniProt", "xref-src": "UniProt"},
    {"xref-id": "GO:0005576", "xref-name": "extracellular region", "xref-src": "GO"}
  ]
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL3921",
  "target_id": "CHEMBL3921",
  "content_hash": "sha256:def456...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440001",
  "_run_type": "incremental",
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "pref-name": "Heparanase",
  "target-type": "SINGLE PROTEIN",
  "organism": "Homo sapiens",
  "tax-id": 9606,
  "species-group-flag": false,

  "target-components": "[{\"accession\": \"Q9Y251\", ...}]",
  "cross-references": "[{\"xref-id\": \"Q9Y251\", ...}]",

  "component_accessions": ["Q9Y251"],
  "component-ids": [4553],
  "component-types": ["PROTEIN"],
  "component-relationships": ["SINGLE PROTEIN"],
  "component-descriptions": ["Heparanase"]
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/target.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_structures.py` |
| Pipeline Config | `configs/entities/chembl/target.yaml` |
| Target Component Schema | `src/bioetl/domain/schemas/chembl/target_component.py` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
