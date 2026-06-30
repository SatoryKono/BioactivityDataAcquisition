# Duplication Baseline Report

- mode: fail-fast
- targets: 4
- total_duplicate_clusters: 68
- max_duplicate_clusters: 69

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/interfaces/cli` | 0 |
| `src/bioetl/infrastructure/adapters` | 55 |
| `src/bioetl/application/pipelines` | 13 |
| `src/bioetl/composition/bootstrap` | 0 |

## src/bioetl/interfaces/cli

- duplicate clusters: 0

| Actionability category | Duplicate clusters |
| --- | ---: |
| `cli_command_contract_shell` | 0 |
- no `R0801` findings

## src/bioetl/infrastructure/adapters

- duplicate clusters: 55

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 44 |
| `adapter_resilience_or_contract_template` | 11 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.openalex._filter_fetch_requests` <-> `bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin` | 2 |
| `bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin` <-> `bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin` | 2 |
| `bioetl.infrastructure.adapters.pubmed._filter_fetch_support` <-> `bioetl.infrastructure.adapters.semanticscholar.fetch_adapter_mixin` | 2 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl._fetch_resilience_error`[22:36], `bioetl.infrastructure.adapters.chembl._fetch_resilience_fallback`[58:81] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.health_check_contract`[12:22], `bioetl.infrastructure.adapters.uniprot.client`[54:64] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin`[57:66], `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`[120:141] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.models_common`[112:123], `bioetl.infrastructure.adapters.chembl.models_compound`[100:109] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[245:254], `bioetl.infrastructure.adapters.pubchem.client_model_mixin`[88:97] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref._batch_support`[53:61], `bioetl.infrastructure.adapters.pubchem.fetch_strategies`[53:75] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.decorators.circuit_breaker`[167:175], `bioetl.infrastructure.adapters.decorators.retry`[147:156] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._health`[43:51], `bioetl.infrastructure.adapters.pubmed._state`[18:26] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations`[11:19], `bioetl.infrastructure.adapters.uniprot.models`[46:54] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.filterable_mixin`[173:182], `bioetl.infrastructure.adapters.uniprot.client`[199:206] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[247:254], `bioetl.infrastructure.adapters.pubmed.adapter`[156:163] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin`[59:66], `bioetl.infrastructure.adapters.common.fetch_resilience_template`[114:125] |

- … truncated 43 additional clusters for brevity

## src/bioetl/application/pipelines

- duplicate clusters: 13

| Actionability category | Duplicate clusters |
| --- | ---: |
| `pipeline_transformer_contract_pattern` | 13 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.pipelines.chembl._activity_transformer_maps` <-> `bioetl.application.pipelines.chembl.assay_parameters_transformer` | 1 |
| `bioetl.application.pipelines.chembl.base_chembl_transformer` <-> `bioetl.application.pipelines.crossref.transformer` | 1 |
| `bioetl.application.pipelines.crossref.__init__` <-> `bioetl.application.pipelines.crossref.extractors` | 1 |
| `bioetl.application.pipelines.crossref.transformer` <-> `bioetl.application.pipelines.openalex.transformer` | 1 |
| `bioetl.application.pipelines.openalex._extractors_authors` <-> `bioetl.application.pipelines.openalex.extractors` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.__init__`[26:38], `bioetl.application.pipelines.crossref.extractors`[35:80] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:100], `bioetl.application.pipelines.uniprot.transformer`[56:76] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.transformer`[89:104], `bioetl.application.pipelines.openalex.transformer`[106:125] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:99], `bioetl.application.pipelines.pubmed.transformer`[95:106] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.semanticscholar.transformer`[104:121], `bioetl.application.pipelines.uniprot.idmapping_transformer`[95:127] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.uniprot.extractors._comment_facets`[26:37], `bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors`[139:150] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.base_chembl_transformer`[109:120], `bioetl.application.pipelines.crossref.transformer`[92:104] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl._activity_transformer_maps`[87:95], `bioetl.application.pipelines.chembl.assay_parameters_transformer`[35:43] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubmed._block_definitions_analytics`[48:55], `bioetl.application.pipelines.pubmed.transformer`[261:268] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.semanticscholar._author_extractors`[10:16], `bioetl.application.pipelines.semanticscholar.extractors`[293:299] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.openalex._extractors_authors`[182:187], `bioetl.application.pipelines.openalex.extractors`[30:35] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.openalex._extractors_publication_fields`[231:236], `bioetl.application.pipelines.openalex.extractors`[42:47] |

- … truncated 1 additional clusters for brevity

## src/bioetl/composition/bootstrap

- duplicate clusters: 0
- no `R0801` findings

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/infrastructure/adapters` | 55 | `export_facade_or_package_barrel` | 0.80 | no |
| `src/bioetl/application/pipelines` | 13 | `pipeline_transformer_contract_pattern` | 0.00 | no |
| `src/bioetl/composition/bootstrap` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/interfaces/cli` | 0 | `cli_command_contract_shell` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/infrastructure/adapters`
- duplicate_clusters: 55
- dominant_actionability_category: `export_facade_or_package_barrel`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
