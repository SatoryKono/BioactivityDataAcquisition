# Wave 3 Health Check Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3C-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py` and `http/client_retry_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/health_check_mixin.py`](../../src/bioetl/infrastructure/adapters/health_check_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog keeps `health_check_mixin.py` in the first
  infrastructure-adapter concentration wave
- the current post-`crossref` and post-`http-retry` local size snapshot keeps
  it as the next strongest remaining adapter hotspot at `404` LOC

## Why This Cluster Next

Current size snapshot inside `src/bioetl/infrastructure/adapters` now shows:

- `health_check_mixin.py` — `404` LOC
- `http/health_monitor.py` — `367`
- `error_handling.py` — `367`
- `chembl/fetch_resilience_mixin.py` — `367`
- `openalex/filter_fetch_adapter_mixin.py` — `360`

`health_check_mixin.py` is the strongest next cluster because:

1. it is now the largest remaining adapter hotspot after the previous two
   bounded splits;
2. it already has a visible internal seam between observability helpers and
   provider-facing template-method logic;
3. it is shared by both HTTP and sync adapter bases, so narrowing it reduces
   pressure in a central adapter family without touching provider-specific
   behavior directly;
4. it comes with stable architecture and behavior anchors in both src and tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/health_check_mixin.py`](../../src/bioetl/infrastructure/adapters/health_check_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/base.py`](../../src/bioetl/infrastructure/adapters/base.py)
- [`src/bioetl/infrastructure/adapters/sync_base.py`](../../src/bioetl/infrastructure/adapters/sync_base.py)
- [`src/bioetl/infrastructure/adapters/http/health.py`](../../src/bioetl/infrastructure/adapters/http/health.py)
- other new internal modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/test_http_base.py`](../../tests/unit/infrastructure/adapters/test_http_base.py)
- [`tests/unit/infrastructure/adapters/test_sync_base.py`](../../tests/unit/infrastructure/adapters/test_sync_base.py)
- [`tests/architecture/test_adapter_contracts.py`](../../tests/architecture/test_adapter_contracts.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded shared-seam shape before code
movement:

- direct `src/` importers:
  - [`base.py`](../../src/bioetl/infrastructure/adapters/base.py) imports
    `HealthCheckProviderMixin` into `BaseHttpAdapter`
  - [`sync_base.py`](../../src/bioetl/infrastructure/adapters/sync_base.py)
    imports `HealthCheckProviderMixin` into `BaseSyncAdapter`
- visible architecture anchor:
  [`tests/architecture/test_adapter_contracts.py`](../../tests/architecture/test_adapter_contracts.py)
  already treats `health_check_mixin.py` as a sanctioned mixin seam
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/test_http_base.py`](../../tests/unit/infrastructure/adapters/test_http_base.py)
  - [`tests/unit/infrastructure/adapters/test_sync_base.py`](../../tests/unit/infrastructure/adapters/test_sync_base.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `HealthCheckMixin`
- `HealthCheckProviderMixin`
- `HealthCheckContext`
- `HEALTH_CHECK_ERRORS`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the health-check flow.

Preferred split direction:

- keep `health_check_mixin.py` as the temporary import-stable facade
- separate small observability/context helpers from the provider-facing
  template-method implementation
- keep `BaseHttpAdapter` and `BaseSyncAdapter` inheritance shape unchanged
  during the first move

Reasonable internal targets for the first slice:

- `_health_check_observability.py`
- `_health_check_probe_flow.py`

The exact file map may differ, but the first slice must stay inside the bounded
health family and preserve current imports from
`bioetl.infrastructure.adapters.health_check_mixin`.

## Immediate Slice

Slice `3C-1`: cluster ledger and health-flow split preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `HealthCheckProviderMixin`
- confirm that `base.py` and `sync_base.py` are the live `src/` caller
  contracts
- freeze first write scope around `health_check_mixin.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to two adapter-base modules
- tests already anchor both HTTP and sync behavior paths
- the first refactor can stay inside the shared health family without reopening
  provider-specific adapter topology

Next code slice:

Slice `3C-2`: health-flow split with compatibility facade.

Planned write scope for `3C-2`:

- keep
  [`health_check_mixin.py`](../../src/bioetl/infrastructure/adapters/health_check_mixin.py)
  as the temporary import-stable facade
- add one or more small internal modules for observability or probe-flow logic
- avoid changes to `base.py` or `sync_base.py` unless typing or import wiring
  requires a minimal adjustment
- avoid touching unrelated health-monitoring modules in the same slice

Implementation result for `3C-2`:

- `health_check_mixin.py` remains the import-stable facade used by
  `BaseHttpAdapter` and `BaseSyncAdapter`
- health-check observability helpers moved to
  `src/bioetl/infrastructure/adapters/_health_check_observability.py`
- pure health-policy helpers moved to
  `src/bioetl/infrastructure/adapters/_health_check_policy.py`
- live mixin classes stayed in `health_check_mixin.py`, preserving current
  inheritance and caller contracts
- dependency-map artifacts were regenerated after the new internal modules were
  added, so architecture drift is already reconciled with the current code

Next step after `3C-2`:

- either add a dedicated ratchet to keep `health_check_mixin.py` as a narrowed
  facade/orchestration shell,
- or move to the next bounded adapter hotspot if this shared health cluster is
  considered sufficiently stable without an extra guard

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/test_http_base.py tests/unit/infrastructure/adapters/test_sync_base.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_adapter_contracts.py tests/architecture/test_code_metrics.py tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the retry split;
2. `health_check_mixin.py` is narrowed to one bounded family and split shape;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one health-flow split rather than
   a broad adapter-base rewrite.

Current state:

- all four cluster-start conditions are now satisfied
