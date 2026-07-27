# Duplication Baseline Report

- mode: fail-fast
- targets: 5
- total_duplicate_clusters: 4
- max_duplicate_clusters: 10
- previous_snapshot_date: 2026-07-22
- total_duplicate_cluster_delta_vs_previous: -9

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 4 |
| `src/bioetl/composition/bootstrap/runtime` | 0 |
| `src/bioetl/composition/factories/pipeline` | 0 |
| `src/bioetl/application/services/control_plane` | 0 |
| `src/bioetl/composition/runtime_builders` | 0 |

## src/bioetl/application/core

- duplicate clusters: 4
- raw duplicate clusters: 8
- excluded duplicate clusters: 4

| Actionability category | Duplicate clusters |
| --- | ---: |
| `export_facade_or_package_barrel` | 4 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.core._fetch_forwarding` <-> `bioetl.application.core.filtered_data_source_mixins` | 1 |
| `bioetl.application.core._fetch_forwarding` <-> `bioetl.application.core.target_data_source_mixins` | 1 |
| `bioetl.application.core.filtered_data_source_mixins` <-> `bioetl.application.core.target_data_source_mixins` | 1 |
| `bioetl.application.core.pre_silver_finalization_flow` <-> `bioetl.application.core.pre_silver_staging_flow` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core._fetch_forwarding`[47:54], `bioetl.application.core.target_data_source_mixins`[77:86] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.filtered_data_source_mixins`[132:138], `bioetl.application.core.target_data_source_mixins`[76:82] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core._fetch_forwarding`[47:52], `bioetl.application.core.filtered_data_source_mixins`[133:138] |
| `src\bioetl\application\core\wiring\__init__.py:1` | `bioetl.application.core.pre_silver_finalization_flow`[32:38], `bioetl.application.core.pre_silver_staging_flow`[43:49] |

## src/bioetl/composition/bootstrap/runtime

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/factories/pipeline

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/application/services/control_plane

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/runtime_builders

- duplicate clusters: 0
- no `R0801` findings

## Trend vs Previous Snapshot

- previous snapshot: `2026-07-22`
- total duplicate cluster delta: -9

| Target | Current | Previous | Delta |
| --- | ---: | ---: | ---: |
| `src/bioetl/application/core` | 4 | 0 | +4 |
| `src/bioetl/composition/bootstrap/runtime` | 0 | 1 | -1 |
| `src/bioetl/composition/factories/pipeline` | 0 | 1 | -1 |
| `src/bioetl/application/services/control_plane` | 0 | 0 | +0 |
| `src/bioetl/composition/runtime_builders` | 0 | 5 | -5 |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/core` | 4 | `export_facade_or_package_barrel` | 1.00 | yes |
| `src/bioetl/application/services/control_plane` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/bootstrap/runtime` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/factories/pipeline` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/runtime_builders` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/application/core`
- duplicate_clusters: 4
- dominant_actionability_category: `export_facade_or_package_barrel`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
