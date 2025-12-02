# Adding a New Pipeline

Step-by-step guide for creating a new pipeline in BioETL.

## Overview

A pipeline in BioETL follows the Extract → Transform → Validate → Write pattern, inheriting from `PipelineBase` or a provider-specific base (e.g., `ChemblBasePipeline`).

## Steps

### 1. Create Configuration File

Create a YAML configuration file in `configs/pipelines/<provider>/<entity>.yaml`:

```yaml
extends: <provider>_default

entity_name: <entity>
endpoint: /<entity>
primary_key: <entity>_id

fields:
  - name: <entity>_id
    data_type: integer
    is_nullable: false
    description: ID сущности
```

### 2. Create Pipeline Documentation

Create documentation in `docs/02-pipelines/<provider>/<entity>/`:

- `00-<entity>-<provider>-overview.md` — Overview of the pipeline
- `01-<entity>-<provider>-extraction.md` — Extraction stage
- `02-<entity>-<provider>-transformation.md` — Transformation stage
- Additional files as needed

### 3. Create Pandera Schema

Define a Pandera schema in the schema registry:

- Create schema file in `src/bioetl/schemas/<entity>.py`
- Document in `docs/02-pipelines/schemas/<entity>-schema.md`

### 4. Implement Pipeline Class

Create pipeline implementation:

```python
from bioetl.pipelines.base import PipelineBase

class <Entity><Provider>Pipeline(PipelineBase):
    # Implementation
```

### 5. Register Pipeline

Register the pipeline in the CLI and factory registry.

### 6. Create Tests

- Unit tests in `tests/bioetl/pipelines/<provider>/<entity>/`
- Integration tests if needed

## Related Documentation

- **[Pipeline Base](../reference/core/pipeline-base.md)** — Base pipeline architecture
- **[Project Rules](../project/rules-summary.md)** — Naming conventions and standards
- **[Adding a New ABC](adding-new-abc.md)** — If you need new components

