# Assay Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.9*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `assay_chembl_id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/assay.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Assay records define the experimental conditions under which bioactivity measurements were made. Each assay links to a target and contains information about the assay type, biological context (organism, tissue, cell type), and confidence of target assignment.

### Key Relationships
```
Assay ◄─── Activity (assay_chembl_id)
    │
    ├───► Target (target_chembl_id)
    │
    ├───► Document (document_chembl_id)
    │
    └───► Cell Line (cell_chembl_id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion_date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `assay_type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for high-confidence assays:

| Filter | Values | Purpose |
|--------|--------|---------|
| `assay_type` | `["B", "F"]` | Binding and Functional only |
| `confidence_score` | `["8", "9"]` | High confidence (0-9 scale) |
| `relationship_type` | `["D"]` | Direct target interaction |

**Required Fields for Gold**: `assay_type`, `description`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay_chembl_id` | `str` | No | `^CHEMBL\d+$` | ChEMBL assay identifier | `assays[].assay_chembl_id` |

### Description & Classification

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `description` | `str` | Yes | — | Full assay description | `assays[].description` |
| `assay_type` | `str` | Yes | `isin=["B","F","A","T","P","U"]` | Assay type code | `assays[].assay_type` |
| `assay_test_type` | `str` | Yes | `isin=["In vivo","In vitro","Ex vivo"]` | Test type | `assays[].assay_test_type` |
| `assay_category` | `str` | Yes | `isin=[...]` | Assay category | `assays[].assay_category` |
| `assay_group` | `str` | Yes | — | Assay group | `assays[].assay_group` |
| `assay_pref_name` | `str` | Yes | — | Preferred assay name | `assays[].assay_pref_name` |

**Assay Type Codes:**
| Code | Description |
|------|-------------|
| `B` | Binding assay |
| `F` | Functional assay |
| `A` | ADMET assay |
| `T` | Toxicity assay |
| `P` | Physicochemical assay |
| `U` | Unclassified |

**Assay Categories:**
- `screening` - High-throughput screening
- `confirmatory` - Confirmatory assay
- `panel` - Panel assay
- `summary` - Summary data
- `other` - Other category

### Biological Context

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay_organism` | `str` | Yes | — | Assay organism | `assays[].assay_organism` |
| `assay_tax_id` | `int` | Yes | — | NCBI Taxonomy ID | `assays[].assay_tax_id` |
| `assay_strain` | `str` | Yes | — | Strain | `assays[].assay_strain` |
| `assay_tissue` | `str` | Yes | — | Tissue | `assays[].assay_tissue` |
| `assay_cell_type` | `str` | Yes | — | Cell type | `assays[].assay_cell_type` |
| `assay_subcellular_fraction` | `str` | Yes | — | Subcellular fraction | `assays[].assay_subcellular_fraction` |

### Foreign Keys

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target_chembl_id` | `str` | Yes | `^CHEMBL\d+$` | FK to Target | `assays[].target_chembl_id` |
| `document_chembl_id` | `str` | Yes | `^CHEMBL\d+$` | FK to Document | `assays[].document_chembl_id` |
| `cell_chembl_id` | `str` | Yes | — | FK to Cell Line | `assays[].cell_chembl_id` |
| `tissue_chembl_id` | `str` | Yes | — | FK to Tissue | `assays[].tissue_chembl_id` |
| `src_id` | `int` | Yes | — | Source database ID | `assays[].src_id` |
| `src_assay_id` | `str` | Yes | — | Source assay ID | `assays[].src_assay_id` |

### Target Relationship & Confidence

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `relationship_type` | `str` | Yes | `isin=["D","H","M","N","S","U"]` | Target relationship | `assays[].relationship_type` |
| `relationship_description` | `str` | Yes | — | Relationship description | `assays[].relationship_description` |
| `confidence_score` | `int` | Yes | `ge=0, le=9` | Target confidence (0-9) | `assays[].confidence_score` |
| `confidence_description` | `str` | Yes | — | Confidence description | `assays[].confidence_description` |

**Relationship Type Codes:**
| Code | Description |
|------|-------------|
| `D` | Direct interaction |
| `H` | Homologous target |
| `M` | Molecular target |
| `N` | Non-molecular mechanism |
| `S` | Substrate/product |
| `U` | Unknown |

### BioAssay Ontology

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `bao_format` | `str` | Yes | `^BAO:\d+$` | BAO assay format ID | `assays[].bao_format` |
| `bao_label` | `str` | Yes | — | BAO format label | `assays[].bao_label` |

### Variant Information (Flattened)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `variant_accession` | `str` | Yes | UniProt accession | `variant_sequence.accession` |
| `variant_isoform` | `str` | Yes | Isoform identifier | `variant_sequence.isoform` |
| `variant_mutation` | `str` | Yes | Mutation (e.g., V600E) | `variant_sequence.mutation` |
| `variant_organism` | `str` | Yes | Variant organism | `variant_sequence.organism` |
| `variant_sequence` | `str` | Yes | Amino acid sequence | `variant_sequence.sequence` |
| `variant_tax_id` | `int` | Yes | Variant taxonomy ID | `variant_sequence.tax_id` |
| `variant_sequence_json` | `str` | Yes | Full JSON (forensic) | JSON of variant_sequence |

### Other Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `score` | `float` | Yes | Assay score | `assays[].score` |
| `aidx` | `str` | Yes | Assay index | `assays[].aidx` |

### Complex Fields (JSON Serialized)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `assay_classifications` | `str` | Yes | Classification hierarchy (JSON) | `assays[].assay_classifications` |
| `assay_parameters` | `str` | Yes | Assay parameters (JSON) | `assays[].assay_parameters` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= assay_chembl_id) | Yes |
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
| `assay_chembl_id` | `assay_chembl_id` | Direct |
| `assay_tax_id` | `assay_tax_id` | `safe_int()` |
| `confidence_score` | `confidence_score` | `safe_int()` |
| `variant_sequence` | `variant_*` | Flatten nested dict |
| `variant_sequence` | `variant_sequence_json` | `json.dumps()` |
| `assay_classifications` | `assay_classifications` | `json.dumps()` |
| `assay_parameters` | `assay_parameters` | `json.dumps()` |

---

## Validation Rules

### Pandera Schema

```python
class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    assay_chembl_id: Series[str] = pa.Field(
        nullable=False, str_matches=r"^CHEMBL\d+$"
    )
    assay_type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=["B", "F", "A", "T", "P", "U"]
    )
    confidence_score: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=9
    )
    target_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True, str_matches=r"^CHEMBL\d+$"
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def _validate_invariants(self) -> None:
    if not self.assay_chembl_id:
        raise ValueError("Assay ChEMBL ID is required")
    if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
        raise ValueError(f"Confidence score must be 0-9, got {self.confidence_score}")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `assay_chembl_id` | Primary source |
| BioAssay Ontology | `bao_format` | Via BAO ID |
| PubChem BioAssay | `src_assay_id` (when src_id=7) | Source mapping |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "assay_chembl_id": "CHEMBL872937",
  "description": "In vivo inhibitory activity against human Heparanase",
  "assay_type": "B",
  "assay_test_type": "In vivo",
  "assay_organism": "Homo sapiens",
  "assay_tax_id": 9606,
  "target_chembl_id": "CHEMBL3921",
  "document_chembl_id": "CHEMBL1146658",
  "confidence_score": 9,
  "confidence_description": "Direct single protein target assigned",
  "relationship_type": "D",
  "relationship_description": "Direct protein target assigned",
  "bao_format": "BAO_0000218",
  "bao_label": "organism-based format",
  "src_id": 1
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL872937",
  "assay_chembl_id": "CHEMBL872937",
  "content_hash": "sha256:ghi789...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440002",
  "_run_type": "incremental",
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "description": "In vivo inhibitory activity against human Heparanase",
  "assay_type": "B",
  "assay_test_type": "In vivo",
  "assay_organism": "Homo sapiens",
  "assay_tax_id": 9606,

  "target_chembl_id": "CHEMBL3921",
  "document_chembl_id": "CHEMBL1146658",

  "confidence_score": 9,
  "confidence_description": "Direct single protein target assigned",
  "relationship_type": "D",
  "relationship_description": "Direct protein target assigned",

  "bao_format": "BAO_0000218",
  "bao_label": "organism-based format",

  "src_id": 1
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/assay.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_activity.py` |
| Pipeline Config | `configs/pipelines/chembl/assay.yaml` |
| Activity Schema | `docs/domain/schemas/chembl/activity-schema.md` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
