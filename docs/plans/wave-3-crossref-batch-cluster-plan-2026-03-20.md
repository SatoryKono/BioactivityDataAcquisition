# Wave 3 CrossRef Batch Cluster Plan

Date: 2026-03-20  
Status: active bounded-cluster plan, preflight completed  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next major cluster from the master refactor program:
`Wave 3: Adapter and infrastructure hotspot reduction`.

The first bounded cluster is the CrossRef batch family centered on
[`src/bioetl/infrastructure/adapters/crossref/batch.py`](../../src/bioetl/infrastructure/adapters/crossref/batch.py).

This selection is evidence-backed from two directions:

- dependency-hotspot backlog identifies `crossref/batch.py` as the largest
  overlap hotspot inside the most concentrated infrastructure adapter package
- complexity-hotspot backlog independently names `crossref/batch.py` as the
  primary first implementation target

## Why This Cluster First

Current size snapshot inside `src/bioetl/infrastructure/adapters` shows:

- `crossref/batch.py` — `445` LOC
- `http/client_retry_mixin.py` — `431`
- `health_check_mixin.py` — `404`
- `http/health_monitor.py` — `367`
- `error_handling.py` — `367`

`crossref/batch.py` is therefore the strongest first cluster because:

1. it is the single largest adapter hotspot in the current local snapshot;
2. it already has an accepted complexity-first split shape;
3. it has a bounded adjacent family in `crossref/` rather than a diffuse
   cross-package blast radius;
4. it comes with clear unit-test anchors.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/crossref/batch.py`](../../src/bioetl/infrastructure/adapters/crossref/batch.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/crossref/client.py`](../../src/bioetl/infrastructure/adapters/crossref/client.py)
- [`src/bioetl/infrastructure/adapters/crossref/fetch_flow.py`](../../src/bioetl/infrastructure/adapters/crossref/fetch_flow.py)
- [`src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py`](../../src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py)

Target test net:

- [`tests/unit/infrastructure/adapters/crossref/test_batch.py`](../../tests/unit/infrastructure/adapters/crossref/test_batch.py)
- [`tests/unit/infrastructure/adapters/crossref/test_crossref_client.py`](../../tests/unit/infrastructure/adapters/crossref/test_crossref_client.py)
- [`tests/unit/infrastructure/adapters/crossref/test_fallback.py`](../../tests/unit/infrastructure/adapters/crossref/test_fallback.py)
- [`tests/unit/infrastructure/adapters/crossref/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/crossref/test_request_metadata.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_no_inline_construction_in_adapters.py`](../../tests/architecture/test_no_inline_construction_in_adapters.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a narrow compatibility surface before any code
movement:

- current direct `src/` imports of `bioetl.infrastructure.adapters.crossref.batch`:
  none at the current snapshot
- direct import anchored in tests:
  [`tests/performance/test_hotspot_budgets.py`](../../tests/performance/test_hotspot_budgets.py)
  imports `DoiBatchProcessor` from `crossref.batch`
- architecture touchpoints:
  [`tests/architecture/test_no_inline_construction_in_adapters.py`](../../tests/architecture/test_no_inline_construction_in_adapters.py)
  names `DoiBatchProcessor` and `SearchPaginator` as adapter collaborators that
  must remain constructor-injected and not inlined

Public collaborator symbols that must remain stable through the first internal
split:

- `DoiBatchProcessor`
- `SearchPaginator`
- `HttpTransport`
- `BaseMetrics`
- `CROSSREF_RUNTIME_ERRORS`
- `CROSSREF_FALLBACK_ERRORS`

## Target Shape

The intended first slice follows the accepted complexity backlog:

- split DOI batch workflow away from search pagination workflow
- keep `batch.py` as a temporary compatibility seam during the first move
- move implementation detail into internal modules such as:
  - `_doi_batch_processor.py`
  - `_search_paginator.py`
- keep public collaborator symbols stable during the first slice

This is not a behavioral rewrite. It is a topology reduction inside one bounded
adapter family.

## Immediate Slice

Slice `3A-1`: cluster ledger and workflow split preflight.

Status: `completed`

Deliverables:

- confirm current direct imports of `crossref.batch`
- confirm which symbols are stable public collaborators
- freeze first write scope around `batch.py` plus new internal modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- direct `src/` importer count is currently zero
- visible external touchpoints are bounded to tests and architecture guards
- the first refactor can therefore stay inside the `crossref/` package with a
  temporary compatibility seam in `batch.py`

Next code slice:

Slice `3A-2`: internal workflow split with compatibility re-export.

Planned write scope for `3A-2`:

- keep [`batch.py`](../../src/bioetl/infrastructure/adapters/crossref/batch.py)
  as the temporary import-stable facade
- add
  `src/bioetl/infrastructure/adapters/crossref/_doi_batch_processor.py`
- add
  `src/bioetl/infrastructure/adapters/crossref/_search_paginator.py`
- avoid broader edits outside `crossref/` unless a test failure proves a real
  caller contract needs adjustment

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/crossref/test_batch.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/crossref/test_crossref_client.py tests/unit/infrastructure/adapters/crossref/test_fallback.py tests/unit/infrastructure/adapters/crossref/test_request_metadata.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py tests/architecture/test_max_loc_per_file.py tests/architecture/test_no_inline_construction_in_adapters.py tests/architecture/test_architecture_dependency_docs_drift.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/crossref`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the master plan has an explicit first bounded adapter cluster;
2. `crossref/batch.py` is chosen with a concrete intended split shape;
3. the verify set is explicit before code movement starts;
4. the next implementation step is narrowed to one safe internal workflow split
   rather than a broad adapter rewrite.
