# Duplication Baseline Report

- mode: report-only
- targets: 4
- total_duplicate_clusters: 44

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/infrastructure/adapters` | 41 |
| `src/bioetl/application/pipelines` | 3 |
| `src/bioetl/composition/bootstrap` | 0 |
| `src/bioetl/interfaces/cli` | 0 |

## src/bioetl/infrastructure/adapters

- duplicate clusters: 41

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 41 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.infrastructure.adapters.openalex._filter_fetch_requests` <-> `bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin` | 2 |
| `bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin` <-> `bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin` | 2 |
| `bioetl.infrastructure.adapters.chembl.client` <-> `bioetl.infrastructure.adapters.crossref.client` | 1 |
| `bioetl.infrastructure.adapters.chembl.client` <-> `bioetl.infrastructure.adapters.decorators.circuit_breaker` | 1 |
| `bioetl.infrastructure.adapters.chembl.client` <-> `bioetl.infrastructure.adapters.pubchem.client_model_mixin` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.models_common`[112:123], `bioetl.infrastructure.adapters.chembl.models_compound`[100:109] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[245:254], `bioetl.infrastructure.adapters.pubchem.client_model_mixin`[88:97] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.decorators.circuit_breaker`[168:176], `bioetl.infrastructure.adapters.decorators.retry`[150:159] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._health`[43:51], `bioetl.infrastructure.adapters.pubmed._state`[18:26] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations`[11:19], `bioetl.infrastructure.adapters.uniprot.models`[46:54] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.filterable_mixin`[196:205], `bioetl.infrastructure.adapters.uniprot.client`[194:201] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[247:254], `bioetl.infrastructure.adapters.pubmed.adapter`[156:163] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.client`[84:91], `bioetl.infrastructure.adapters.pubmed.adapter`[101:108] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.client_builders`[170:179], `bioetl.infrastructure.adapters.crossref.client_runtime_helpers`[104:111] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.models`[35:42], `bioetl.infrastructure.adapters.crossref.models_shared`[148:155] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref._doi_batch_processor`[42:52], `bioetl.infrastructure.adapters.crossref._search_paginator`[38:50] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.decorators._fetch_request_builder`[22:29], `bioetl.infrastructure.adapters.decorators.circuit_breaker`[169:176] |

- … truncated 29 additional clusters for brevity

## src/bioetl/application/pipelines

- duplicate clusters: 3

| Actionability category | Duplicate clusters |
| --- | ---: |
| `pipeline_transformer_contract_pattern` | 3 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.pipelines.chembl._activity_transformer_maps` <-> `bioetl.application.pipelines.chembl.assay_parameters_transformer` | 1 |
| `bioetl.application.pipelines.chembl.base_chembl_transformer` <-> `bioetl.application.pipelines.common.publication_transformer_context` | 1 |
| `bioetl.application.pipelines.pubmed._block_definitions_analytics` <-> `bioetl.application.pipelines.pubmed.transformer` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.base_chembl_transformer`[109:120], `bioetl.application.pipelines.common.publication_transformer_context`[178:187] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl._activity_transformer_maps`[87:95], `bioetl.application.pipelines.chembl.assay_parameters_transformer`[35:43] |
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
| `src/bioetl/infrastructure/adapters` | 41 | `export_facade_or_package_barrel` | 1.00 | no |
| `src/bioetl/application/pipelines` | 3 | `pipeline_transformer_contract_pattern` | 0.00 | no |
| `src/bioetl/composition/bootstrap` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/interfaces/cli` | 0 | `cli_command_contract_shell` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/infrastructure/adapters`
- duplicate_clusters: 41
- dominant_actionability_category: `export_facade_or_package_barrel`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
