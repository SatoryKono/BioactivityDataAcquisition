# Domain Entities

Rich domain objects representing bioactivity data with invariants and business logic.

## Overview

BioETL entities follow these design principles:

- **Immutable**: Frozen dataclasses with `slots=True` for memory efficiency
- **Validated**: Invariants checked on construction via `__post_init__`
- **Pure Python**: No external dependencies in domain layer

### Field Classification

| Category | Description | Example |
|----------|-------------|---------|
| **REQUIRED** | Must be non-None, validated in `__post_init__` | `entity_id`, `content_hash` |
| **LINEAGE** | System metadata for tracking | `run_id`, `ingestion_ts` |
| **API-OPTIONAL** | May be None (API-dependent) | `pchembl_value`, `target_name` |
| **COMPUTED** | Derived from other fields | `pchembl_value` (log conversion) |

## Base Entity

### BaseEntity

Base class containing system fields for lineage and versioning.

::: bioetl.domain.entities.BaseEntity
    options:
        show_root_heading: true
        show_source: true
        members:
            - entity_id
            - content_hash
            - run_id
            - run_type
            - ingestion_ts
            - source_batch_id

### RequiredEntityFields

Protocol defining minimum required fields for all entities.

::: bioetl.domain.entities.RequiredEntityFields
    options:
        show_root_heading: true
        show_source: false

## ChEMBL Entities

### Activity

Bioactivity measurement from ChEMBL database.

::: bioetl.domain.entities.Activity
    options:
        show_root_heading: true
        show_source: false

### Assay

Experimental assay information.

::: bioetl.domain.entities.Assay
    options:
        show_root_heading: true
        show_source: false

### Molecule

Chemical compound structure.

::: bioetl.domain.entities.Molecule
    options:
        show_root_heading: true
        show_source: false

### Target

Biological target (protein, gene, etc.).

::: bioetl.domain.entities.Target
    options:
        show_root_heading: true
        show_source: false

### TargetComponent

Component of a complex biological target.

::: bioetl.domain.entities.TargetComponent
    options:
        show_root_heading: true
        show_source: false

### Document

Publication or patent reference.

::: bioetl.domain.entities.Document
    options:
        show_root_heading: true
        show_source: false

## PubChem Entities

### Compound

PubChem compound with chemical properties.

::: bioetl.domain.entities.Compound
    options:
        show_root_heading: true
        show_source: false

## PubMed Entities

### Publication

Scientific publication metadata.

::: bioetl.domain.entities.Publication
    options:
        show_root_heading: true
        show_source: false

## UniProt Entities

### Protein

UniProt protein entry.

::: bioetl.domain.entities.Protein
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.domain.entities import Activity, BaseEntity
from bioetl.domain.types import RunType, RunID, ContentHash
from datetime import datetime
from uuid import uuid4

# Create an activity entity
activity = Activity(
    entity_id="CHEMBL12345",
    content_hash=ContentHash("sha256:abc123..."),
    run_id=RunID(uuid4()),
    run_type=RunType.INCREMENTAL,
    ingestion_ts=datetime.now(),
    # ChEMBL-specific fields
    activity_id=12345,
    assay_chembl_id="CHEMBL123456",
    molecule_chembl_id="CHEMBL789",
    standard_type="IC50",
    standard_value=50.0,
    standard_units="nM",
)

# Check required fields protocol
from bioetl.domain.entities import RequiredEntityFields
assert isinstance(activity, RequiredEntityFields)
```

## See Also

- [Types](types.md) - Core type definitions used by entities
- [Ports](ports.md) - Port interfaces that operate on entities
- [Exceptions](exceptions.md) - Validation errors for entities
