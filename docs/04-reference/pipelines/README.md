# Pipeline Reference

This directory contains technical reference documentation for individual pipelines.

## ChEMBL Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/chembl/activity.yaml` | activity |
| `configs/pipelines/chembl/assay.yaml` | assay |
| `configs/pipelines/chembl/assay_parameters.yaml` | assay_parameters |
| `configs/pipelines/chembl/cell_line.yaml` | cell_line |
| `configs/pipelines/chembl/compound_record.yaml` | compound_record |
| `configs/pipelines/chembl/molecule.yaml` | molecule |
| `configs/pipelines/chembl/protein_class.yaml` | protein_class |
| `configs/pipelines/chembl/publication.yaml` | publication |
| `configs/pipelines/chembl/publication_similarity.yaml` | publication_similarity |
| `configs/pipelines/chembl/publication_term.yaml` | publication_term |
| `configs/pipelines/chembl/target.yaml` | target |
| `configs/pipelines/chembl/target_component.yaml` | target_component |

## Composite Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/composite/publication.yaml` | publication |

## Crossref Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/crossref/publication.yaml` | publication |

## OpenAlex Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/openalex/publication.yaml` | publication |

## PubChem Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/pubchem/compound.yaml` | compound |

## PubMed Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/pubmed/publication.yaml` | publication |

## Semantic Scholar Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/semanticscholar/publication.yaml` | publication |

## UniProt Pipelines

| Config | Entity |
|--------|--------|
| `configs/pipelines/uniprot/idmapping.yaml` | idmapping |
| `configs/pipelines/uniprot/protein.yaml` | protein |

## Pipeline Configuration

All pipeline configurations are in `configs/pipelines/`:

```bash
configs/pipelines/_base.yaml
configs/pipelines/chembl/activity.yaml
configs/pipelines/chembl/assay.yaml
configs/pipelines/chembl/assay_parameters.yaml
configs/pipelines/chembl/cell_line.yaml
configs/pipelines/chembl/compound_record.yaml
configs/pipelines/chembl/molecule.yaml
configs/pipelines/chembl/protein_class.yaml
configs/pipelines/chembl/publication.yaml
configs/pipelines/chembl/publication_similarity.yaml
configs/pipelines/chembl/publication_term.yaml
configs/pipelines/chembl/target.yaml
configs/pipelines/chembl/target_component.yaml
configs/pipelines/composite/publication.yaml
configs/pipelines/crossref/publication.yaml
configs/pipelines/openalex/publication.yaml
configs/pipelines/pubchem/compound.yaml
configs/pipelines/pubmed/publication.yaml
configs/pipelines/semanticscholar/publication.yaml
configs/pipelines/uniprot/idmapping.yaml
configs/pipelines/uniprot/protein.yaml
```

## Related Documentation

- [Running Pipelines](../../03-guides/running-pipelines.md)
- [Pipeline Lifecycle](../../03-guides/pipeline-lifecycle.md)
- [CLI Reference](../cli.md)
