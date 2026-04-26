# Сбор evidence завершён: dependency-hotspots

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

**Создано объектов evidence:** 7
**Gate Статус:** PASSED

Примечание о rebaseline: hotspot interpretation still holds on the current
tree, while the dependency-map side of the signal was re-confirmed as green
during `RF-011`.

## Сводка evidence

| ID                                                                             | Claim Summary                                                                                                                        | Confidence |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| EV-dependency-hotspots-module-map-zero-layer-violations                        | The dependency map reports 0 layer-policy violations despite a large import graph.                                                   | 0.96       |
| EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli | Cross-layer pressure clusters around composite, composition-factory/bootstrap, and CLI-service seams.                                | 0.90       |
| EV-dependency-hotspots-95-files-exceed-10kb                                    | `src/bioetl` contains 82 files above 10 KB, concentrated in application and infrastructure.                                          | 0.93       |
| EV-dependency-hotspots-17-files-exceed-350-loc                                 | `src/bioetl` contains 10 files above 350 LOC, mostly in infrastructure.                                                              | 0.93       |
| EV-dependency-hotspots-loc-tail-is-contained-in-size-tail                      | All 10 files above 350 LOC are also above 10 KB.                                                                                     | 0.91       |
| EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail          | The overlap tail is now split across CLI commands, storage, and selected application/service seams rather than centered on adapters. | 0.92       |
| EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail               | The largest file is still a size-only tail example: `silver_publications.py` is 17.1 KB but only 341 LOC.                            | 0.89       |

## Ключевые выводы

- The architecture remains import-disciplined, but the dependency map still shows concentrated cross-layer pressure around composite orchestration, composition wiring, and CLI-service seams.
- The broad hotspot inventory is still a size problem first: the current summary baseline remains materially wider by `>10 KB` than by `>350 LOC`, even after the recent cleanup waves.
- The overlap tail is no longer adapter-dominant; it now repeats most clearly in `src/bioetl/interfaces/cli/commands`, with the remaining tail spread across storage, schemas, config, quality, and application pipeline/service seams.
- Size-only hotspots still matter: `silver_publications.py` remains above the byte threshold but below the LOC cutoff.

## Отмеченные противоречия

- There is no formal contradiction between the dependency map and the hotspot counts: the former shows policy discipline, while the latter shows maintainability concentration inside allowed seams.
- The `>350 LOC` heuristic is stricter than some layer-specific architecture budgets, so the hotspot set should be read as risk inventory rather than direct test-failure inventory.

## Оставшиеся пробелы

- This evidence set does not yet connect hotspot files to churn, ownership history, or bug density.
- Package-level hotspot counts are coarse and do not yet identify the most entangled classes/functions inside each file.
- The dependency map highlights pressure centers, but it does not quantify which hotspot files generate the most incoming or outgoing imports individually.
