# Pillars

## dependency-hotspots

- Priority: High
- Scope: Architecture dependency-map facts and source-tree hotspot counts for Python modules under `src/bioetl`, using the requested thresholds `>10 KB` and `>350 LOC`.
- Scope restrictions:
  - In scope: `docs/02-architecture/generated/module-dependency-map.md`, `src/bioetl/**/*.py`, `tests/architecture/test_code_metrics.py`, and evidence snapshots generated from current filesystem metrics.
  - Out of scope: test files, performance hotspot benchmarks, runtime latency profiling, and function-level complexity analysis.

### Research Questions

1. What does the current dependency map say about layer-policy violations and cross-layer pressure?
2. How many source files exceed `10 KB`?
3. How many source files exceed `350 LOC`?
4. How much overlap is there between the `>10 KB` and `>350 LOC` sets?
5. Which layers and packages dominate the hotspot inventory?
6. Which individual files lead the hotspot tail by size and by LOC?
