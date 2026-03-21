# Wave 3 Error Handling Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3F-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`,
`health_check_mixin.py`, `chembl/fetch_resilience_mixin.py`, and
`openalex/filter_fetch_adapter_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/error_handling.py`](../../src/bioetl/infrastructure/adapters/error_handling.py).

This selection is evidence-backed from two directions:

- the local hotspot snapshot kept `error_handling.py` in the strongest
  remaining adapter group at `367` LOC;
- unlike provider-bounded clusters, this file is a shared adapter helper seam,
  so reducing it lowers pressure across composition defaults and adapter
  families at once.

## Why This Cluster Next

Current remaining hotspot comparison after the OpenAlex split showed:

- `error_handling.py` — `367` LOC
- `http/health_monitor.py` — `367`

`error_handling.py` is a reasonable next bounded cluster because:

1. it still lives inside adapter infrastructure rather than composition or
   interfaces;
2. its public surface is compact and stable: `AdapterErrorContext`,
   `ErrorCategory`, and `ErrorService`;
3. the main visible internal seam is already explicit in code: structured
   context building and telemetry emission versus the `ErrorService` facade;
4. it comes with a strong dedicated unit net and DI architecture guardrails.

`http/health_monitor.py` remains an important follow-up hotspot, but
`error_handling.py` is the better next target because its first split can
remove size/complexity pressure without reopening interface or HTTP monitoring
topology.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/error_handling.py`](../../src/bioetl/infrastructure/adapters/error_handling.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/common/adapter_defaults.py`](../../src/bioetl/infrastructure/adapters/common/adapter_defaults.py)
- [`src/bioetl/composition/factories/datasource/adapter_helpers.py`](../../src/bioetl/composition/factories/datasource/adapter_helpers.py)
- other new internal adapter modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/test_error_handling.py`](../../tests/unit/infrastructure/adapters/test_error_handling.py)
- [`tests/unit/infrastructure/test_adapters.py`](../../tests/unit/infrastructure/test_adapters.py)
- [`tests/architecture/test_di_infrastructure_adapters.py`](../../tests/architecture/test_di_infrastructure_adapters.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded shared-helper shape before code
movement:

- direct `src/` shared callers include:
  - [`common/adapter_defaults.py`](../../src/bioetl/infrastructure/adapters/common/adapter_defaults.py)
  - [`composition/factories/datasource/adapter_helpers.py`](../../src/bioetl/composition/factories/datasource/adapter_helpers.py)
- architecture already treats this area as a sanctioned helper seam through
  [`tests/architecture/test_di_infrastructure_adapters.py`](../../tests/architecture/test_di_infrastructure_adapters.py)
- direct behavior anchor is the dedicated suite
  [`tests/unit/infrastructure/adapters/test_error_handling.py`](../../tests/unit/infrastructure/adapters/test_error_handling.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `AdapterErrorContext`
- `ErrorCategory`
- `ErrorService`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the shared adapter error flow.

Preferred split direction:

- keep `error_handling.py` as the import-stable facade used by composition and
  adapter callers;
- separate structured context and telemetry helpers from the `ErrorService`
  facade;
- preserve the `ErrorService` constructor and public methods unchanged during
  the first move.

Reasonable internal target for the first slice:

- `_error_handling_support.py`

The exact file map may evolve later, but the first slice must preserve current
imports from `bioetl.infrastructure.adapters.error_handling`.

## Immediate Slice

Slice `3F-1`: cluster ledger and shared error-flow preflight.

Status: `completed`

Deliverables:

- confirm current shared callers of `ErrorService`
- confirm that `adapter_defaults.py` and composition helper wiring are the live
  caller contracts
- freeze first write scope around `error_handling.py` plus new internal module
  only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the file is shared, but still bounded within adapter/composition helper
  topology
- the first refactor can stay centered on `error_handling.py` without
  rewriting adapter constructors or composition wiring
- the strongest internal seam is the structured context + telemetry helper path

Next code slice:

Slice `3F-2`: structured-context and telemetry split with compatibility facade.

Status: `completed`

Implemented write scope for `3F-2`:

- keep
  [`error_handling.py`](../../src/bioetl/infrastructure/adapters/error_handling.py)
  as the import-stable facade
- move `AdapterErrorContext`, context-building helpers, telemetry emission, and
  utility helpers into
  [`_error_handling_support.py`](../../src/bioetl/infrastructure/adapters/_error_handling_support.py)
- preserve the public symbols `AdapterErrorContext`, `ErrorCategory`, and
  `ErrorService`
- keep call sites in `adapter_defaults.py` and composition helper wiring
  unchanged

Implementation result:

- `error_handling.py` now acts as a thinner shared facade around `ErrorService`
  behavior;
- structured context and telemetry helpers now live in
  `_error_handling_support.py`;
- `error_handling.py` dropped from `367` to `267` LOC while preserving the same
  public surface and caller contracts.

Next closeout step:

- add a small ratchet so
  [`error_handling.py`](../../src/bioetl/infrastructure/adapters/error_handling.py)
  stays a bounded facade and does not absorb context/telemetry helpers again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/test_error_handling.py tests/unit/infrastructure/test_adapters.py tests/architecture/test_di_infrastructure_adapters.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/error_handling.py src/bioetl/infrastructure/adapters/_error_handling_support.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`

## Definition Of Done For Current Slice

This cluster transition is complete when:

1. `error_handling.py` is explicitly selected as the next shared adapter
   hotspot after the OpenAlex split;
2. `error_handling.py` is narrowed without changing the public `ErrorService`
   surface;
3. the verify set is explicit and green for the current split;
4. the next implementation step is reduced to a possible ratchet or to the
   next bounded hotspot rather than a broad shared-helper rewrite.
