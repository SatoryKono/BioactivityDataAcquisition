# ChEMBL Tissue Pipeline Specification

*Version 1.0.0 | Aligned with RULES.md v5.22*

---

## 1. Identification

| Parameter | Value |
|-----------|-------|
| **Pipeline ID** | `chembl_tissue` |
| **Provider** | ChEMBL (EBI) |
| **Entity** | tissue |
| **Source API** | ChEMBL REST API (`/tissue`) |
| **Strategy** | Direct Entity (full extract from API) |

---

## 2. Business Context

### 2.1. Entity Purpose

Tissues represent anatomical locations and biological samples used in ChEMBL assays:

- **Biological Context**: Normalizes tissue/organ references across assays for cross-study comparison.
- **Reference Table**: Provides a canonical list of tissues with ontology cross-references (BTO, UBERON, EFO, CALOHA).

### 2.2. Use Cases

1. **Tissue-Specific Analysis**: Filter activities and assays by tissue type (e.g., liver, brain).
2. **Composite Assay Enrichment**: Enriches composite_assay pipeline with tissue metadata via `tissue-id` FK.
3. **Ontology Mapping**: Cross-reference tissues with external ontologies (UBERON, BTO, EFO).

---

## 3. Extraction & Transformation

### 3.1. Fields

| # | Field | Type | Nullable | Description |
|---|-------|------|----------|-------------|
| 1 | `tissue-id` | string | No | Primary key (ChEMBL format: `CHEMBL\d+`) |
| 2 | `pref-name` | string | No | Preferred tissue name |
| 3 | `bto-id` | string | Yes | Brenda Tissue Ontology ID (format: `BTO:0000000`) |
| 4 | `caloha-id` | string | Yes | CALIPHO tissue ID (format: `TS-0000`) |
| 5 | `efo-id` | string | Yes | EFO ontology ID (format: `EFO:0000000`) |
| 6 | `uberon-id` | string | Yes | UBERON anatomy ontology ID (format: `UBERON:0000000`) |

---

## 4. Validation

### 4.1. DQ Rules

| Field | Rule | Condition | Nullable |
|-------|------|-----------|----------|
| `tissue-id` | pattern | `^CHEMBL\d+$` | No |
| `pref-name` | length | 1-200 chars | No |
| `bto-id` | pattern | `^BTO:\d{7}$` | Yes |
| `caloha-id` | pattern | `^TS-\d{4}$` | Yes |
| `efo-id` | pattern | `^EFO:\d{7}$` | Yes |
| `uberon-id` | pattern | `^UBERON:\d{7}$` | Yes |

### 4.2. Error Thresholds

| Threshold | Condition | Action |
|-----------|-----------|--------|
| Soft | > 5% errors | WARNING |
| Hard | > 20% errors | FAIL BATCH |

---

## 5. Pipeline Configuration

```yaml
pipeline-name: chembl_tissue
provider: chembl
entity-type: tissue
version: "1.0.0"

primary-keys: ["tissue-id"]
silver-table: "chembl_tissue"
gold-table: "chembl_tissue"
```

---

## 6. CLI Usage

```bash
# Incremental load
bioetl run chembl_tissue

# With record limit
bioetl run chembl_tissue --limit 500

# Full rebuild
bioetl run chembl_tissue --run-type rebuild
```

---

## 7. Related Files

| Component | Path |
|-----------|------|
| Config | `configs/pipelines/chembl/tissue.yaml` |
| DQ Rules | `configs/quality/entities/chembl/tissue.yaml` |
| Schema | `configs/schemas/chembl/tissue.yaml` |
| Transformer | `src/bioetl/application/pipelines/chembl/tissue-transformer.py` |

---

## 8. Entity Relationships

```
Tissue (tissue-id)
    └── Assay (tissue-id FK) [1:N]
        └── Activity [1:N]
    └── Composite Assay (enricher via tissue-id) [1:N]
```

---

*Last updated: 2026-02-17*
