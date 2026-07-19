# Duplication Baseline Report

- mode: fail-fast
- targets: 5
- total_duplicate_clusters: 14
- max_duplicate_clusters: 0
- previous_snapshot_date: 2026-07-17
- total_duplicate_cluster_delta_vs_previous: +4

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 6 |
| `src/bioetl/composition/bootstrap/runtime` | 1 |
| `src/bioetl/composition/factories/pipeline` | 1 |
| `src/bioetl/application/services/control_plane` | 1 |
| `src/bioetl/composition/runtime_builders` | 5 |

## src/bioetl/application/core

- duplicate clusters: 6

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 6 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.core.batch_execution.contracts` <-> `bioetl.application.core.batch_executor_state_flow` | 1 |
| `bioetl.application.core.batch_operation_errors` <-> `bioetl.application.core.preflight.health_aggregator` | 1 |
| `bioetl.application.core.wiring.__init__` <-> `bioetl.application.core.wiring.__init__` | 1 |
| `bioetl.application.core.wiring.factory` <-> `bioetl.application.core.wiring.factory` | 1 |
| `bioetl.application.core.wiring.registry` <-> `bioetl.application.core.wiring.registry` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.wiring.registry`[13:66], `bioetl.application.core.wiring.registry`[13:66] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.wiring.__init__`[11:46], `bioetl.application.core.wiring.__init__`[11:46] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.wiring.transformer`[13:33], `bioetl.application.core.wiring.transformer`[13:33] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.wiring.factory`[13:29], `bioetl.application.core.wiring.factory`[13:29] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.batch_execution.contracts`[15:23], `bioetl.application.core.batch_executor_state_flow`[32:38] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.batch_operation_errors`[9:19], `bioetl.application.core.preflight.health_aggregator`[32:40] |

## src/bioetl/composition/bootstrap/runtime

- duplicate clusters: 1

| Actionability category | Duplicate clusters |
| --- | ---: |
| `composition_runtime_wiring_pattern` | 1 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.bootstrap.runtime.observability_bundle` <-> `bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\composition\bootstrap\runtime\_runner_assembly_support.py:1` | `bioetl.composition.bootstrap.runtime.observability_bundle`[212:219], `bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases`[95:102] |

## src/bioetl/composition/factories/pipeline

- duplicate clusters: 1

| Actionability category | Duplicate clusters |
| --- | ---: |
| `composition_runtime_wiring_pattern` | 1 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.factories.pipeline._creation_wiring` <-> `bioetl.composition.factories.pipeline._factory_method_types` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\composition\factories\pipeline\_runner_assembly_support.py:1` | `bioetl.composition.factories.pipeline._creation_wiring`[97:104], `bioetl.composition.factories.pipeline._factory_method_types`[50:59] |

## src/bioetl/application/services/control_plane

- duplicate clusters: 1

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 1 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection` <-> `bioetl.application.services.control_plane.manifest.diagnostics.resume_contract` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\application\services\control_plane\workflow\__init__.py:1` | `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection`[103:109], `bioetl.application.services.control_plane.manifest.diagnostics.resume_contract`[83:89] |

## src/bioetl/composition/runtime_builders

- duplicate clusters: 5

| Actionability category | Duplicate clusters |
| --- | ---: |
| `composition_runtime_wiring_pattern` | 5 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.runtime_builders._run_manifest_control_plane_paths` <-> `bioetl.composition.runtime_builders._run_manifest_data_roots` | 2 |
| `bioetl.composition.runtime_builders._manifest_publication_context_support` <-> `bioetl.composition.runtime_builders.run_manifest_builder` | 1 |
| `bioetl.composition.runtime_builders._run_manifest_data_roots` <-> `bioetl.composition.runtime_builders._run_manifest_refs` | 1 |
| `bioetl.composition.runtime_builders._runner_control_plane_policy` <-> `bioetl.composition.runtime_builders._runner_control_plane_policy_support` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_data_roots`[46:67], `bioetl.composition.runtime_builders._run_manifest_refs`[21:40] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[21:39], `bioetl.composition.runtime_builders._run_manifest_data_roots`[88:106] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[37:51], `bioetl.composition.runtime_builders._run_manifest_data_roots`[114:133] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._runner_control_plane_policy`[108:127], `bioetl.composition.runtime_builders._runner_control_plane_policy_support`[153:171] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._manifest_publication_context_support`[158:163], `bioetl.composition.runtime_builders.run_manifest_builder`[185:190] |

## Trend vs Previous Snapshot

- previous snapshot: `2026-07-17`
- total duplicate cluster delta: +4

| Target | Current | Previous | Delta |
| --- | ---: | ---: | ---: |
| `src/bioetl/application/core` | 6 | 2 | +4 |
| `src/bioetl/composition/bootstrap/runtime` | 1 | 1 | +0 |
| `src/bioetl/composition/factories/pipeline` | 1 | 1 | +0 |
| `src/bioetl/application/services/control_plane` | 1 | 1 | +0 |
| `src/bioetl/composition/runtime_builders` | 5 | 5 | +0 |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/core` | 6 | `export_facade_or_package_barrel` | 1.00 | yes |
| `src/bioetl/composition/runtime_builders` | 5 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/application/services/control_plane` | 1 | `export_facade_or_package_barrel` | 1.00 | yes |
| `src/bioetl/composition/bootstrap/runtime` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/composition/factories/pipeline` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |

## First Wave Selection

- target: `src/bioetl/application/core`
- duplicate_clusters: 6
- dominant_actionability_category: `export_facade_or_package_barrel`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
