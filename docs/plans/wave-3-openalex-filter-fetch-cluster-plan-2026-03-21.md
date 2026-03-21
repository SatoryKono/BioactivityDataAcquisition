# Wave 3 OpenAlex Filter Fetch Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3E-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`,
`health_check_mixin.py`, and `chembl/fetch_resilience_mixin.py` splits
inside `Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter mixins in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot keeps
  `openalex/filter_fetch_adapter_mixin.py` in the top remaining adapter hotspot
  group at `360` LOC, while the larger `error_handling.py` and
  `http/health_monitor.py` have materially broader shared blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` shows:

- `error_handling.py` — `367` LOC
- `http/health_monitor.py` — `367`
- `openalex/filter_fetch_adapter_mixin.py` — `360`

`openalex/filter_fetch_adapter_mixin.py` is the safest next bounded cluster
because:

1. it stays inside one provider family rather than a shared cross-provider
   utility seam;
2. the live `src` caller contract is narrow and explicit through
   [`client.py`](../../src/bioetl/infrastructure/adapters/openalex/client.py);
3. the file already exposes visible internal seams: request normalization,
   fetcher resolution, fallback orchestration, and public fetch dispatch;
4. its behavior is already anchored by dedicated OpenAlex adapter tests.

`error_handling.py` and `http/health_monitor.py` remain important backlog
items, but both currently touch more shared composition, bootstrap, interface,
or adapter-base surfaces than this provider-bounded OpenAlex cluster.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/openalex/client.py`](../../src/bioetl/infrastructure/adapters/openalex/client.py)
- [`src/bioetl/infrastructure/adapters/openalex/cursor_flow.py`](../../src/bioetl/infrastructure/adapters/openalex/cursor_flow.py)
- [`src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py`](../../src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py)
- [`src/bioetl/infrastructure/adapters/openalex/query_execution.py`](../../src/bioetl/infrastructure/adapters/openalex/query_execution.py)
- other new internal OpenAlex modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/openalex/test_adapter.py`](../../tests/unit/infrastructure/adapters/openalex/test_adapter.py)
- [`tests/unit/infrastructure/adapters/openalex/test_fallback.py`](../../tests/unit/infrastructure/adapters/openalex/test_fallback.py)
- [`tests/unit/infrastructure/adapters/openalex/test_fallback_orchestrator.py`](../../tests/unit/infrastructure/adapters/openalex/test_fallback_orchestrator.py)
- [`tests/unit/infrastructure/adapters/openalex/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/openalex/test_request_metadata.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded OpenAlex family shape before code
movement:

- direct `src/` importer:
  [`client.py`](../../src/bioetl/infrastructure/adapters/openalex/client.py)
  imports `OpenAlexAdapterFilterFetchMixin` into `OpenAlexAdapter`
- the current mixin collaborates with already decomposed runtime services via:
  - [`cursor_flow.py`](../../src/bioetl/infrastructure/adapters/openalex/cursor_flow.py)
  - [`fallback_orchestrator.py`](../../src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py)
  - [`query_execution.py`](../../src/bioetl/infrastructure/adapters/openalex/query_execution.py)
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/openalex/test_adapter.py`](../../tests/unit/infrastructure/adapters/openalex/test_adapter.py)
  - [`tests/unit/infrastructure/adapters/openalex/test_fallback.py`](../../tests/unit/infrastructure/adapters/openalex/test_fallback.py)
  - [`tests/unit/infrastructure/adapters/openalex/test_fallback_orchestrator.py`](../../tests/unit/infrastructure/adapters/openalex/test_fallback_orchestrator.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `OpenAlexAdapterFilterFetchMixin`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the OpenAlex filter/fallback fetch flow.

Preferred split direction:

- keep `filter_fetch_adapter_mixin.py` as the temporary import-stable facade;
- separate normalized request models and request-building helpers from the
  public mixin shell;
- separate pure dispatch/fallback orchestration helpers from the mixin methods;
- keep `OpenAlexAdapter` inheritance shape unchanged during the first move.

Reasonable internal targets for the first slice:

- `_filter_fetch_requests.py`
- `_filter_fetch_flow.py`

The exact file map may differ, but the first slice must stay inside the bounded
OpenAlex adapter family and preserve current imports from
`bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin`.

## Immediate Slice

Slice `3E-1`: cluster ledger and OpenAlex filter/fallback preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `OpenAlexAdapterFilterFetchMixin`
- confirm that `client.py` is the live `src/` caller contract
- freeze first write scope around `filter_fetch_adapter_mixin.py` plus new
  internal modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the OpenAlex adapter family
- the file already has visible seams for request normalization and fetch flow
  orchestration
- the first refactor can stay inside
  `src/bioetl/infrastructure/adapters/openalex` without reopening shared
  adapter-base or interface topology

Next code slice:

Slice `3E-2`: filter/fallback flow split with compatibility facade.

Status: `completed`

Implemented write scope for `3E-2`:

- keep
  [`filter_fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py)
  as the temporary import-stable facade
- move request dataclasses and request-building helpers into
  [`_filter_fetch_requests.py`](../../src/bioetl/infrastructure/adapters/openalex/_filter_fetch_requests.py)
- move pure fetch dispatch and fallback orchestration helpers into
  [`_filter_fetch_flow.py`](../../src/bioetl/infrastructure/adapters/openalex/_filter_fetch_flow.py)
- preserve the public collaborator symbol `OpenAlexAdapterFilterFetchMixin`
- keep changes inside the bounded OpenAlex adapter family without reopening
  shared adapter-base utilities

Implementation result:

- `filter_fetch_adapter_mixin.py` now acts as a thinner import-stable facade;
- normalized request dataclasses and request-building helpers now live in
  `_filter_fetch_requests.py`;
- pure fetch dispatch, fetcher resolution, and fallback orchestration helpers
  now live in `_filter_fetch_flow.py`;
- the runtime inheritance shape for `OpenAlexAdapter` remains unchanged.

Next closeout step:

- add a small ratchet so
  [`filter_fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py)
  stays a bounded facade and does not absorb request-shape or flow helpers
  again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/openalex/test_adapter.py tests/unit/infrastructure/adapters/openalex/test_fallback.py tests/unit/infrastructure/adapters/openalex/test_fallback_orchestrator.py tests/unit/infrastructure/adapters/openalex/test_request_metadata.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/openalex`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the ChEMBL
   resilience split;
2. `filter_fetch_adapter_mixin.py` is reduced to one bounded OpenAlex family
   split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one OpenAlex filter/fallback
   split rather than a broader shared-adapter rewrite.
