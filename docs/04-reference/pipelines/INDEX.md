______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# Pipeline Operational Coverage

> **Canonical pipeline catalog:** [README.md](README.md)
>
> This page is the operational facet supplement for the current catalog of
> `27` active pipeline surfaces (`22` provider entity pipelines and `5`
> composite entity pipelines). The config-backed inventory remains
> [pipeline-catalog.md](../pipeline-catalog.md).
>
> Primary keys, effective merge mode, nullability counts, and Gold contract
> ownership are maintained in
> [Contract Facet Matrix](contract-facet-matrix.md).

## Operational Facet Coverage

Every active per-pipeline spec is covered by the matrix below. For documentation
facets, `Direct` means the linked spec has pipeline-local detail and `Shared`
means the common pipeline/config/control-plane contract below governs the
facet. Documentation coverage is intentionally separate from effective runtime
state: `Gold docs` records where behavior is described, while `Gold runtime`
records whether the effective `pipeline.sink.gold.enabled` value enables the
sink. `Disabled` is reserved for an effective runtime value of `false`; it must
not be inferred from unrelated flags such as
`filters.input_filter.enabled: false`. `N/A` means the facet does not apply.

`SinkLayerConfig.enabled` defaults to `true` in
`src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py`.
Consequently, a pipeline whose entity YAML omits
`pipeline.sink.gold.enabled` is runtime-enabled after config loading. The
effective-config reports
`reports/quality/pipeline-config-contract-ownership-map.json` and
`reports/quality/contract-coverage-matrix.json` currently confirm all `27`
pipeline Gold sinks as enabled.

Shared evidence sources:

- Bronze, Silver, and Gold inventory:
  [pipeline-catalog.md](../pipeline-catalog.md),
  [gold-schemas.md](../contracts/gold-schemas.md), and
  [data-contracts-current.md](../contracts/data-contracts-current.md).
- DQ and quarantine handling:
  [dq-contracts.md](../contracts/dq-contracts.md),
  [quarantine-management.md](../../05-operations/runbooks/quarantine-management.md),
  and
  [dq-failure-investigation.md](../../05-operations/runbooks/dq-failure-investigation.md).
- Replay, checkpoint, and run lifecycle:
  [run-manifest-ledger.md](../contracts/run-manifest-ledger.md),
  [checkpoint-debugging.md](../../05-operations/runbooks/checkpoint-debugging.md),
  [run-manifest-inspection.md](../../05-operations/runbooks/run-manifest-inspection.md),
  and
  [workflow-control-plane.md](../../05-operations/runbooks/workflow-control-plane.md).
- Config owner paths:
  `configs/entities/{provider}/{entity}.yaml` for provider/entity pipelines and
  `configs/entities/composite/{entity}.yaml` plus
  `configs/composites/{entity}.yaml` for composite pipelines.

| Pipeline | Spec | Bronze | Silver | Gold docs | Gold runtime | DQ / Quarantine | Replay / Checkpoint | Run lifecycle | Config owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `chembl_protein_class` | [Spec](chembl/01-protein-class-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/protein_class.yaml` |
| `chembl_cell_line` | [Spec](chembl/02-cell-line-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/chembl/cell_line.yaml` |
| `chembl_molecule` | [Spec](chembl/03-molecule-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/molecule.yaml` |
| `chembl_target` | [Spec](chembl/04-target-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/target.yaml` |
| `chembl_activity` | [Spec](chembl/05-activity-spec.md) | Direct | Direct | Direct | Enabled | Direct / Shared | Direct | Shared | `configs/entities/chembl/activity.yaml` |
| `chembl_assay` | [Spec](chembl/06-assay-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/chembl/assay.yaml` |
| `chembl_publication` | [Spec](chembl/07-publication-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/publication.yaml` |
| `chembl_assay_parameters` | [Spec](chembl/08-assay-parameters-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/assay_parameters.yaml` |
| `chembl_compound_record` | [Spec](chembl/09-compound-record-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/compound_record.yaml` |
| `chembl_target_component` | [Spec](chembl/10-target-component-spec.md) | Shared | Shared | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/target_component.yaml` |
| `chembl_target_protein_classification` | [Spec](chembl/11-target-protein-classification-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/target_protein_classification.yaml` |
| `chembl_publication_term` | [Spec](chembl/13-publication-term-spec.md) | Shared | Shared | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/publication_term.yaml` |
| `chembl_publication_similarity` | [Spec](chembl/12-publication-similarity-spec.md) | Shared | Shared | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/publication_similarity.yaml` |
| `chembl_subcellular_fraction` | [Spec](chembl/14-subcellular-fraction-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/chembl/subcellular_fraction.yaml` |
| `chembl_tissue` | [Spec](chembl/15-tissue-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/chembl/tissue.yaml` |
| `uniprot_protein` | [Spec](uniprot/01-protein-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Direct / Shared | Shared | `configs/entities/uniprot/protein.yaml` |
| `uniprot_idmapping` | [Spec](uniprot/02-idmapping-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/uniprot/idmapping.yaml` |
| `pubchem_compound` | [Spec](pubchem/01-compound-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/pubchem/compound.yaml` |
| `pubmed_publication` | [Spec](pubmed/01-publication-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/pubmed/publication.yaml` |
| `crossref_publication` | [Spec](crossref/01-publication-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/crossref/publication.yaml` |
| `openalex_publication` | [Spec](openalex/01-publication-spec.md) | Direct | Direct | Direct | Enabled | Shared | Direct / Shared | Shared | `configs/entities/openalex/publication.yaml` |
| `semanticscholar_publication` | [Spec](semanticscholar/01-publication-spec.md) | Direct | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/semanticscholar/publication.yaml` |
| `composite_publication` | [Spec](composite/01-publication-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/composite/publication.yaml`; `configs/composites/publication.yaml` |
| `composite_molecule` | [Spec](composite/02-molecule-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/composite/molecule.yaml`; `configs/composites/molecule.yaml` |
| `composite_target` | [Spec](composite/03-target-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/composite/target.yaml`; `configs/composites/target.yaml` |
| `composite_activity` | [Spec](composite/04-activity-spec.md) | Shared | Direct | Direct | Enabled | Direct / Shared | Shared | Shared | `configs/entities/composite/activity.yaml`; `configs/composites/activity.yaml` |
| `composite_assay` | [Spec](composite/05-assay-spec.md) | Shared | Direct | Direct | Enabled | Shared | Shared | Shared | `configs/entities/composite/assay.yaml`; `configs/composites/assay.yaml` |

## Publication Pipeline Specs

Publication-specific pipeline details remain available in the individual specs:

- [ChEMBL Publication](chembl/07-publication-spec.md)
- [CrossRef Publication](crossref/01-publication-spec.md)
- [OpenAlex Publication](openalex/01-publication-spec.md)
- [PubMed Publication](pubmed/01-publication-spec.md)
- [Semantic Scholar Publication](semanticscholar/01-publication-spec.md)
- [Composite Publication](composite/01-publication-spec.md)
