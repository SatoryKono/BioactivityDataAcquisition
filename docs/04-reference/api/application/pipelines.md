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
        show_root_heading: true
        show_source: false

### Activity Transformer

::: bioetl.application.pipelines.chembl.activity_transformer.ActivityTransformer
    options:
        show_root_heading: true
        show_source: false

### Assay Pipeline

Experimental assay descriptions.

::: bioetl.application.pipelines.chembl.assay.ChEMBLAssayPipeline
    options:
        show_root_heading: true
        show_source: false

### Assay Transformer

::: bioetl.application.pipelines.chembl.assay_transformer.AssayTransformer
    options:
        show_root_heading: true
        show_source: false

### Molecule Pipeline

Chemical compound structures.

::: bioetl.application.pipelines.chembl.molecule.ChEMBLMoleculePipeline
    options:
        show_root_heading: true
        show_source: false

### Molecule Transformer

::: bioetl.application.pipelines.chembl.molecule_transformer.MoleculeTransformer
    options:
        show_root_heading: true
        show_source: false

### Target Pipeline

Biological targets (proteins, genes).

::: bioetl.application.pipelines.chembl.target.ChEMBLTargetPipeline
    options:
        show_root_heading: true
        show_source: false

### Target Transformer

::: bioetl.application.pipelines.chembl.target_transformer.TargetTransformer
    options:
        show_root_heading: true
        show_source: false

### Document Pipeline

Publications and patents.

::: bioetl.application.pipelines.chembl.document.ChEMBLDocumentPipeline
    options:
        show_root_heading: true
        show_source: false

### Document Transformer

::: bioetl.application.pipelines.chembl.document_transformer.DocumentTransformer
    options:
        show_root_heading: true
        show_source: false

### Target Component Pipeline

Target components (protein chains, domains).

::: bioetl.application.pipelines.chembl.target_component.ChEMBLTargetComponentPipeline
    options:
        show_root_heading: true
        show_source: false

### Target Component Transformer

::: bioetl.application.pipelines.chembl.target_component_transformer.TargetComponentTransformer
    options:
        show_root_heading: true
        show_source: false

### Base ChEMBL Transformer

Common functionality for all ChEMBL transformers.

::: bioetl.application.pipelines.chembl.base_chembl_transformer.BaseChemblTransformer
    options:
        show_root_heading: true
        show_source: false

## PubChem Pipeline

PubChem provides chemical compound data.

### Compound Pipeline

::: bioetl.application.pipelines.pubchem.compound.PubChemCompoundPipeline
    options:
        show_root_heading: true
        show_source: false

### Compound Transformer

::: bioetl.application.pipelines.pubchem.transformer.PubChemTransformer
    options:
        show_root_heading: true
        show_source: false

## UniProt Pipeline

UniProt provides protein sequence and annotation data.

### Protein Pipeline

::: bioetl.application.pipelines.uniprot.protein.UniProtProteinPipeline
    options:
        show_root_heading: true
        show_source: false

### Protein Transformer

::: bioetl.application.pipelines.uniprot.transformer.UniProtTransformer
    options:
        show_root_heading: true
        show_source: false

## PubMed Pipeline

PubMed provides scientific publication metadata.

### Publications Pipeline

::: bioetl.application.pipelines.pubmed.publications.PubMedPublicationsPipeline
    options:
        show_root_heading: true
        show_source: false

### Publications Transformer

::: bioetl.application.pipelines.pubmed.transformer.PubMedTransformer
    options:
        show_root_heading: true
        show_source: false

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
pipeline_name: chembl_activity
provider: chembl
entity_type: activity
batch_size: 100
primary_keys:
  - activity_id

# Silver layer field filtering
silver_filters:
  include_fields: null  # All fields
  exclude_fields:
    - _internal_field

# Gold layer configuration
gold_filters:
  exclude_json_fields:
    - molecule_structures
    - target_components
```

## Usage Example

```python
from bioetl.composition.bootstrap import bootstrap_pipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType

# Create pipeline context
ctx = PipelineContext(
    pipeline_name="chembl_activity",
    run_type=RunType.INCREMENTAL,
)

# Bootstrap and run
runner = bootstrap_pipeline(ctx)
await runner.run()
```

## See Also

- [Core Components](core.md) - PipelineRunner, Executor
- [Transformers](transformers.md) - BaseTransformer framework
- [Bootstrap](../composition/bootstrap.md) - Pipeline assembly
- [CLI Reference](../../cli.md) - Command-line interface
