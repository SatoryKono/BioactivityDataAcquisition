# Wave 3 CrossRef Client Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3L-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`,
`chembl/fetch_paging_mixin.py`, and
`semanticscholar/fetch_adapter_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/crossref/client.py`](../../src/bioetl/infrastructure/adapters/crossref/client.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter facades in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `crossref/client.py` in the top
  remaining provider-bounded hotspot group at `316` LOC, while larger shared
  seams such as `common/base_title_fallback.py` and
  `cached_bronze_data_source.py` have broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `crossref/client.py` — `316` LOC
- `pubchem/client.py` — `305`
- `pubmed/models.py` — `301`
- `crossref/models.py` — `301`

`crossref/client.py` was a good next bounded cluster because:

1. it stays inside one provider family rather than a shared utility seam;
2. the live `src` caller contract is narrow and explicit through the package
   canonical entrypoint;
3. the file was already mostly facade-only, but still mixed provider-specific
   fallback-policy hooks with runtime wiring and observability surface;
4. its behavior is already anchored by dedicated CrossRef adapter and
   compatibility tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/crossref/client.py`](../../src/bioetl/infrastructure/adapters/crossref/client.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py`](../../src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py)
- [`src/bioetl/infrastructure/adapters/crossref/client_fetch_helpers.py`](../../src/bioetl/infrastructure/adapters/crossref/client_fetch_helpers.py)
- [`src/bioetl/infrastructure/adapters/crossref/client_observability_helpers.py`](../../src/bioetl/infrastructure/adapters/crossref/client_observability_helpers.py)
- new internal CrossRef modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/crossref/test_crossref_client.py`](../../tests/unit/infrastructure/adapters/crossref/test_crossref_client.py)
- [`tests/unit/infrastructure/adapters/crossref/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/crossref/test_request_metadata.py)
- [`tests/unit/infrastructure/adapters/crossref/test_compatibility.py`](../../tests/unit/infrastructure/adapters/crossref/test_compatibility.py)
- [`tests/unit/infrastructure/adapters/crossref/test_batch.py`](../../tests/unit/infrastructure/adapters/crossref/test_batch.py)
- [`tests/unit/infrastructure/adapters/crossref/test_fallback.py`](../../tests/unit/infrastructure/adapters/crossref/test_fallback.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded CrossRef family shape before code
movement:

- the current client facade already delegates most behavior to extracted helpers
  and runtime services;
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/crossref/test_crossref_client.py`](../../tests/unit/infrastructure/adapters/crossref/test_crossref_client.py)
  - [`tests/unit/infrastructure/adapters/crossref/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/crossref/test_request_metadata.py)
  - [`tests/unit/infrastructure/adapters/crossref/test_compatibility.py`](../../tests/unit/infrastructure/adapters/crossref/test_compatibility.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `CROSSREF_API_BASE`
- `CROSSREF_HEALTH_ERRORS`
- `CrossRefAdapter`
- `CrossRefFetchFlow`
- `CrossRefQueryBuilder`
- `CrossRefResponseMapper`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
remaining internal topology of the CrossRef client facade.

Preferred split direction:

- keep `client.py` as the import-stable canonical adapter entrypoint;
- move provider-specific fallback-policy hookpoints into a private internal
  mixin;
- leave runtime wiring, fetch delegation, and observability surface in the
  facade for the first move;
- keep the injected `CrossRefAdapter` runtime contract unchanged.

Reasonable internal target for the first slice:

- `_client_fallback_policy.py`

## Immediate Slice

Slice `3L-1`: cluster ledger and CrossRef client preflight.

Status: `completed`

Deliverables:

- confirm that `client.py` is still a live provider-facing entrypoint
- confirm that existing helper extraction already covers fetch and observability
  concerns
- freeze first write scope around `client.py` plus one new internal module only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live blast radius is bounded to the CrossRef adapter family;
- the file was already close to a facade, but still owned provider-specific
  fallback-policy hooks locally;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/crossref` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3L-2`: fallback-policy hook split with compatibility facade.

Status: `completed`

Implemented write scope for `3L-2`:

- keep
  [`client.py`](../../src/bioetl/infrastructure/adapters/crossref/client.py)
  as the canonical import-stable facade
- move provider-specific fallback-policy hookpoints into
  [`_client_fallback_policy.py`](../../src/bioetl/infrastructure/adapters/crossref/_client_fallback_policy.py)
- preserve the public collaborator symbols exported by `client.py`
- keep changes inside the bounded CrossRef adapter family without reopening
  package entrypoint policy

Implementation result:

- `client.py` now acts as a thinner canonical facade;
- fallback-policy hookpoints now live in `_client_fallback_policy.py`;
- runtime wiring, fetch delegation, and observability surface remain in
  `client.py`;
- the runtime contract for `CrossRefAdapter` remains unchanged;
- `client.py` was reduced from `316` to `287` LOC.

Next closeout step:

- add a small ratchet so
  [`client.py`](../../src/bioetl/infrastructure/adapters/crossref/client.py)
  stays a bounded facade and does not absorb provider-specific policy hooks
  again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/crossref/test_crossref_client.py tests/unit/infrastructure/adapters/crossref/test_request_metadata.py tests/unit/infrastructure/adapters/crossref/test_compatibility.py tests/unit/infrastructure/adapters/crossref/test_batch.py tests/unit/infrastructure/adapters/crossref/test_fallback.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/crossref`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the Semantic
   Scholar split;
2. `client.py` is reduced to one bounded CrossRef family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one CrossRef client policy split
   rather than a broader provider rewrite.
