# Duplication Baseline Report

- mode: fail-fast
- targets: 5
- total_duplicate_clusters: 0
- max_duplicate_clusters: 0

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
- raw duplicate clusters: 9
- excluded duplicate clusters: 9
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
