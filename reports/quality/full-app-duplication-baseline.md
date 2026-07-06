# Duplication Baseline Report

- mode: report-only
- targets: 4
- total_duplicate_clusters: 2
- total_raw_duplicate_clusters: 40
- excluded_duplicate_clusters: 38
- normalized_view: enabled
- exclude_actionability_categories: `export_facade_or_package_barrel`

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/infrastructure/adapters` | 0 |
| `src/bioetl/application/pipelines` | 2 |
| `src/bioetl/composition/bootstrap` | 0 |
| `src/bioetl/interfaces/cli` | 0 |

## src/bioetl/infrastructure/adapters

- duplicate clusters: 0
- raw duplicate clusters: 38
- excluded duplicate clusters: 38
- no `R0801` findings

## src/bioetl/application/pipelines

- duplicate clusters: 2

| Actionability category | Duplicate clusters |
| --- | ---: |
| `pipeline_transformer_contract_pattern` | 2 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.pipelines.chembl.base_chembl_transformer` <-> `bioetl.application.pipelines.common.publication_transformer_context` | 1 |
| `bioetl.application.pipelines.pubmed._block_definitions_analytics` <-> `bioetl.application.pipelines.pubmed.transformer` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.base_chembl_transformer`[109:120], `bioetl.application.pipelines.common.publication_transformer_context`[178:187] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubmed._block_definitions_analytics`[48:55], `bioetl.application.pipelines.pubmed.transformer`[254:261] |

## src/bioetl/composition/bootstrap

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/interfaces/cli

- duplicate clusters: 0

| Actionability category | Duplicate clusters |
| --- | ---: |
| `cli_command_contract_shell` | 0 |
- no `R0801` findings

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/pipelines` | 2 | `pipeline_transformer_contract_pattern` | 0.00 | no |
| `src/bioetl/composition/bootstrap` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/infrastructure/adapters` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/interfaces/cli` | 0 | `cli_command_contract_shell` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/application/pipelines`
- duplicate_clusters: 2
- dominant_actionability_category: `pipeline_transformer_contract_pattern`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
