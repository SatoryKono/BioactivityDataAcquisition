# Wave 3 HTTP Client Retry Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3B-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py` split inside `Wave 3: Adapter and infrastructure hotspot
reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/http/client_retry_mixin.py`](../../src/bioetl/infrastructure/adapters/http/client_retry_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog keeps `http/client_retry_mixin.py` in the
  first infrastructure-adapter concentration wave
- the current post-`crossref` local size snapshot makes it the largest
  remaining adapter hotspot at `431` LOC

## Why This Cluster Next

Current size snapshot inside `src/bioetl/infrastructure/adapters` now shows:

- `http/client_retry_mixin.py` — `431` LOC
- `health_check_mixin.py` — `404`
- `http/health_monitor.py` — `367`
- `error_handling.py` — `367`
- `chembl/fetch_resilience_mixin.py` — `367`

`client_retry_mixin.py` is the strongest next cluster because:

1. it is now the largest remaining adapter hotspot in the live codebase;
2. it belongs to a bounded `http/` family with existing helper seams;
3. its main responsibilities are dense but structurally separable
   (retry-state, attempt loop, retryability decision, budget/logging);
4. it already has a focused unit-test anchor.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/http/client_retry_mixin.py`](../../src/bioetl/infrastructure/adapters/http/client_retry_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/http/client.py`](../../src/bioetl/infrastructure/adapters/http/client.py)
- [`src/bioetl/infrastructure/adapters/http/client_retry_observability.py`](../../src/bioetl/infrastructure/adapters/http/client_retry_observability.py)
- other new internal `http/_client_retry_*` modules created strictly for the
  split

Target test net:

- [`tests/unit/infrastructure/adapters/test_client_retry_mixin.py`](../../tests/unit/infrastructure/adapters/test_client_retry_mixin.py)
- [`tests/unit/infrastructure/adapters/http/test_retry_config.py`](../../tests/unit/infrastructure/adapters/http/test_retry_config.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a narrow caller surface before code movement:

- direct `src/` importer:
  [`src/bioetl/infrastructure/adapters/http/client.py`](../../src/bioetl/infrastructure/adapters/http/client.py)
  imports `HTTPClientRetryMixin` into `UnifiedHTTPClient`
- direct unit-test importer:
  [`tests/unit/infrastructure/adapters/test_client_retry_mixin.py`](../../tests/unit/infrastructure/adapters/test_client_retry_mixin.py)
  imports `HTTPClientRetryMixin` for concrete behavior checks
- existing adjacent helper seam:
  [`client_retry_observability.py`](../../src/bioetl/infrastructure/adapters/http/client_retry_observability.py)
  already owns span/error finalization logic, which lowers the blast radius for
  further retry-flow thinning

Public collaborator symbol that must remain stable through the first internal
split:

- `HTTPClientRetryMixin`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the retry flow.

Preferred split direction:

- keep `client_retry_mixin.py` as the temporary import-stable facade
- extract internal retry state and/or attempt-result helpers into small internal
  modules
- extract attempt-loop or retry-decision branches only where the boundary is
  already visible in the existing code
- keep `UnifiedHTTPClient` inheritance shape unchanged during the first move

Reasonable internal targets for the first slice:

- `_client_retry_state.py`
- `_client_retry_attempts.py`
- `_client_retry_policy.py`

The exact file map may differ, but the first slice must stay inside the bounded
`http/` family and preserve the current `HTTPClientRetryMixin` import surface.

## Immediate Slice

Slice `3B-1`: cluster ledger and retry-flow split preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `HTTPClientRetryMixin`
- confirm that `client.py` is the only live `src/` caller contract
- freeze first write scope around `client_retry_mixin.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- `UnifiedHTTPClient` is the only live `src/` importer at the current snapshot
- tests already give a direct behavior net for the mixin itself
- the first refactor can stay within `src/bioetl/infrastructure/adapters/http`
  without reopening broader adapter topology

Next code slice:

Slice `3B-2`: retry-flow split with compatibility facade.

Planned write scope for `3B-2`:

- keep
  [`client_retry_mixin.py`](../../src/bioetl/infrastructure/adapters/http/client_retry_mixin.py)
  as the temporary import-stable facade
- add one or more small internal modules for retry-state or attempt orchestration
- avoid changes to `client.py` unless typing or import wiring requires a minimal
  adjustment
- avoid touching unrelated `http/` helpers in the same slice

Implementation result for `3B-2`:

- `client_retry_mixin.py` remains the import-stable facade used by
  `UnifiedHTTPClient`
- retry-state models moved to
  `src/bioetl/infrastructure/adapters/http/_client_retry_models.py`
- pure retry policy and metrics helpers moved to
  `src/bioetl/infrastructure/adapters/http/_client_retry_policy.py`
- live retry orchestration methods stayed in the mixin, preserving current
  behavior and inheritance shape
- dependency-map artifacts were regenerated after the new internal modules were
  added, so architecture drift is already reconciled with the current code

Next step after `3B-2`:

- either add a dedicated ratchet to keep `client_retry_mixin.py` as a narrowed
  facade/orchestration shell,
- or move to the next bounded adapter hotspot if this cluster is considered
  sufficiently stable without an extra guard

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/test_client_retry_mixin.py tests/unit/infrastructure/adapters/http/test_retry_config.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/http`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after `crossref`;
2. `client_retry_mixin.py` is narrowed to one bounded family and split shape;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one retry-flow split rather than
   a broad `http/` rewrite.

Current state:

- all four cluster-start conditions are now satisfied
