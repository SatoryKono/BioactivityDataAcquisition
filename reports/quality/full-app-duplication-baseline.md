# Duplication Baseline Report

- mode: report-only
- targets: 4
- total_duplicate_clusters: 113

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/infrastructure/adapters` | 72 |
| `src/bioetl/application/pipelines` | 22 |
| `src/bioetl/composition/bootstrap` | 2 |
| `src/bioetl/interfaces/cli` | 17 |

## src/bioetl/infrastructure/adapters

- duplicate clusters: 72

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.infrastructure.adapters.crossref.client` <-> `bioetl.infrastructure.adapters.crossref.client_fetch_helpers` | 3 |
| `bioetl.infrastructure.adapters.chembl.__init__` <-> `bioetl.infrastructure.adapters.chembl.models` | 2 |
| `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin` <-> `bioetl.infrastructure.adapters.common.fetch_resilience_template` | 2 |
| `bioetl.infrastructure.adapters.crossref.client` <-> `bioetl.infrastructure.adapters.openalex.client` | 2 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_paging_mixin`[22:50], `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`[33:61] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl._fetch_resilience_fallback`[58:81], `bioetl.infrastructure.adapters.chembl.fetch_paging_mixin`[36:50] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._fetch`[47:69], `bioetl.infrastructure.adapters.pubmed._search`[46:63] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.__init__`[43:54], `bioetl.infrastructure.adapters.chembl.models`[58:69] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.health_check_contract`[12:22], `bioetl.infrastructure.adapters.uniprot.client`[54:64] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.client`[75:87], `bioetl.infrastructure.adapters.semanticscholar.adapter`[61:93] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin`[57:66], `bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`[134:155] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.models_common`[112:123], `bioetl.infrastructure.adapters.chembl.models_compound`[100:109] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.fallback`[24:36], `bioetl.infrastructure.adapters.pubmed.fallback`[26:37] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.pubmed._fetch`[33:44], `bioetl.infrastructure.adapters.pubmed._search`[32:43] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.chembl.client`[245:254], `bioetl.infrastructure.adapters.pubchem.client_model_mixin`[88:97] |
| `src/bioetl/infrastructure/adapters/uniprot/__init__.py:1` | `bioetl.infrastructure.adapters.crossref.client`[75:83], `bioetl.infrastructure.adapters.openalex.client`[76:84] |

- … truncated 60 additional clusters for brevity

## src/bioetl/application/pipelines

- duplicate clusters: 22

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.pipelines.chembl.target_protein_classification_summary` <-> `bioetl.application.pipelines.chembl.target_protein_classification_transformer` | 2 |
| `bioetl.application.pipelines.common.blocks` <-> `bioetl.application.pipelines.crossref.blocks` | 2 |
| `bioetl.application.pipelines.uniprot.extractors._comment_facets_data` <-> `bioetl.application.pipelines.uniprot.transformer_business_data_mixin` | 2 |
| `bioetl.application.pipelines.chembl.__init__` <-> `bioetl.application.pipelines.chembl.pipeline_types` | 1 |
| `bioetl.application.pipelines.chembl._activity_transformer_maps` <-> `bioetl.application.pipelines.chembl.assay_parameters_transformer` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.__init__`[90:105], `bioetl.application.pipelines.chembl.pipeline_types`[10:25] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.__init__`[26:38], `bioetl.application.pipelines.crossref.extractors`[35:80] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:100], `bioetl.application.pipelines.uniprot.transformer`[56:76] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.crossref.transformer`[90:105], `bioetl.application.pipelines.openalex.transformer`[106:125] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubchem.transformer`[70:99], `bioetl.application.pipelines.pubmed.transformer`[96:107] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.semanticscholar.transformer`[104:121], `bioetl.application.pipelines.uniprot.idmapping_transformer`[95:127] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.uniprot.extractors._comment_facets`[26:37], `bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors`[139:150] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.pubmed.block_definitions`[19:29], `bioetl.application.pipelines.pubmed.blocks`[15:25] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.target_protein_classification_summary`[275:284], `bioetl.application.pipelines.chembl.target_protein_classification_transformer`[162:174] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl.base_chembl_transformer`[109:120], `bioetl.application.pipelines.crossref.transformer`[93:105] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.uniprot.extractors._comment_facets_data`[56:64], `bioetl.application.pipelines.uniprot.transformer_business_data_mixin`[182:190] |
| `src/bioetl/application/pipelines/uniprot/extractors/__init__.py:1` | `bioetl.application.pipelines.chembl._activity_transformer_maps`[87:95], `bioetl.application.pipelines.chembl.assay_parameters_transformer`[35:43] |

- … truncated 10 additional clusters for brevity

## src/bioetl/composition/bootstrap

- duplicate clusters: 2

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.bootstrap` <-> `bioetl.composition.bootstrap.runtime.__init__` | 1 |
| `bioetl.composition.bootstrap.composite_infrastructure_context` <-> `bioetl.composition.bootstrap.runtime._composite_plan_runtime_support` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/composition/bootstrap/runtime/__init__.py:1` | `bioetl.composition.bootstrap.runtime.__init__`[33:39], `bioetl.composition.bootstrap`[79:85] |
| `src/bioetl/composition/bootstrap/runtime/__init__.py:1` | `bioetl.composition.bootstrap.composite_infrastructure_context`[27:32], `bioetl.composition.bootstrap.runtime._composite_plan_runtime_support`[40:45] |

## src/bioetl/interfaces/cli

- duplicate clusters: 17

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.interfaces.cli.commands._run_manifest_output_support` <-> `bioetl.interfaces.cli.commands.domains.maintenance.plan` | 2 |
| `bioetl.interfaces.cli.commands._run_manifest_output` <-> `bioetl.interfaces.cli.commands._run_manifest_output_support` | 1 |
| `bioetl.interfaces.cli.commands._run_manifest_output` <-> `bioetl.interfaces.cli.commands.domains.maintenance.plan` | 1 |
| `bioetl.interfaces.cli.commands._workflow_command_runtime` <-> `bioetl.interfaces.cli.commands.workflow` | 1 |
| `bioetl.interfaces.cli.commands._workflow_run_support` <-> `bioetl.interfaces.cli.commands.workflow` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands._workflow_run_support`[137:162], `bioetl.interfaces.cli.commands.workflow`[294:319] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands._workflow_support`[101:122], `bioetl.interfaces.cli.commands.workflow`[295:316] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.run_all`[185:198], `bioetl.interfaces.cli.commands.run_composite`[318:330] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.composite.command_input`[20:31], `bioetl.interfaces.cli.commands.domains.composite.runtime`[19:42] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.health.server_integration`[113:127], `bioetl.interfaces.cli.commands.health`[83:97] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands._workflow_command_runtime`[65:75], `bioetl.interfaces.cli.commands.workflow`[323:333] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands._run_manifest_output_support`[11:27], `bioetl.interfaces.cli.commands.domains.maintenance.plan`[26:37] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.diagnostics`[343:350], `bioetl.interfaces.cli.commands.quarantine`[167:174] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.run_all.public_runtime`[176:183], `bioetl.interfaces.cli.commands.run`[284:291] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands._run_manifest_output_support`[45:52], `bioetl.interfaces.cli.commands.domains.maintenance.plan`[50:57] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.domains.shared.execution_policy`[57:62], `bioetl.interfaces.cli.exit_codes`[73:79] |
| `src/bioetl/interfaces/cli/commands/domains/shared/__init__.py:1` | `bioetl.interfaces.cli.commands.maintenance`[101:112], `bioetl.interfaces.cli.main`[164:175] |

- … truncated 5 additional clusters for brevity
