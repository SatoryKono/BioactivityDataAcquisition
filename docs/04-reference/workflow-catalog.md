______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-07'

______________________________________________________________________

# Workflow Catalog

Current source of truth: `configs/workflows/*.yaml`.

**Boundary:** this page is the declarative workflow inventory (what workflows exist).
For CLI command reference, see [CLI Reference](cli.md). For execution workflows and
runtime control flow, see [Running Pipelines](../03-guides/running-pipelines.md).

This page is not the formal lifecycle-state specification.

Evidence-backed DAG, control-plane, and transform classifications are published
in the [Pipeline and Workflow Passports](passports/index.md) index.

Runtime model evidence:

- Domain config: `src/bioetl/domain/workflow/config.py`
- Strict schema: `src/bioetl/infrastructure/schemas/workflow_config.py`
- DAG validation: `src/bioetl/domain/workflow/dag.py`
- Runner: `src/bioetl/application/services/workflow_runner_service.py`
- Workflow control plane:
  `src/bioetl/application/services/control_plane/workflow/`

For current workflow lifecycle semantics, statuses, and repair/force behavior,
use [Workflow State Machine](domain/workflow-state-machine.md).

## Composite execution boundary

Composite pipelines (`composite_activity`, `composite_assay`, `composite_molecule`,
`composite_publication`, `composite_target`) are **not** declared in
`configs/workflows/*.yaml`.

| Surface | Source of truth | CLI entry |
| --- | --- | --- |
| Composite merge policy | `configs/composites/*.yaml` | `bioetl run-composite --composite <entity>` |
| Composite entity contract | `configs/entities/composite/*.yaml` | same command |
| Declarative workflow DAG | `configs/workflows/*.yaml` | `bioetl workflow run <name>` |

Use [Running Pipelines](../03-guides/running-pipelines.md) for composite run
examples and [Pipeline Catalog](pipeline-catalog.md) for composite inventory.

## Contract

Every workflow YAML uses this shape:

```yaml
schema_version: "1.0.0"
workflow:
  name: example
  version: "1.0.0"
  defaults:
    run_options: {}
  steps:
    - kind: pipeline
      step_id: example_step
      pipeline_name: some_pipeline
    - kind: transform
      step_id: transform_step
      transform_name: some_transform
      depends_on:
        - example_step
      config: {}
```

`WorkflowConfig.__post_init__` calls `topologically_sorted_step_ids`, so
duplicate step IDs, missing dependencies, and dependency cycles are domain
invariant violations, not documentation conventions.

## Catalog

| Workflow | File | Steps | Pipeline steps | Transform steps | Edges | Purpose/dependencies |
| --- | --- | ---: | --- | --- | ---: | --- |
| `chembl_activity` | `configs/workflows/chembl_activity.yaml` | 1 | `chembl_activity` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_assay` | `configs/workflows/chembl_assay.yaml` | 1 | `chembl_assay` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_assay_parameters` | `configs/workflows/chembl_assay_parameters.yaml` | 1 | `chembl_assay_parameters` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_baseline` | `configs/workflows/chembl_baseline.yaml` | 7 | `chembl_assay`, `chembl_target`, `chembl_publication` | `reconcile_foreign_keys` x4 | 8 | Baseline ChEMBL DAG with bidirectional Gold foreign-key reconciliation after source pipeline steps. |
| `chembl_cell_line` | `configs/workflows/chembl_cell_line.yaml` | 1 | `chembl_cell_line` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_compound_record` | `configs/workflows/chembl_compound_record.yaml` | 1 | `chembl_compound_record` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_core` | `configs/workflows/chembl_core.yaml` | 5 | `chembl_activity`, `chembl_assay`, `chembl_target` | `reconcile_foreign_keys`, `summarize_upstream_outputs` | 5 | Core ChEMBL DAG with unbounded activity/assay/target ingests, assay-target reconciliation, and output summary. |
| `chembl_molecule` | `configs/workflows/chembl_molecule.yaml` | 1 | `chembl_molecule` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_protein_class` | `configs/workflows/chembl_protein_class.yaml` | 1 | `chembl_protein_class` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_publication` | `configs/workflows/chembl_publication.yaml` | 1 | `chembl_publication` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_publication_similarity` | `configs/workflows/chembl_publication_similarity.yaml` | 1 | `chembl_publication_similarity` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_publication_term` | `configs/workflows/chembl_publication_term.yaml` | 1 | `chembl_publication_term` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_reference_pack` | `configs/workflows/chembl_reference_pack.yaml` | 10 | `chembl_target`, `chembl_target_component`, `chembl_protein_class`, `chembl_target_protein_classification`, `chembl_tissue`, `chembl_subcellular_fraction`, `chembl_cell_line`, `chembl_publication`, `chembl_publication_term`, `chembl_publication_similarity` | - | 6 | Reference-data pack with dependency edges for target/protein-classification related steps. |
| `chembl_subcellular_fraction` | `configs/workflows/chembl_subcellular_fraction.yaml` | 1 | `chembl_subcellular_fraction` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_target` | `configs/workflows/chembl_target.yaml` | 1 | `chembl_target` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_target_component` | `configs/workflows/chembl_target_component.yaml` | 1 | `chembl_target_component` | - | 0 | Single-pipeline workflow wrapper. |
| `chembl_target_protein_classification` | `configs/workflows/chembl_target_protein_classification.yaml` | 4 | `chembl_target`, `chembl_target_component`, `chembl_protein_class`, `chembl_target_protein_classification` | - | 4 | Target/protein-classification workflow with explicit upstream dependencies. |
| `chembl_tissue` | `configs/workflows/chembl_tissue.yaml` | 1 | `chembl_tissue` | - | 0 | Single-pipeline workflow wrapper. |
| `crossref_publication` | `configs/workflows/crossref_publication.yaml` | 1 | `crossref_publication` | - | 0 | Single-pipeline workflow wrapper. |
| `openalex_publication` | `configs/workflows/openalex_publication.yaml` | 1 | `openalex_publication` | - | 0 | Single-pipeline workflow wrapper. |
| `pubchem_compound` | `configs/workflows/pubchem_compound.yaml` | 1 | `pubchem_compound` | - | 0 | Single-pipeline workflow wrapper. |
| `publication_provider_pack` | `configs/workflows/publication_provider_pack.yaml` | 4 | `crossref_publication`, `openalex_publication`, `pubmed_publication`, `semanticscholar_publication` | - | 0 | Independent publication-provider enrichment pack. |
| `pubmed_publication` | `configs/workflows/pubmed_publication.yaml` | 1 | `pubmed_publication` | - | 0 | Single-pipeline workflow wrapper. |
| `semanticscholar_publication` | `configs/workflows/semanticscholar_publication.yaml` | 1 | `semanticscholar_publication` | - | 0 | Single-pipeline workflow wrapper. |
| `uniprot_idmapping` | `configs/workflows/uniprot_idmapping.yaml` | 1 | `uniprot_idmapping` | - | 0 | Single-pipeline workflow wrapper. |
| `uniprot_protein` | `configs/workflows/uniprot_protein.yaml` | 1 | `uniprot_protein` | - | 0 | Single-pipeline workflow wrapper. |
| `uniprot_support_pack` | `configs/workflows/uniprot_support_pack.yaml` | 2 | `uniprot_protein`, `uniprot_idmapping` | - | 0 | Independent UniProt support pack. |

## Quality Gates

Use the architecture/workflow checks in `tests/architecture/` and the strict
schema conversion in `src/bioetl/infrastructure/schemas/workflow_config.py` as
the regression guard. Workflow documentation must not describe `tasks` or
ledger-only resume semantics; the current YAML contract is `workflow.steps`,
and resume/repair semantics belong to ADR-047 plus the workflow control plane.

## Regeneration Workflow

Refresh this page whenever `configs/workflows/*.yaml` changes.

Minimum revalidation:

1. confirm the updated YAML still matches
   `src/bioetl/infrastructure/schemas/workflow_config.py`;
2. confirm step semantics still align with
   `src/bioetl/domain/workflow/dag.py` and
   `src/bioetl/application/services/workflow_runner_service.py`;
3. confirm lifecycle wording remains aligned with
   [Workflow State Machine](domain/workflow-state-machine.md).
