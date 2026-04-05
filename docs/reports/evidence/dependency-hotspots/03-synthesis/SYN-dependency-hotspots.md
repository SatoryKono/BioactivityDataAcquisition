# Synthesis: dependency-hotspots

## Executive Summary

- The current architecture is structurally disciplined at the layer-policy level: the generated dependency map still reports `0` layer-policy violations on the refreshed baseline, so the main problem is not forbidden imports but concentration inside allowed seams. (EV-dependency-hotspots-module-map-zero-layer-violations)
- Cross-layer pressure is concentrated around a relatively small set of allowed seams, especially `application.composite -> domain.composite`, `composition.factories -> application.core`, `composition.bootstrap -> application.composite`, and `interfaces.cli -> application.services`. (EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli)
- The hotspot inventory is broad by size and narrower by LOC: the current tree still has a meaningfully wider `>10 KB` tail than `>350 LOC` tail, so LOC-only triage would undercount dense modules. (EV-dependency-hotspots-95-files-exceed-10kb, EV-dependency-hotspots-17-files-exceed-350-loc)
- The overlap tail has shifted over time and should now be read as a moving concentration signal rather than a fixed package ranking snapshot. (EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail)
- Size-only hotspots matter materially: the single largest file, `silver_publications.py`, is `17131` bytes while still below the LOC cutoff, which means LOC-only programs would miss some of the densest maintenance surfaces. (EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail)

## Key Insights

### Insight 1: Import-discipline and maintainability pressure are separate concerns in the current codebase

- Observation: The module dependency map is clean at the policy level, but it still shows several high-volume allowed seams and concentrated cross-layer pressure. (EV-dependency-hotspots-module-map-zero-layer-violations, EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli)
- Implication: The next refactoring wave should target structural concentration and navigation cost, not just illegal imports. A green layer-policy signal does not mean the graph is easy to evolve.
- Confidence: 0.93
- Evidence:
  - EV-dependency-hotspots-module-map-zero-layer-violations
  - EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli

### Insight 2: The hotspot problem is a wide size tail, not only a small set of giant LOC offenders

- Observation: the `>10 KB` tail remains materially broader than the `>350 LOC` tail on the current baseline. (EV-dependency-hotspots-95-files-exceed-10kb, EV-dependency-hotspots-17-files-exceed-350-loc)
- Implication: If backlog prioritization looks only at LOC, it will undercount the actual maintainability surface. The project has a broad layer of dense modules that are large enough to be difficult even when they stay under coarse line-count caps.
- Confidence: 0.93
- Evidence:
  - EV-dependency-hotspots-95-files-exceed-10kb
  - EV-dependency-hotspots-17-files-exceed-350-loc

### Insight 3: The densest hotspot tail should be treated as a moving maintenance signal, not a permanent package verdict

- Observation: earlier scans concentrated the overlap tail in infrastructure adapters, while the refreshed summary layer already shows a more split picture across CLI, storage, schemas, config, quality, and application seams. (EV-dependency-hotspots-17-files-exceed-350-loc, EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail)
- Implication: prioritization should use current summary-layer interpretation plus fresh metrics, not historical package rankings from one scan.
- Confidence: 0.92
- Evidence:
  - EV-dependency-hotspots-17-files-exceed-350-loc
  - EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail

### Insight 4: Interfaces and selected application seams are still part of the hotspot core, not just spillover noise

- Observation: the hotspot core still includes `interfaces/cli` and selected application/service seams, not just infrastructure-heavy modules. (EV-dependency-hotspots-17-files-exceed-350-loc, EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli)
- Implication: A hotspot program limited to infrastructure would leave at least one meaningful pressure seam untouched: the CLI/service boundary and selected application pipeline helpers still need explicit treatment.
- Confidence: 0.89
- Evidence:
  - EV-dependency-hotspots-17-files-exceed-350-loc
  - EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli

### Insight 5: Size and LOC are complementary heuristics, not substitutes

- Observation: The entire `>350 LOC` set is contained inside the `>10 KB` set, but the reverse is not true; the largest file by bytes remains below the LOC cutoff. (EV-dependency-hotspots-loc-tail-is-contained-in-size-tail, EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail)
- Implication: The overlap set is a useful “highest-density” shortlist, while the size-only set still identifies dense schemas, config modules, and composition modules that deserve separate review.
- Confidence: 0.90
- Evidence:
  - EV-dependency-hotspots-loc-tail-is-contained-in-size-tail
  - EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail

## Contradictions and Resolutions

### Contradiction 1: Zero layer violations vs strong dependency pressure

- Evidence:
  - EV-dependency-hotspots-module-map-zero-layer-violations
  - EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli
- Tension: The dependency map says the architecture is clean, but the same map also shows heavy cross-layer traffic concentrated in a few seams.
- Resolution: Resolved conceptually. These claims describe different dimensions: policy compliance versus structural pressure.
- Recommendation: Keep layer-policy enforcement as a safety floor, but treat cross-layer edge concentration as a separate optimization target.

### Contradiction 2: Project-native file budgets are layer-specific, while the hotspot scan uses one cross-cutting `>350 LOC` threshold

- Evidence:
  - EV-dependency-hotspots-17-files-exceed-350-loc
  - EV-dependency-hotspots-module-map-zero-layer-violations
- Tension: Some files above `350 LOC` may still be within current layer-specific architecture budgets, so the hotspot inventory is not identical to the set of test violations.
- Resolution: Partially resolved. The scan is still valuable, but it should be interpreted as a comparative hotspot heuristic, not as a restatement of architecture-test failures.
- Recommendation: Keep the cross-cutting hotspot threshold for prioritization, but do not confuse it with the canonical enforcement limits.

### Contradiction 3: The largest file is not in the LOC-hotspot set

- Evidence:
  - EV-dependency-hotspots-largest-size-files-extend-beyond-loc-tail
  - EV-dependency-hotspots-loc-tail-is-contained-in-size-tail
- Tension: A file can be the largest by bytes while remaining outside the LOC tail, which seems to contradict the idea that the LOC tail captures the worst files.
- Resolution: Resolved. The LOC tail captures the densest large files, while the size inventory captures a broader class of dense or packed modules.
- Recommendation: Use both cuts together: overlap for first-priority files, size-only for the second wave.

## Gaps and Uncertainties

- This synthesis does not yet correlate hotspot files with churn, defect history, ownership, or architectural exemptions.
- The dependency map is package- and module-group oriented; it does not yet tell us which individual hotspot files contribute the most import fan-in or fan-out.
- The current evidence does not distinguish between “dense but cohesive” large files and “dense because responsibilities are mixed” large files.

## Recommended Decisions

- **DEC-HOTSPOT-001:** Choose the first refactoring wave boundary.

  - Options:
    - Start with the overlap set (`>10 KB` and `>350 LOC`) as the highest-density shortlist.
    - Start with dependency-pressure seams (`composite`, `composition`, `cli`) even when the files are not all in the overlap set.

- **DEC-HOTSPOT-002:** Decide whether size-only hotspots are first-class backlog items.

  - Options:
    - Treat `>10 KB` files below `350 LOC` as phase-two hotspots.
    - Ignore size-only hotspots and focus only on LOC-heavy modules.

- **DEC-HOTSPOT-003:** Decide whether infrastructure adapters should be the first package decomposition target.

  - Options:
    - Prioritize `src/bioetl/infrastructure/adapters` first.
    - Prioritize CLI/application pressure seams first because of user-facing orchestration impact.

- **DEC-HOTSPOT-004:** Define how dependency pressure and file-size pressure should be merged into one prioritization model.

  - Options:
    - One combined score using dependency pressure plus hotspot thresholds.
    - Two parallel tracks: graph pressure first, file-size debt second.

## Decision Readiness

- Evidence analyzed: 7 objects
- Key insights: 5
- Contradictions: 3
  - Resolved: 2
  - Partially resolved: 1
  - Pending: 0

## Top Insights

1. The project’s main structural issue is concentrated pressure inside allowed seams, not broken layer rules. (EV-dependency-hotspots-module-map-zero-layer-violations, EV-dependency-hotspots-cross-layer-pressure-centers-on-composite-factories-cli)
1. The hotspot inventory is materially broader by size than by LOC, so LOC-only triage would miss a large share of dense modules. (EV-dependency-hotspots-95-files-exceed-10kb, EV-dependency-hotspots-17-files-exceed-350-loc)
1. Hotspot prioritization should follow fresh summary-layer interpretation and current metrics rather than one historical package ranking snapshot. (EV-dependency-hotspots-infrastructure-adapters-dominates-overlap-tail)
