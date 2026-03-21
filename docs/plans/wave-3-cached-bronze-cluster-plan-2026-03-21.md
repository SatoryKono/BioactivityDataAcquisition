# Wave 3 Cached Bronze Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3Q-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
provider-bounded Wave 3 sequence and marks the transition into broader shared
adapter seams.

The current cluster is centered on
[`src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`](../../src/bioetl/infrastructure/adapters/cached_bronze_data_source.py).

This selection is evidence-backed from two directions:

- the current size snapshot kept `cached_bronze_data_source.py` at `324` LOC,
  making it one of the largest remaining shared seams in
  `src/bioetl/infrastructure/adapters`;
- unlike `common/base_title_fallback.py`, it already had a narrow direct test
  anchor and a bounded composition touchpoint through cached-bronze wiring.

## Why This Cluster Next

Current remaining shared-seam comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `common/base_title_fallback.py` — `324` LOC
- `cached_bronze_data_source.py` — `324`
- `decorators/retry.py` — `296`
- `decorators/circuit_breaker.py` — `296`

`cached_bronze_data_source.py` was the safer next shared cluster because:

1. it has a dedicated unit-test file with broad behavioral coverage;
2. its live callers are explicit through composition wiring and package-root
   re-export only;
3. the file had visible pure-helper seams around date parsing, batch listing,
   empty-cache resolution, and record counting;
4. the first slice could stay inside one facade plus one private helper module.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`](../../src/bioetl/infrastructure/adapters/cached_bronze_data_source.py)

Immediate adjacent files allowed only if needed by the split:

- new internal adapter modules created strictly for the split
- [`src/bioetl/infrastructure/adapters/__init__.py`](../../src/bioetl/infrastructure/adapters/__init__.py) only as export-surface context

Target test net:

- [`tests/unit/infrastructure/adapters/test_cached_bronze_data_source.py`](../../tests/unit/infrastructure/adapters/test_cached_bronze_data_source.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded shared-seam shape before code
movement:

- package-root export surface is narrow: `CachedBronzeDataSource` only;
- the direct behavior anchor is concentrated in one unit-test file;
- composition uses the class through explicit factory wiring, not through a
  dense graph of internal imports.

Visible internal seam before the first split:

- date parsing and list-batch path policy
- unsupported fetch-parameter logging
- empty-cache error path resolution
- batch iteration and record counting

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the cached-bronze facade.

Preferred split direction:

- keep `cached_bronze_data_source.py` as the public import-stable facade;
- move pure list/path/count helpers into a private internal module;
- preserve the async data-source contract and package-root re-export;
- leave public lifecycle and fetch orchestration methods in the facade.

Reasonable internal target for the first slice:

- `_cached_bronze_support.py`

## Immediate Slice

Slice `3Q-1`: cluster ledger and cached-bronze preflight.

Status: `completed`

Deliverables:

- confirm package-root export surface for the cached-bronze adapter
- confirm the pure-helper seam around list/path/count logic
- freeze first write scope around `cached_bronze_data_source.py` plus one
  internal helper only
- keep docs/evidence language aligned with a compatibility-preserving facade

Preflight result:

- the live blast radius is bounded;
- the file already had a helper-friendly split between orchestration and pure
  utility logic;
- the first refactor could stay inside `src/bioetl/infrastructure/adapters`
  without reopening composition or storage topology.

Next code slice:

Slice `3Q-2`: cached-bronze support split with compatibility facade.

Status: `completed`

Implemented write scope for `3Q-2`:

- keep
  [`cached_bronze_data_source.py`](../../src/bioetl/infrastructure/adapters/cached_bronze_data_source.py)
  as the public import-stable facade
- move list/path/count helper logic into
  [`_cached_bronze_support.py`](../../src/bioetl/infrastructure/adapters/_cached_bronze_support.py)
- preserve the public collaborator symbol exported by the package root
- keep changes inside the bounded cached-bronze seam

Implementation result:

- `cached_bronze_data_source.py` now acts as a thinner public facade;
- list/date/path/count helper logic now lives in `_cached_bronze_support.py`;
- async lifecycle and fetch orchestration remain in the facade;
- package-root re-export remains unchanged;
- `cached_bronze_data_source.py` was reduced from `324` to `297` LOC.

Next closeout step:

- add a small ratchet so
  [`cached_bronze_data_source.py`](../../src/bioetl/infrastructure/adapters/cached_bronze_data_source.py)
  stays a bounded facade and does not absorb pure support logic again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/test_cached_bronze_data_source.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/cached_bronze_data_source.py src/bioetl/infrastructure/adapters/_cached_bronze_support.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the first post-provider shared seam is explicitly selected and reduced;
2. `cached_bronze_data_source.py` is reduced to one bounded shared-seam split
   target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to closeout/ratchet work or to the
   next shared seam rather than another unbounded adapter rewrite.
