# Duplication Baseline Report

- mode: fail-fast
- targets: 5
- total_duplicate_clusters: 9
- max_duplicate_clusters: 9

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 2 |
| `src/bioetl/composition/bootstrap/runtime` | 1 |
| `src/bioetl/composition/factories/pipeline` | 1 |
| `src/bioetl/application/services/control_plane` | 0 |
| `src/bioetl/composition/runtime_builders` | 5 |

## src/bioetl/application/core

- duplicate clusters: 2
- raw duplicate clusters: 6
- excluded duplicate clusters: 4

| Actionability category | Duplicate clusters |
| --- | ---: |
| `behavior_bearing_candidate` | 2 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.core._quarantine_metrics_support` <-> `bioetl.application.core.batch_metrics` | 2 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/core/wiring/registry.py:1` | `bioetl.application.core._quarantine_metrics_support`[108:118], `bioetl.application.core.batch_metrics`[340:347] |
| `src/bioetl/application/core/wiring/registry.py:1` | `bioetl.application.core._quarantine_metrics_support`[108:117], `bioetl.application.core.batch_metrics`[312:318] |

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
| `src/bioetl/composition/bootstrap/runtime/composite_support_helpers.py:1` | `bioetl.composition.bootstrap.runtime.observability_bundle`[212:219], `bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases`[105:112] |

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
| `src/bioetl/composition/factories/pipeline/_runner_assembly_support.py:1` | `bioetl.composition.factories.pipeline._creation_wiring`[97:104], `bioetl.composition.factories.pipeline._factory_method_types`[50:59] |

## src/bioetl/application/services/control_plane

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/runtime_builders

- duplicate clusters: 5

| Actionability category | Duplicate clusters |
| --- | ---: |
| `composition_runtime_wiring_pattern` | 5 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.runtime_builders._run_manifest_control_plane_paths` <-> `bioetl.composition.runtime_builders._run_manifest_data_roots` | 2 |
| `bioetl.composition.runtime_builders._manifest_publication_context_support` <-> `bioetl.composition.runtime_builders.run_manifest_builder` | 1 |
| `bioetl.composition.runtime_builders._run_manifest_identity_ref_values` <-> `bioetl.composition.runtime_builders._run_manifest_refs` | 1 |
| `bioetl.composition.runtime_builders._runner_control_plane_policy` <-> `bioetl.composition.runtime_builders._runner_control_plane_policy_support` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[21:39], `bioetl.composition.runtime_builders._run_manifest_data_roots`[88:106] |
| `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[37:51], `bioetl.composition.runtime_builders._run_manifest_data_roots`[114:133] |
| `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_identity_ref_values`[39:54], `bioetl.composition.runtime_builders._run_manifest_refs`[110:119] |
| `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py:1` | `bioetl.composition.runtime_builders._runner_control_plane_policy`[108:127], `bioetl.composition.runtime_builders._runner_control_plane_policy_support`[153:171] |
| `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py:1` | `bioetl.composition.runtime_builders._manifest_publication_context_support`[158:163], `bioetl.composition.runtime_builders.run_manifest_builder`[193:198] |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/composition/runtime_builders` | 5 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/composition/bootstrap/runtime` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/composition/factories/pipeline` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/application/core` | 2 | `behavior_bearing_candidate` | 0.00 | no |
| `src/bioetl/application/services/control_plane` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/composition/runtime_builders`
- duplicate_clusters: 5
- dominant_actionability_category: `composition_runtime_wiring_pattern`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
