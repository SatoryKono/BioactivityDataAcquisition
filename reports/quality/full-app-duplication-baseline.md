# Duplication Baseline Report

- mode: report-only
- targets: 4
- total_duplicate_clusters: 0
- total_raw_duplicate_clusters: 38
- excluded_duplicate_clusters: 38
- normalized_view: enabled
- exclude_actionability_categories: `export_facade_or_package_barrel`

> Interpretation note: this is a visibility baseline. `R0801` can over-report
> around facades, export barrels, and compatibility shims, so use it as
> prioritization input rather than immediate blocking debt.

| Target | Duplicate clusters |
| --- | ---: |
| `src/bioetl/infrastructure/adapters` | 0 |
| `src/bioetl/application/pipelines` | 0 |
| `src/bioetl/composition/bootstrap` | 0 |
| `src/bioetl/interfaces/cli` | 0 |

## src/bioetl/infrastructure/adapters

- duplicate clusters: 0
- raw duplicate clusters: 38
- excluded duplicate clusters: 38
- no `R0801` findings

## src/bioetl/application/pipelines

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/composition/bootstrap

- duplicate clusters: 0
- no `R0801` findings

## src/bioetl/interfaces/cli

- duplicate clusters: 0

| Actionability category | Duplicate clusters |
| --- | ---: |
| `cli_command_contract_shell` | 0 |
- no `R0801` findings

## Reduction Leverage Ranking

| Target | Duplicate clusters | Dominant actionability | Low-risk share | Recommended first wave |
| --- | ---: | --- | ---: | --- |
| `src/bioetl/application/pipelines` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/composition/bootstrap` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/infrastructure/adapters` | 0 | `n/a` | 0.00 | no |
| `src/bioetl/interfaces/cli` | 0 | `cli_command_contract_shell` | 0.00 | no |

## First Wave Selection

- target: `src/bioetl/application/pipelines`
- duplicate_clusters: 0
- dominant_actionability_category: `None`
- selection_rule: prefer low-risk actionability families with bounded cluster counts, then maximize duplicate reduction leverage
