# Pipelines

Provider-specific pipeline implementations.

## Overview

BioETL supports multiple bioactivity data providers:

| Provider | Entities | Status |
|----------|----------|--------|
| **ChEMBL** | Activity, Assay, Molecule, Target, Document, TargetComponent | Production |
| **PubChem** | Compound | Production |
| **UniProt** | Protein | Production |
| **PubMed** | Publication | Production |

## ChEMBL Pipelines

ChEMBL provides bioactivity data from medicinal chemistry literature.

### Activity Pipeline

Bioactivity measurements (IC50, Ki, EC50, etc.).

::: bioetl.application.pipelines.chembl.activity.ChEMBLActivityPipeline
    options:
        show-root-heading: true
        show-source: false

### Activity Transformer

::: bioetl.application.pipelines.chembl.activity-transformer.ActivityTransformer
    options:
        show-root-heading: true
        show-source: false

### Assay Pipeline

Experimental assay descriptions.

::: bioetl.application.pipelines.chembl.assay.ChEMBLAssayPipeline
    options:
        show-root-heading: true
        show-source: false

### Assay Transformer

::: bioetl.application.pipelines.chembl.assay-transformer.AssayTransformer
    options:
        show-root-heading: true
        show-source: false

### Molecule Pipeline

Chemical compound structures.

::: bioetl.application.pipelines.chembl.molecule.ChEMBLMoleculePipeline
    options:
        show-root-heading: true
        show-source: false

### Molecule Transformer

::: bioetl.application.pipelines.chembl.molecule-transformer.MoleculeTransformer
    options:
        show-root-heading: true
        show-source: false

### Target Pipeline

Biological targets (proteins, genes).

::: bioetl.application.pipelines.chembl.target.ChEMBLTargetPipeline
    options:
        show-root-heading: true
        show-source: false

### Target Transformer

::: bioetl.application.pipelines.chembl.target-transformer.TargetTransformer
    options:
        show-root-heading: true
        show-source: false

### Document Pipeline

Publications and patents.

::: bioetl.application.pipelines.chembl.document.ChEMBLDocumentPipeline
    options:
        show-root-heading: true
        show-source: false

### Document Transformer

::: bioetl.application.pipelines.chembl.document-transformer.DocumentTransformer
    options:
        show-root-heading: true
        show-source: false

### Target Component Pipeline

Target components (protein chains, domains).

::: bioetl.application.pipelines.chembl.target-component.ChEMBLTargetComponentPipeline
    options:
        show-root-heading: true
        show-source: false

### Target Component Transformer

::: bioetl.application.pipelines.chembl.target-component-transformer.TargetComponentTransformer
    options:
        show-root-heading: true
        show-source: false

### Base ChEMBL Transformer

Common functionality for all ChEMBL transformers.

::: bioetl.application.pipelines.chembl.base-chembl-transformer.BaseChemblTransformer
    options:
        show-root-heading: true
        show-source: false

## PubChem Pipeline

PubChem provides chemical compound data.

### Compound Pipeline

::: bioetl.application.pipelines.pubchem.compound.PubChemCompoundPipeline
    options:
        show-root-heading: true
        show-source: false

### Compound Transformer

::: bioetl.application.pipelines.pubchem.transformer.PubChemCompoundTransformer
    options:
        show-root-heading: true
        show-source: false

## UniProt Pipeline

UniProt provides protein sequence and annotation data.

### Protein Pipeline

::: bioetl.application.pipelines.uniprot.protein.UniProtProteinPipeline
    options:
        show-root-heading: true
        show-source: false

### Protein Transformer

::: bioetl.application.pipelines.uniprot.transformer.UniProtProteinTransformer
    options:
        show-root-heading: true
        show-source: false

## PubMed Pipeline

PubMed provides scientific publication metadata.

### Publications Pipeline

::: bioetl.application.pipelines.pubmed.publications.PubMedPublicationsPipeline
    options:
        show-root-heading: true
        show-source: false

### Publications Transformer

::: bioetl.application.pipelines.pubmed.transformer.PubMedPublicationTransformer
    options:
        show-root-heading: true
        show-source: false

## Pipeline Registration

Pipelines are registered via decorator pattern:

```python
from bioetl.composition.factories import register

@register("chembl_activity")
def chembl_activity_factory(ctx: PipelineContext) -> PipelineRunner:
    """Factory for ChEMBL activity pipeline."""
    ...
```

## Pipeline Configuration

Each pipeline has YAML configuration:

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline-name: chembl_activity
provider: chembl
entity-type: activity
batch-size: 100
primary-keys:
  - activity-id

# Silver layer field filtering
silver-filters:
  include-fields: null  # All fields
  exclude-fields:
    - -internal-field

# Gold layer configuration
gold-filters:
  exclude-json-fields:
    - molecule-structures
    - target-components
```

## Usage Example

```python
from bioetl.composition.bootstrap import bootstrap-pipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType

# Create pipeline context
ctx = PipelineContext(
    pipeline-name="chembl_activity",
    run-type=RunType.INCREMENTAL,
)

# Bootstrap and run
runner = bootstrap-pipeline(ctx)
await runner.run()
```

## See Also

- [Core Components](core.md) - PipelineRunner, Executor
- [Transformers](transformers.md) - BaseTransformer framework
- [Bootstrap](../composition/bootstrap.md) - Pipeline assembly
- [CLI Reference](../../cli.md) - Command-line interface
