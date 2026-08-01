# Duplication Baseline Report

- mode: fail-fast
- targets: 5
- total_duplicate_clusters: 4
- max_duplicate_clusters: 4

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/application/core` | 0 |
| `src/bioetl/composition/bootstrap/runtime` | 0 |
| `src/bioetl/composition/factories/pipeline` | 0 |
| `src/bioetl/application/services/control_plane` | 4 |
| `src/bioetl/composition/runtime_builders` | 0 |

## src/bioetl/application/core

- duplicate clusters: 0
- raw duplicate clusters: 7
- excluded duplicate clusters: 7
- no `R0801` findings

## src/bioetl/composition/bootstrap/runtime

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/factories/pipeline

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/application/services/control_plane

- duplicate clusters: 4

| Actionability category | Duplicate clusters |
| --- | ---: |
| `behavior_bearing_candidate` | 4 |

| Top recurring module pairs | Duplicate clusters |
| --- | ---: |
| `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core` <-> `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended` | 2 |
| `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection` <-> `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_payload` | 1 |
| `bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories` <-> `bioetl.application.services.control_plane.run_manifest_reproducibility_score_cards` | 1 |

| Cluster path | Compared modules |
| --- | --- |
| `src/bioetl/application/services/control_plane/ledger/core_events.py:1` | `bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories`[39:47], `bioetl.application.services.control_plane.run_manifest_reproducibility_score_cards`[36:44] |
| `src/bioetl/application/services/control_plane/ledger/core_events.py:1` | `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core`[70:79], `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended`[44:53] |
| `src/bioetl/application/services/control_plane/ledger/core_events.py:1` | `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core`[139:147], `bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended`[114:122] |
| `src/bioetl/application/services/control_plane/ledger/core_events.py:1` | `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection`[118:124], `bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_payload`[105:111] |

## src/bioetl/composition/runtime_builders

- duplicate clusters: 0
- no `R0801` findings

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/services/control_plane` | 4 | `behavior_bearing_candidate` | 0.00 | no |
| `src/bioetl/application/core` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/bootstrap/runtime` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/factories/pipeline` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/runtime_builders` | 0 | `n/a` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/application/services/control_plane`
- duplicate_clusters: 4
- dominant_actionability_category: `behavior_bearing_candidate`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
