# Composite Target Pipeline

> **Pipeline**: `composite_target`
> **Version**: 1.1.0
> **Last Updated**: 2026-02-03
> **Reference**: ADR-026 Composite Pipeline Pattern

---

## Overview

The `composite_target` pipeline combines biological target data from ChEMBL with
UniProt ID mappings and protein classification hierarchy. It demonstrates the
**chained dependencies** feature where one dependency provides keys for another.

### Architecture

```
┌─────────────────────┐
│    Seed Pipeline    │
│   (chembl_target)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Extract Keys     │
│ (target_chembl_id,  │
│   component_id)     │
└──────────┬──────────┘
           │
    Dependencies (sequential)
           │
┌──────────▼──────────┐
│ chembl_target_      │ ← Uses component_id from seed
│    component        │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ chembl_protein_     │ ← Uses protein_classification_id
│     class           │   from target_component (chained!)
└──────────┬──────────┘
           │
    Enrichers (parallel)
           │
┌──────────▼──────────┐
│  uniprot_idmapping  │ ← Uses target_chembl_id from seed
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│    Merge Step       │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│    Gold Output      │
└─────────────────────┘
```

---

## Pipeline Identity

| Attribute | Value |
|-----------|-------|
| **Pipeline Name** | `composite_target` |
| **Seed Pipeline** | `chembl_target` |
| **Seed Keys** | `target_chembl_id`, `component_id` |
| **Output Silver Path** | `data/output/silver/composite/target` |
| **Output Gold Path** | `data/output/gold/composite/target` |
| **Max Concurrency** | 2 |

---

## Chained Dependencies

This pipeline demonstrates **chained dependencies** — a feature where one dependency
provides keys for another.

### Standard Dependency vs Chained Dependency

| Type | Key Source | Example |
|------|------------|---------|
| **Standard** | Seed pipeline | `component_id` from `chembl_target` |
| **Chained** | Another dependency | `protein_classification_id` from `chembl_target_component` |

### Configuration Example

```yaml
dependencies:
  # 1. Standard dependency: uses keys from seed
  - pipeline: chembl_target_component
    join_keys:
      - component_id      # Column in seed
    silver_table: silver/chembl/target_component

  # 2. Chained dependency: uses keys from #1
  - pipeline: chembl_protein_class
    join_keys:
      - protein_classification_id  # Column in target_component Silver
    filter_field: protein_class_id # API field name (differs from column!)
    key_source: chembl_target_component  # Read keys from this Silver table
    silver_table: silver/chembl/protein_class
```

### Why Chained Dependencies?

The `protein_class` API endpoint:
- Has **no** `target_chembl_id` field
- Uses `protein_class_id` as primary key
- Relationships: `target` → `target_component` → `protein_class` (M:N)

Without chained dependencies, we would need to:
1. Load ALL ~1,500 protein classes (wasteful)
2. Or manually orchestrate pipelines

With chained dependencies:
1. `target_component` populates Silver with `protein_classification_id`
2. `protein_class` reads those IDs and filters API calls
3. Only relevant protein classes are loaded

---

## Dependencies

| Order | Pipeline | Join Key | Key Source | Filter Field |
|-------|----------|----------|------------|--------------|
| 1 | `chembl_target_component` | `component_id` | seed | `component_id` |
| 2 | `chembl_protein_class` | `protein_classification_id` | `chembl_target_component` | `protein_class_id` |

### Field Mapping: filter_field

When the source column name differs from the API filter field:

| Source Table | Source Column | API Field |
|--------------|---------------|-----------|
| target_component | `protein_classification_id` | `protein_class_id` |

The `filter_field` parameter maps between these.

---

## Enrichers

| Pipeline | Join Key | Required | Timeout |
|----------|----------|----------|---------|
| `uniprot_idmapping` | `target_chembl_id` | No | 600s |

---

## Data Quality

### Thresholds

| Level | Soft Fail | Hard Fail |
|-------|-----------|-----------|
| Composite | 10% | 30% |
| uniprot_idmapping | 30% | 80% |

### Required Fields (Gold)

- `target_chembl_id`
- `pref_name`

---

## Usage

```bash
# Full composite run
bioetl run --pipeline composite_target

# With limit
bioetl run --pipeline composite_target --limit 100

# Dry run
bioetl run --pipeline composite_target --dry-run

# Resume after failure
bioetl run --pipeline composite_target --resume
```

---

## Output Schema

### Key Fields

| Field | Source | Description |
|-------|--------|-------------|
| `target_chembl_id` | seed | Primary key |
| `pref_name` | seed | Target preferred name |
| `target_type` | seed | Classification (SINGLE PROTEIN, ORGANISM, etc.) |
| `component_id` | seed | Primary component ID |
| `uniprot_accession` | uniprot | UniProt accession |
| `mapping_status` | uniprot | found/not_found/error |
| `protein_classification_id` | target_component | Protein class ID |

### Lineage Metadata

```json
{
  "_composite_run_id": "uuid",
  "_source_providers": ["chembl", "uniprot"],
  "_enrichment_status": {
    "uniprot_idmapping": "success"
  }
}
```

---

## Related Documents

- [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ChEMBL Target Pipeline](./chembl/04-target-spec.md)
- [ChEMBL Target Component Pipeline](./chembl/10-target-component-spec.md)
- [ChEMBL Protein Class Pipeline](./chembl/protein-class-spec.md)
