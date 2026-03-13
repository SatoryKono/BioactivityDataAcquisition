# Assay Schema (ChEMBL)
*Version: 1.0.0 | Aligned with RULES.md v5.24*

## Overview

| Attribute | Value |
|-----------|-------|
| **Entity ID** | `assay-chembl-id` (Business Key) |
| **Content Hash** | `content_hash` (SHA256 for SCD Type 2) |
| **Source** | ChEMBL API (`/chembl/api/data/assay.json`) |
| **Update Frequency** | Quarterly (ChEMBL release cycle) |
| **Schema Version** | 1.0.0 (ChEMBL 34 aligned) |

### Purpose
Assay records define the experimental conditions under which bioactivity measurements were made. Each assay links to a target and contains information about the assay type, biological context (organism, tissue, cell type), and confidence of target assignment.

### Key Relationships
```
Assay ◄─── Activity (assay-chembl-id)
    │
    ├───► Target (target-chembl-id)
    │
    ├───► Document (document-chembl-id)
    │
    └───► Cell Line (cell-chembl-id)
```

---

## Medallion Representation

| Layer | Format | Validation | Partition Key | Retention |
|-------|--------|------------|---------------|-----------|
| Bronze | JSONL+zstd | None | `ingestion-date` | 90 days |
| Silver | Delta Lake | Pandera (soft) | `assay-type` | Permanent |
| Gold | Delta Lake | Pandera (strict) | None | Permanent |

### Gold Layer Filtering
Gold layer applies filters for high-confidence assays:

| Filter | Values | Purpose |
|--------|--------|---------|
| `assay-type` | `["B", "F"]` | Binding and Functional only |
| `confidence-score` | `["8", "9"]` | High confidence (0-9 scale) |
| `relationship-type` | `["D"]` | Direct target interaction |

**Required Fields for Gold**: `assay-type`, `description`

---

## Field Schemas

### Primary Key

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `assay-chembl-id` | `str` | No | `^CHEMBL\d+$` | ChEMBL assay identifier | `assays[].assay-chembl-id` |

### Description & Classification

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `description` | `str` | Yes | — | Full assay description | `assays[].description` |
| `assay-type` | `str` | Yes | `isin=["B","F","A","T","P","U"]` | Assay type code | `assays[].assay-type` |
| `assay-test-type` | `str` | Yes | `isin=["In vivo","In vitro","Ex vivo"]` | Test type | `assays[].assay-test-type` |
| `assay-category` | `str` | Yes | `isin=[...]` | Assay category | `assays[].assay-category` |
| `assay-group` | `str` | Yes | — | Assay group | `assays[].assay-group` |
| `assay-pref-name` | `str` | Yes | — | Preferred assay name | `assays[].assay-pref-name` |

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
| `assay-organism` | `str` | Yes | — | Assay organism | `assays[].assay-organism` |
| `assay-tax-id` | `int` | Yes | — | NCBI Taxonomy ID | `assays[].assay-tax-id` |
| `assay-strain` | `str` | Yes | — | Strain | `assays[].assay-strain` |
| `assay-tissue` | `str` | Yes | — | Tissue | `assays[].assay-tissue` |
| `assay-cell-type` | `str` | Yes | — | Cell type | `assays[].assay-cell-type` |
| `assay-subcellular-fraction` | `str` | Yes | — | Subcellular fraction | `assays[].assay-subcellular-fraction` |

### Foreign Keys

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `target-chembl-id` | `str` | Yes | `^CHEMBL\d+$` | FK to Target | `assays[].target-chembl-id` |
| `document-chembl-id` | `str` | Yes | `^CHEMBL\d+$` | FK to Document | `assays[].document-chembl-id` |
| `cell-chembl-id` | `str` | Yes | — | FK to Cell Line | `assays[].cell-chembl-id` |
| `tissue-chembl-id` | `str` | Yes | — | FK to Tissue | `assays[].tissue-chembl-id` |
| `src-id` | `int` | Yes | — | Source database ID | `assays[].src-id` |
| `src-assay-id` | `str` | Yes | — | Source assay ID | `assays[].src-assay-id` |

### Target Relationship & Confidence

| Field | Type | Nullable | Constraints | Description | Source |
|-------|------|----------|-------------|-------------|--------|
| `relationship-type` | `str` | Yes | `isin=["D","H","M","N","S","U"]` | Target relationship | `assays[].relationship-type` |
| `relationship-description` | `str` | Yes | — | Relationship description | `assays[].relationship-description` |
| `confidence-score` | `int` | Yes | `ge=0, le=9` | Target confidence (0-9) | `assays[].confidence-score` |
| `confidence-description` | `str` | Yes | — | Confidence description | `assays[].confidence-description` |

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
| `bao-format` | `str` | Yes | `^BAO:\d+$` | BAO assay format ID | `assays[].bao-format` |
| `bao-label` | `str` | Yes | — | BAO format label | `assays[].bao-label` |

### Variant Information (Flattened)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `variant-accession` | `str` | Yes | UniProt accession | `variant-sequence.accession` |
| `variant-isoform` | `str` | Yes | Isoform identifier | `variant-sequence.isoform` |
| `variant-mutation` | `str` | Yes | Mutation (e.g., V600E) | `variant-sequence.mutation` |
| `variant-organism` | `str` | Yes | Variant organism | `variant-sequence.organism` |
| `variant-sequence` | `str` | Yes | Amino acid sequence | `variant-sequence.sequence` |
| `variant-tax-id` | `int` | Yes | Variant taxonomy ID | `variant-sequence.tax-id` |
| `variant-sequence-json` | `str` | Yes | Full JSON (forensic) | JSON of variant-sequence |

### Other Fields

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `score` | `float` | Yes | Assay score | `assays[].score` |
| `aidx` | `str` | Yes | Assay index | `assays[].aidx` |

### Complex Fields (JSON Serialized)

| Field | Type | Nullable | Description | Source |
|-------|------|----------|-------------|--------|
| `assay-classifications` | `str` | Yes | Classification hierarchy (JSON) | `assays[].assay-classifications` |
| `assay-parameters` | `str` | Yes | Assay parameters (JSON) | `assays[].assay-parameters` |

---

## Meta-Fields (RULES.md §2.4)

| Field | Type | Nullable | Purpose | Included in Content Hash |
|-------|------|----------|---------|-------------------------|
| `entity_id` | `str` | No | Business key (= assay-chembl-id) | Yes |
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
| `assay-chembl-id` | `assay-chembl-id` | Direct |
| `assay-tax-id` | `assay-tax-id` | `safe-int()` |
| `confidence-score` | `confidence-score` | `safe-int()` |
| `variant-sequence` | `variant-*` | Flatten nested dict |
| `variant-sequence` | `variant-sequence-json` | `json.dumps()` |
| `assay-classifications` | `assay-classifications` | `json.dumps()` |
| `assay-parameters` | `assay-parameters` | `json.dumps()` |

---

## Validation Rules

### Pandera Schema

```python
class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    assay-chembl-id: Series[str] = pa.Field(
        nullable=False, str-matches=r"^CHEMBL\d+$"
    )
    assay-type: Optional[Series[str]] = pa.Field(
        nullable=True, isin=["B", "F", "A", "T", "P", "U"]
    )
    confidence-score: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=9
    )
    target-chembl-id: Optional[Series[str]] = pa.Field(
        nullable=True, str-matches=r"^CHEMBL\d+$"
    )

    class Config:
        strict = True
        ordered = False
        coerce = True
```

### Entity Invariants

```python
def -validate-invariants(self) -> None:
    if not self.assay-chembl-id:
        raise ValueError("Assay ChEMBL ID is required")
    if self.confidence-score is not None and not (0 <= self.confidence-score <= 9):
        raise ValueError(f"Confidence score must be 0-9, got {self.confidence-score}")
```

---

## Cross-Source Mapping

| Source | ID Field | Mapping Strategy |
|--------|----------|------------------|
| ChEMBL | `assay-chembl-id` | Primary source |
| BioAssay Ontology | `bao-format` | Via BAO ID |
| PubChem BioAssay | `src-assay-id` (when src-id=7) | Source mapping |

---

## Example Records

### Bronze (Raw API Response)

```json
{
  "assay-chembl-id": "CHEMBL872937",
  "description": "In vivo inhibitory activity against human Heparanase",
  "assay-type": "B",
  "assay-test-type": "In vivo",
  "assay-organism": "Homo sapiens",
  "assay-tax-id": 9606,
  "target-chembl-id": "CHEMBL3921",
  "document-chembl-id": "CHEMBL1146658",
  "confidence-score": 9,
  "confidence-description": "Direct single protein target assigned",
  "relationship-type": "D",
  "relationship-description": "Direct protein target assigned",
  "bao-format": "BAO-0000218",
  "bao-label": "organism-based format",
  "src-id": 1
}
```

### Silver (Normalized)

```json
{
  "entity_id": "CHEMBL872937",
  "assay-chembl-id": "CHEMBL872937",
  "content_hash": "sha256:ghi789...",
  "_run_id": "550e8400-e29b-41d4-a716-446655440002",
  "_run_type": "incremental",
  "_ingestion_ts": "2024-01-15T10:30:00Z",
  "_dq_warn": false,
  "_index": 0,

  "description": "In vivo inhibitory activity against human Heparanase",
  "assay-type": "B",
  "assay-test-type": "In vivo",
  "assay-organism": "Homo sapiens",
  "assay-tax-id": 9606,

  "target-chembl-id": "CHEMBL3921",
  "document-chembl-id": "CHEMBL1146658",

  "confidence-score": 9,
  "confidence-description": "Direct single protein target assigned",
  "relationship-type": "D",
  "relationship-description": "Direct protein target assigned",

  "bao-format": "BAO-0000218",
  "bao-label": "organism-based format",

  "src-id": 1
}
```

---

## Related Artifacts

| Artifact | Path |
|----------|------|
| Pandera Schema | `src/bioetl/domain/schemas/chembl/assay.py` |
| Domain Entity | `src/bioetl/domain/entities/chembl_activity.py` |
| Pipeline Config | `configs/entities/chembl/assay.yaml` |
| Activity Schema | `docs/domain/schemas/chembl/activity-schema.md` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-28 | Initial schema documentation |

---

*Build reliably. Document honestly. Ask boldly.*
