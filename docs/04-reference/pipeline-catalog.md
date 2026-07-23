______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# Pipeline Catalog

Current source of truth:

- Entity pipeline configs: `configs/entities/**/*.yaml`
- Composite merge configs: `configs/composites/*.yaml`
- Provider configs: `configs/providers/*.yaml`
- Config loaders: `src/bioetl/infrastructure/config/pipeline_config_api.py`,
  `src/bioetl/infrastructure/config/composite_config_api.py`
- Composition factories: `src/bioetl/composition/factories/`

This page is the config-backed inventory of active provider/entity/composite
pipeline surfaces. It is not the architectural rationale page and it is not the
workflow lifecycle spec.

Per-pipeline operational facet coverage is normalized in
[pipelines/INDEX.md#operational-facet-coverage](pipelines/INDEX.md#operational-facet-coverage).
Use that matrix to audit Bronze, Silver, Gold, quarantine, DQ, replay,
checkpoint, run lifecycle, and config-owner coverage without duplicating the
shared control-plane contract in every individual pipeline spec.

## Summary

| Family | Count | Files | Notes |
| --- | ---: | --- | --- |
| Provider entity pipelines | 22 | `configs/entities/{provider}/{entity}.yaml` | ChEMBL 15, UniProt 2, plus CrossRef/OpenAlex/PubChem/PubMed/Semantic Scholar. |
| Composite entity pipelines | 5 | `configs/entities/composite/*.yaml` | Entity-level pipeline contracts for composite activity, assay, molecule, publication, target. |
| Composite merge configs | 5 | `configs/composites/*.yaml` | ADR-026 seed/enrich/merge behavior. |
| Provider settings | 7 | `configs/providers/*.yaml` | Provider API/rate-limit/fallback settings. |

## Entity Pipeline Catalog

`Gold runtime` is the effective value after config loading, not a literal-only
scan of entity YAML. `pipeline.sink.gold.enabled` defaults to `true` through
`SinkLayerConfig`; `default` below means that the YAML omits the flag and uses
that runtime default. This column does not describe Gold contract availability
and must not be inferred from other `enabled` keys such as input filters.

| Pipeline | Config | Provider | Entity | Description | Gold runtime |
| --- | --- | --- | --- | --- | --- |
| `chembl_activity` | `configs/entities/chembl/activity.yaml` | ChEMBL | activity | Extract biological activity records from ChEMBL API. | enabled (explicit) |
| `chembl_assay` | `configs/entities/chembl/assay.yaml` | ChEMBL | assay | Extract bioassay definitions from ChEMBL API. | enabled (explicit) |
| `chembl_assay_parameters` | `configs/entities/chembl/assay_parameters.yaml` | ChEMBL | assay_parameters | Extract experimental assay parameters from ChEMBL API. | enabled (default) |
| `chembl_cell_line` | `configs/entities/chembl/cell_line.yaml` | ChEMBL | cell_line | Extract cell lines from ChEMBL API. | enabled (default) |
| `chembl_compound_record` | `configs/entities/chembl/compound_record.yaml` | ChEMBL | compound_record | Extract compound records from ChEMBL API. | enabled (default) |
| `chembl_molecule` | `configs/entities/chembl/molecule.yaml` | ChEMBL | molecule | Extract molecules/compounds from ChEMBL API. | enabled (default) |
| `chembl_protein_class` | `configs/entities/chembl/protein_class.yaml` | ChEMBL | protein_class | ChEMBL protein classification hierarchy. | enabled (default) |
| `chembl_publication` | `configs/entities/chembl/publication.yaml` | ChEMBL | publication | Extract scientific publications from ChEMBL API. | enabled (explicit) |
| `chembl_publication_similarity` | `configs/entities/chembl/publication_similarity.yaml` | ChEMBL | publication_similarity | Extract publication similarity data from ChEMBL API. | enabled (default) |
| `chembl_publication_term` | `configs/entities/chembl/publication_term.yaml` | ChEMBL | publication_term | Extract publication terms from ChEMBL publication records. | enabled (default) |
| `chembl_subcellular_fraction` | `configs/entities/chembl/subcellular_fraction.yaml` | ChEMBL | subcellular_fraction | Extract unique subcellular fractions from ChEMBL assay records. | enabled (default) |
| `chembl_target` | `configs/entities/chembl/target.yaml` | ChEMBL | target | Extract biological targets from ChEMBL API. | enabled (explicit) |
| `chembl_target_component` | `configs/entities/chembl/target_component.yaml` | ChEMBL | target_component | Extract target components and protein sequences. | enabled (default) |
| `chembl_target_protein_classification` | `configs/entities/chembl/target_protein_classification.yaml` | ChEMBL | target_protein_classification | Path-first target-to-protein-classification relation rows from local snapshots. | enabled (default) |
| `chembl_tissue` | `configs/entities/chembl/tissue.yaml` | ChEMBL | tissue | Extract tissues from ChEMBL API. | enabled (default) |
| `crossref_publication` | `configs/entities/crossref/publication.yaml` | CrossRef | publication | Enrich publication records with CrossRef metadata via DOI. | enabled (default) |
| `openalex_publication` | `configs/entities/openalex/publication.yaml` | OpenAlex | publication | Batch DOI resolution via OpenAlex with title fallback. | enabled (default) |
| `pubchem_compound` | `configs/entities/pubchem/compound.yaml` | PubChem | compound | Ingest PubChem compounds. | enabled (default) |
| `pubmed_publication` | `configs/entities/pubmed/publication.yaml` | PubMed | publication | Extract publication metadata from PubMed Entrez. | enabled (default) |
| `semanticscholar_publication` | `configs/entities/semanticscholar/publication.yaml` | Semantic Scholar | publication | Batch DOI resolution via Semantic Scholar with title fallback. | enabled (default) |
| `uniprot_idmapping` | `configs/entities/uniprot/idmapping.yaml` | UniProt | idmapping | Map ChEMBL target IDs to UniProt accessions. | enabled (default) |
| `uniprot_protein` | `configs/entities/uniprot/protein.yaml` | UniProt | protein | Ingest UniProt proteins. | enabled (default) |
| `composite_activity` | `configs/entities/composite/activity.yaml` | Composite | activity | Composite activity entity merging data from multiple providers. | enabled (default) |
| `composite_assay` | `configs/entities/composite/assay.yaml` | Composite | assay | Composite assay entity merging data from multiple providers. | enabled (default) |
| `composite_molecule` | `configs/entities/composite/molecule.yaml` | Composite | molecule | Composite molecule entity merging data from multiple providers. | enabled (default) |
| `composite_publication` | `configs/entities/composite/publication.yaml` | Composite | publication | Composite publication entity merging data from multiple providers. | enabled (default) |
| `composite_target` | `configs/entities/composite/target.yaml` | Composite | target | Composite target entity merging data from multiple providers. | enabled (default) |

## Composite Merge Catalog

| Composite | Merge config | Version | Runtime owner | Notes |
| --- | --- | --- | --- | --- |
| `composite_activity` | `configs/composites/activity.yaml` | 1.0.0 | `src/bioetl/application/composite/` | Uses seed, dependencies, enrichers, merge, cross-validation, DQ overrides, execution, lineage. |
| `composite_assay` | `configs/composites/assay.yaml` | 1.0.0 | `src/bioetl/application/composite/` | Uses seed, dependencies, enrichers, merge, cross-validation, DQ overrides, execution, lineage. |
| `composite_molecule` | `configs/composites/molecule.yaml` | 1.0.0 | `src/bioetl/application/composite/` | Uses normalized anchor/join policy plus seed/enrich/merge config. |
| `composite_publication` | `configs/composites/publication.yaml` | 1.1.0 | `src/bioetl/application/composite/` | Combines publication data from ChEMBL, CrossRef, OpenAlex, PubMed, Semantic Scholar. |
| `composite_target` | `configs/composites/target.yaml` | 1.3.0 | `src/bioetl/application/composite/` | Uses normalized anchor and UniProt mapping join boundary policies. |

## Dependency Model

Provider pipelines are configured declaratively and wired through composition:

```mermaid
flowchart LR
    EntityConfig["configs/entities/**/*.yaml"]
    ProviderConfig["configs/providers/*.yaml"]
    Loader["infrastructure.config pipeline/composite loaders"]
    Registry["composition registry_api and pipeline factory registry"]
    Factory["GenericPipelineFactory / RunnerFactory"]
    Runner["application.core.PipelineRunner"]
    Ports["domain ports"]
    Adapters["infrastructure adapters/storage/observability"]

    EntityConfig --> Loader
    ProviderConfig --> Loader
    Loader --> Registry
    Registry --> Factory
    Factory --> Runner
    Runner --> Ports
    Factory --> Adapters
    Adapters --> Ports
```

## Filter Compatibility Status

The pipeline config boundary no longer supports runtime compatibility for
legacy semantic Silver filters:

| Surface | Evidence | Current behavior |
| --- | --- | --- |
| Entity YAML | `configs/entities/**/*.yaml` | Active `filters.silver_filters` are structural-only; semantic keys were moved to `gold_filters` or dropped as duplicates. |
| Validation helper | `src/bioetl/infrastructure/config/silver_filter_migration.py` | `validate_no_semantic_silver_filter_payload()` rejects semantic keys under `silver_filters`. |
| Pipeline schema | `src/bioetl/infrastructure/schemas/pipeline_config.py` | `PipelineYamlConfig.reject_semantic_silver_filters()` fails before field validation. |
| Domain projection | `src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py` | `SilverFiltersConfig.to_domain()` returns structural-only `SilverFilterConfig`. |
| Source profiles | `configs/entities/chembl/*.yaml` | Curated ChEMBL `extraction_params` profiles are explicitly versioned as baseline and are not widened by Silver/Gold cleanup. |

Future source-side widening must update `filters.source_profile` separately and
prove Gold/Silver parity before changing provider extraction params.

## Regeneration Workflow

Refresh this page whenever any of the following changes:

- `configs/entities/**/*.yaml`
- `configs/composites/*.yaml`
- `configs/providers/*.yaml`

Revalidate the updated inventory against:

1. active provider and pipeline reference pages under `docs/04-reference/`;
2. composition/runtime owners under `src/bioetl/composition/` and
   `src/bioetl/application/composite/`;
3. the current workflow inventory in [workflow-catalog.md](workflow-catalog.md)
   when declarative workflows or composite packs depend on the changed
   pipeline/config surfaces.
