# Duplication Baseline Report

- mode: report-only
- targets: 4
- total_duplicate_clusters: 82

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/infrastructure/adapters` | 63 |
| `src/bioetl/application/pipelines` | 17 |
| `src/bioetl/composition/bootstrap` | 0 |
| `src/bioetl/interfaces/cli` | 2 |

## src/bioetl/infrastructure/adapters

- duplicate clusters: 63

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 52 |
| `adapter_resilience_or_contract_template` | 11 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.infrastructure.adapters.crossref.client` <-> `bioetl.infrastructure.adapters.crossref.client_fetch_helpers` | 3 |
| `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.decorators.circuit_breaker` <-> `bioetl.infrastructure.adapters.decorators.retry` | 2 |
| `bioetl.infrastructure.adapters.openalex._filter_fetch_requests` <-> `bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin` | 2 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_paging_mixin`[22:50], `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`[33:61] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl._fetch_resilience_fallback`[58:81], `bioetl.infrastructure.adapters.chembl.fetch_paging_mixin`[36:50] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._fetch`[36:58], `bioetl.infrastructure.adapters.pubmed._search`[35:52] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.health_check_contract`[12:22], `bioetl.infrastructure.adapters.uniprot.client`[54:64] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin`[57:66], `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`[134:155] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.models_common`[112:123], `bioetl.infrastructure.adapters.chembl.models_compound`[100:109] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[245:254], `bioetl.infrastructure.adapters.pubchem.client_model_mixin`[88:97] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref._batch_support`[53:61], `bioetl.infrastructure.adapters.pubchem.fetch_strategies`[53:75] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.decorators.circuit_breaker`[155:175], `bioetl.infrastructure.adapters.decorators.retry`[138:146] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.decorators.circuit_breaker`[177:185], `bioetl.infrastructure.adapters.decorators.retry`[198:209] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._fetch`[36:44], `bioetl.infrastructure.adapters.pubmed._health`[43:51] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.uniprot._uniprot_model_annotations`[11:19], `bioetl.infrastructure.adapters.uniprot.models`[46:54] |

- … truncated 51 additional clusters for brevity

## src/bioetl/application/pipelines

- duplicate clusters: 17

| Actionability category | Duplicate clusters |
| --- | ---: |
| `pipeline_transformer_contract_pattern` | 17 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.pipelines.uniprot.extractors._comment_facets_data` <-> `bioetl.application.pipelines.uniprot.transformer_business_data_mixin` | 2 |
| `bioetl.application.pipelines.chembl.__init__` <-> `bioetl.application.pipelines.chembl.pipeline_types` | 1 |
| `bioetl.application.pipelines.chembl._activity_transformer_maps` <-> `bioetl.application.pipelines.chembl.assay_parameters_transformer` | 1 |
| `bioetl.application.pipelines.chembl.base_chembl_transformer` <-> `bioetl.application.pipelines.crossref.transformer` | 1 |
| `bioetl.application.pipelines.crossref.__init__` <-> `bioetl.application.pipelines.crossref.extractors` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.__init__`[90:105], `bioetl.application.pipelines.chembl.pipeline_types`[10:25] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.__init__`[26:38], `bioetl.application.pipelines.crossref.extractors`[35:80] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:100], `bioetl.application.pipelines.uniprot.transformer`[56:76] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.transformer`[90:105], `bioetl.application.pipelines.openalex.transformer`[106:125] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:99], `bioetl.application.pipelines.pubmed.transformer`[96:107] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.semanticscholar.transformer`[104:121], `bioetl.application.pipelines.uniprot.idmapping_transformer`[95:127] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.uniprot.extractors._comment_facets`[26:37], `bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors`[139:150] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.base_chembl_transformer`[109:120], `bioetl.application.pipelines.crossref.transformer`[93:105] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.uniprot.extractors._comment_facets_data`[56:64], `bioetl.application.pipelines.uniprot.transformer_business_data_mixin`[182:190] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl._activity_transformer_maps`[87:95], `bioetl.application.pipelines.chembl.assay_parameters_transformer`[35:43] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubmed._block_definitions_analytics`[48:55], `bioetl.application.pipelines.pubmed.transformer`[267:274] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.transformer`[136:150], `bioetl.application.pipelines.pubmed.transformer`[228:237] |

- … truncated 5 additional clusters for brevity

## src/bioetl/composition/bootstrap

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/interfaces/cli

- duplicate clusters: 2

| Actionability category | Duplicate clusters |
| --- | ---: |
| `cli_command_contract_shell` | 2 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.interfaces.cli.commands.domains.health.server_integration` <-> `bioetl.interfaces.cli.commands.vacuum` | 1 |
| `bioetl.interfaces.cli.commands.domains.run_all.public_runtime` <-> `bioetl.interfaces.cli.commands.run` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.run_all.public_runtime`[169:176], `bioetl.interfaces.cli.commands.run`[284:291] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.health.server_integration`[118:123], `bioetl.interfaces.cli.commands.vacuum`[58:63] |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/interfaces/cli` | 2 | `cli_command_contract_shell` | 1.00 | yes |
| `src/bioetl/infrastructure/adapters` | 63 | `export_facade_or_package_barrel` | 0.83 | no |
| `src/bioetl/application/pipelines` | 17 | `pipeline_transformer_contract_pattern` | 0.00 | no |
| `src/bioetl/composition/bootstrap` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/interfaces/cli`
- duplicate_clusters: 2
- dominant_actionability_category: `cli_command_contract_shell`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
