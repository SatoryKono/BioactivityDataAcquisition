# Evidence Collection Complete: dependency-hotspots

**Evidence Objects Created:** 7  
**Gate Status:** PASSED

## Evidence Summary

| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-dependency-hotspots-module-map-zero-layer-violations | The dependency map reports 0 layer-policy violations despite a large import graph. | 0.96 |
| EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli | Cross-layer pressure clusters around composite, composition-factory/bootstrap, and CLI-service seams. | 0.90 |
| EV-dependency-hotspots-95-files-exceed-10kb | `src/bioetl` contains 95 files above 10 KB, concentrated in infrastructure and application. | 0.93 |
| EV-dependency-hotspots-17-files-exceed-350-loc | `src/bioetl` contains 17 files above 350 LOC, mostly in infrastructure. | 0.93 |
| EV-dependency-hotspots-loc-tail-is-contained-in-size-tail | All 17 files above 350 LOC are also above 10 KB. | 0.91 |
| EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail | `src/bioetl/infrastructure/adapters` holds 7 of the 17 files exceeding both thresholds. | 0.92 |
| EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail | The largest files are not identical to the LOC tail; the biggest file is 17.1 KB but only 341 LOC. | 0.89 |

## Key Findings

- The architecture remains import-disciplined, but the dependency map still shows concentrated cross-layer pressure around composite orchestration, composition wiring, and CLI-service seams.
- The broad hotspot inventory is a size problem first: 95 files exceed 10 KB, while only 17 exceed 350 LOC.
- The narrowest and densest hotspot tail is heavily infrastructure-biased, especially inside `src/bioetl/infrastructure/adapters`.
- Size-only hotspots matter: large schema/config and mixin modules can sit below the LOC cutoff while still contributing to maintenance drag.

## Contradictions Noted

- There is no formal contradiction between the dependency map and the hotspot counts: the former shows policy discipline, while the latter shows maintainability concentration inside allowed seams.
- The `>350 LOC` heuristic is stricter than some layer-specific architecture budgets, so the hotspot set should be read as risk inventory rather than direct test-failure inventory.

## Gaps Remaining

- This evidence set does not yet connect hotspot files to churn, ownership history, or bug density.
- Package-level hotspot counts are coarse and do not yet identify the most entangled classes/functions inside each file.
- The dependency map highlights pressure centers, but it does not quantify which hotspot files generate the most incoming or outgoing imports individually.
