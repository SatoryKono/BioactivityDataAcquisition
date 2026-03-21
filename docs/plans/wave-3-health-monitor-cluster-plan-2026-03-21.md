# Wave 3 Health Monitor Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3G-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`,
`health_check_mixin.py`, `chembl/fetch_resilience_mixin.py`,
`openalex/filter_fetch_adapter_mixin.py`, and `error_handling.py` splits
inside `Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/http/health_monitor.py`](../../src/bioetl/infrastructure/adapters/http/health_monitor.py).

This selection is evidence-backed from two directions:

- the local hotspot snapshot kept `http/health_monitor.py` as one of the
  strongest remaining adapter files at `367` LOC;
- unlike provider-bounded clusters, this file is a shared HTTP seam used by
  composition bootstrap and interface-facing monitoring flows.

## Why This Cluster Next

After the `error_handling.py` split, `health_monitor.py` remained the strongest
shared hotspot in the adapter family.

`health_monitor.py` is a good bounded cluster because:

1. it stays within the HTTP adapter/health domain rather than spreading into
   broad interface refactors;
2. its public surface is compact and stable: `HealthAdjustedConfig`,
   `ProviderHealthState`, `ProviderHealthMonitor`, and `ProviderHealthTracker`;
3. the main internal seam is already visible in code: transition logic and
   health-check observability versus the monitor facade;
4. it already has strong behavior anchors in the dedicated health-monitor test
   suite and composition bootstrap tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/http/health_monitor.py`](../../src/bioetl/infrastructure/adapters/http/health_monitor.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/http/health_tracker.py`](../../src/bioetl/infrastructure/adapters/http/health_tracker.py)
- [`src/bioetl/composition/bootstrap/cli/health.py`](../../src/bioetl/composition/bootstrap/cli/health.py)
- other new internal HTTP health modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/http/test_health_monitor.py`](../../tests/unit/infrastructure/adapters/http/test_health_monitor.py)
- [`tests/unit/composition/bootstrap/test_health_bootstrap.py`](../../tests/unit/composition/bootstrap/test_health_bootstrap.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded shared HTTP-health shape before code
movement:

- composition bootstrap uses
  [`bootstrap/cli/health.py`](../../src/bioetl/composition/bootstrap/cli/health.py)
  to construct `ProviderHealthMonitor`
- runtime wrapper stays in
  [`health_tracker.py`](../../src/bioetl/infrastructure/adapters/http/health_tracker.py)
- direct behavior anchor is the dedicated suite
  [`tests/unit/infrastructure/adapters/http/test_health_monitor.py`](../../tests/unit/infrastructure/adapters/http/test_health_monitor.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `HealthAdjustedConfig`
- `ProviderHealthState`
- `ProviderHealthMonitor`
- `ProviderHealthTracker`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the shared HTTP health-monitor flow.

Preferred split direction:

- keep `health_monitor.py` as the import-stable facade used by composition and
  HTTP-facing callers;
- separate state-transition and observability helpers from the monitor facade;
- preserve `ProviderHealthMonitor` methods and `ProviderHealthTracker`
  integration unchanged during the first move.

Reasonable internal target for the first slice:

- `_health_monitor_support.py`

The exact file map may evolve later, but the first slice must preserve current
imports from `bioetl.infrastructure.adapters.http.health_monitor`.

## Immediate Slice

Slice `3G-1`: cluster ledger and health-monitor preflight.

Status: `completed`

Deliverables:

- confirm current shared callers of `ProviderHealthMonitor`
- confirm that `health_tracker.py` and composition bootstrap are the live
  caller contracts
- freeze first write scope around `health_monitor.py` plus one new internal
  module only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the file is shared, but still bounded within HTTP health-monitor topology
- the first refactor can stay centered on `health_monitor.py` without
  reopening interfaces or health-server routing
- the strongest internal seam is transition logic plus health-check
  observability

Next code slice:

Slice `3G-2`: transition and observability split with compatibility facade.

Status: `completed`

Implemented write scope for `3G-2`:

- keep
  [`health_monitor.py`](../../src/bioetl/infrastructure/adapters/http/health_monitor.py)
  as the import-stable facade
- move transition logic and observability helpers into
  [`_health_monitor_support.py`](../../src/bioetl/infrastructure/adapters/http/_health_monitor_support.py)
- preserve the public symbols `HealthAdjustedConfig`,
  `ProviderHealthState`, `ProviderHealthMonitor`, and `ProviderHealthTracker`
- keep `health_tracker.py` and composition bootstrap call sites unchanged

Implementation result:

- `health_monitor.py` now acts as a thinner HTTP-health facade;
- transition logic and health-check observability helpers now live in
  `_health_monitor_support.py`;
- `health_monitor.py` dropped from `367` to `290` LOC while preserving the same
  public surface and caller contracts.

Next closeout step:

- add a small ratchet so
  [`health_monitor.py`](../../src/bioetl/infrastructure/adapters/http/health_monitor.py)
  stays a bounded facade and does not absorb transition/observability helpers
  again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/http/test_health_monitor.py tests/unit/composition/bootstrap/test_health_bootstrap.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/http/health_monitor.py src/bioetl/infrastructure/adapters/http/_health_monitor_support.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`

## Definition Of Done For Current Slice

This cluster transition is complete when:

1. `health_monitor.py` is explicitly selected as the next shared HTTP hotspot
   after the `error_handling.py` split;
2. `health_monitor.py` is narrowed without changing the public monitor/tracker
   surface;
3. the verify set is explicit and green for the current split;
4. the next implementation step is reduced to a possible ratchet or to the
   next bounded hotspot rather than a broad health-server rewrite.
