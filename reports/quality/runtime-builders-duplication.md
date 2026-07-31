# Duplication Baseline Report

- mode: fail-fast
- targets: 1
- total_duplicate_clusters: 0
- max_duplicate_clusters: 0

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/composition/runtime_builders` | 0 |

## src/bioetl/composition/runtime_builders

- duplicate clusters: 0
- no `R0801` findings

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/composition/runtime_builders` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/composition/runtime_builders`
- duplicate_clusters: 0
- dominant_actionability_category: `None`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
