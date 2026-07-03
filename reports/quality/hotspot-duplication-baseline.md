# Duplication Baseline Report

- mode: report-only
- targets: 5
- total_duplicate_clusters: 0
- previous_snapshot_date: 2026-06-01
- total_duplicate_cluster_delta_vs_previous: +0

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 0 |
| `src/bioetl/composition/bootstrap/runtime` | 0 |
| `src/bioetl/composition/factories/pipeline` | 0 |
| `src/bioetl/application/services/control_plane` | 0 |
| `src/bioetl/composition/runtime_builders` | 0 |

## src/bioetl/application/core

- duplicate clusters: 0
- no `R0801` findings

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

- previous snapshot: `2026-06-01`
- total duplicate cluster delta: +0

| Target | Current | Previous | Delta |
| --- | ---: | ---: | ---: |
| `src/bioetl/application/core` | 0 | n/a | n/a |
| `src/bioetl/application/services/control_plane` | 0 | 0 | +0 |
| `src/bioetl/composition/bootstrap/runtime` | 0 | n/a | n/a |
| `src/bioetl/composition/factories/pipeline` | 0 | n/a | n/a |
| `src/bioetl/composition/runtime_builders` | 0 | 0 | +0 |

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/core` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/application/services/control_plane` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/bootstrap/runtime` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/factories/pipeline` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/runtime_builders` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/application/core`
- duplicate_clusters: 0
- dominant_actionability_category: `None`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
