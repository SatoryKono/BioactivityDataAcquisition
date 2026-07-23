# Duplication Baseline Report

- mode: report-only
- targets: 5
- total_duplicate_clusters: 6
- previous_snapshot_date: 2026-07-22
- total_duplicate_cluster_delta_vs_previous: -7

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 0 |
| `src/bioetl/composition/bootstrap/runtime` | 1 |
| `src/bioetl/composition/factories/pipeline` | 1 |
| `src/bioetl/application/services/control_plane` | 0 |
| `src/bioetl/composition/runtime_builders` | 4 |

## src/bioetl/application/core

- duplicate clusters: 0
- raw duplicate clusters: 4
- excluded duplicate clusters: 4
- no `R0801` findings

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
| `src\bioetl\composition\bootstrap\runtime\_runner_assembly_support.py:1` | `bioetl.composition.bootstrap.runtime.observability_bundle`[212:219], `bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases`[105:112] |

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

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/runtime_builders

- duplicate clusters: 4

| Actionability category | Duplicate clusters |
| --- | ---: |
| `composition_runtime_wiring_pattern` | 4 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.composition.runtime_builders._run_manifest_control_plane_paths` <-> `bioetl.composition.runtime_builders._run_manifest_data_roots` | 2 |
| `bioetl.composition.runtime_builders._manifest_publication_context_support` <-> `bioetl.composition.runtime_builders.run_manifest_builder` | 1 |
| `bioetl.composition.runtime_builders._runner_control_plane_policy` <-> `bioetl.composition.runtime_builders._runner_control_plane_policy_support` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[21:39], `bioetl.composition.runtime_builders._run_manifest_data_roots`[88:106] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._run_manifest_control_plane_paths`[37:51], `bioetl.composition.runtime_builders._run_manifest_data_roots`[114:133] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._runner_control_plane_policy`[108:127], `bioetl.composition.runtime_builders._runner_control_plane_policy_support`[153:171] |
| `src\bioetl\composition\runtime_builders\_snapshot_mapping_support.py:1` | `bioetl.composition.runtime_builders._manifest_publication_context_support`[158:163], `bioetl.composition.runtime_builders.run_manifest_builder`[185:190] |

## Trend vs Previous Snapshot

- previous snapshot: `2026-07-22`
- total duplicate cluster delta: -7

| Target | Current | Previous | Delta |
| --- | ---: | ---: | ---: |
| `src/bioetl/application/core` | 0 | 6 | -6 |
| `src/bioetl/composition/bootstrap/runtime` | 1 | 1 | +0 |
| `src/bioetl/composition/factories/pipeline` | 1 | 1 | +0 |
| `src/bioetl/application/services/control_plane` | 0 | 0 | +0 |
| `src/bioetl/composition/runtime_builders` | 4 | 5 | -1 |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/composition/runtime_builders` | 4 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/composition/bootstrap/runtime` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/composition/factories/pipeline` | 1 | `composition_runtime_wiring_pattern` | 1.00 | yes |
| `src/bioetl/application/core` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/application/services/control_plane` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/composition/runtime_builders`
- duplicate_clusters: 4
- dominant_actionability_category: `composition_runtime_wiring_pattern`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
