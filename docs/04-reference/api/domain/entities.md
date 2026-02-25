# Domain Entities

Rich domain objects representing bioactivity data with invariants and business logic.

## Overview

BioETL entities follow these design principles:

- **Immutable**: Frozen dataclasses with `slots=True` for memory efficiency
- **Validated**: Invariants checked on construction via `--post-init--`
- **Pure Python**: No external dependencies in domain layer

### Field Classification

| Category         | Description                                    | Example                          |
| ---------------- | ---------------------------------------------- | -------------------------------- |
| **REQUIRED**     | Must be non-None, validated in `--post-init--` | `entity-id`, `content-hash`      |
| **LINEAGE**      | System metadata for tracking                   | `run-id`, `ingestion-ts`         |
| **API-OPTIONAL** | May be None (API-dependent)                    | `pchembl-value`, `target-name`   |
| **COMPUTED**     | Derived from other fields                      | `pchembl-value` (log conversion) |

## Base Entity

### BaseEntity

Base class containing system fields for lineage and versioning.

::: bioetl.domain.entities.BaseEntity
options:
show_root_heading: true
show_source: true
members:
\- entity-id
\- content-hash
\- run-id
\- run-type
\- ingestion-ts
\- source-batch-id

<!-- RequiredEntityFields: planned protocol, not yet implemented -->

## ChEMBL Entities

### Bioactivity

Bioactivity measurement from ChEMBL database.

::: bioetl.domain.entities.Bioactivity
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

### ChemblPublication

Publication or patent reference.

::: bioetl.domain.entities.ChemblPublication
options:
show_root_heading: true
show_source: false

## PubChem Entities

### CompoundRecord

PubChem compound with chemical properties.

::: bioetl.domain.entities.CompoundRecord
    options:
        show_root_heading: true
        show_source: false

## PubMed Entities

### PubMedPublicationEntity

Scientific publication metadata.

::: bioetl.domain.entities.PubMedPublicationEntity
    options:
        show_root_heading: true
        show_source: false

## UniProt Entities

### ProteinClassification

UniProt protein classification.

::: bioetl.domain.entities.ProteinClassification
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.domain.entities import Bioactivity, BaseEntity
from bioetl.domain.types import RunType, RunID, ContentHash
from datetime import datetime
from uuid import uuid4

# Create an activity entity
activity = Bioactivity(
    entity-id="CHEMBL12345",
    content-hash=ContentHash("sha256:abc123..."),
    run-id=RunID(uuid4()),
    run-type=RunType.INCREMENTAL,
    ingestion-ts=datetime.now(),
    # ChEMBL-specific fields
    activity-id="12345",
    molecule-chembl-id="CHEMBL789",
    standard-type="IC50",
    standard-value=50.0,
    standard-units="nM",
)

# Check required fields protocol
from bioetl.domain.entities import RequiredEntityFields

assert isinstance(activity, RequiredEntityFields)
```

## See Also

- [Types](types.md) - Core type definitions used by entities
- [Ports](ports.md) - Port interfaces that operate on entities
- [Exceptions](exceptions.md) - Validation errors for entities
