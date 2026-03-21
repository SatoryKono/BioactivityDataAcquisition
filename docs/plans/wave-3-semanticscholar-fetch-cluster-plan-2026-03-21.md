# Wave 3 Semantic Scholar Fetch Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3K-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`, and
`chembl/fetch_paging_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter helpers in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot kept
  `semanticscholar/fetch_adapter_mixin.py` in the top remaining provider-bounded
  hotspot group at `316` LOC, while larger shared seams such as
  `common/base_title_fallback.py` and `cached_bronze_data_source.py` have
  broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `semanticscholar/fetch_adapter_mixin.py` — `316` LOC
- `crossref/client.py` — `316`
- `pubchem/client.py` — `305`
- `pubmed/models.py` — `301`

`semanticscholar/fetch_adapter_mixin.py` was the safest next bounded cluster
because:

1. it stays inside one provider family rather than a shared utility seam;
2. the live `src` caller contract is narrow and explicit through
   [`adapter.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/adapter.py);
3. the file already had a visible internal seam between search/page flow and
   DOI batch plus fallback orchestration;
4. its behavior is already anchored by dedicated Semantic Scholar adapter and
   fallback tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/adapter.py)
- [`src/bioetl/infrastructure/adapters/semanticscholar/batch_request_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/batch_request_mixin.py)
- [`src/bioetl/infrastructure/adapters/semanticscholar/fallback.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fallback.py)
- new internal Semantic Scholar modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py)
- [`tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py)
- [`tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py)
- [`tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded Semantic Scholar family shape before
code movement:

- direct `src/` caller:
  [`adapter.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/adapter.py)
  mixes `SemanticScholarFetchAdapterMixin` into `SemanticScholarAdapter`;
- the current fetch mixin already collaborates with extracted helpers via:
  - [`batch_request_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/batch_request_mixin.py)
  - [`fallback.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fallback.py)
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py)
  - [`tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py)
  - [`tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `SemanticScholarFetchAdapterMixin`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of Semantic Scholar fetch flow.

Preferred split direction:

- keep `fetch_adapter_mixin.py` as the temporary import-stable facade;
- move search/page orchestration into a private internal helper module;
- leave DOI batch filtering and fallback orchestration in the facade for the
  first move;
- keep the injected `SemanticScholarFetchAdapterMixin` contract unchanged for
  `SemanticScholarAdapter`.

Reasonable internal target for the first slice:

- `_search_fetch_flow.py`

## Immediate Slice

Slice `3K-1`: cluster ledger and Semantic Scholar fetch preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `SemanticScholarFetchAdapterMixin`
- confirm that `adapter.py` is the live `src` caller contract
- freeze first write scope around `fetch_adapter_mixin.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the Semantic Scholar adapter family;
- the file already had a visible seam between search/page flow and DOI/fallback
  orchestration;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/semanticscholar` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3K-2`: search-flow split with compatibility facade.

Status: `completed`

Implemented write scope for `3K-2`:

- keep
  [`fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py)
  as the temporary import-stable facade
- move search validation and page orchestration into
  [`_search_fetch_flow.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/_search_fetch_flow.py)
- preserve the public collaborator symbol `SemanticScholarFetchAdapterMixin`
- keep changes inside the bounded Semantic Scholar adapter family without
  reopening `SemanticScholarAdapter` runtime wiring

Implementation result:

- `fetch_adapter_mixin.py` now acts as a thinner import-stable facade;
- search/page flow now lives in `_search_fetch_flow.py`;
- DOI batch and fallback orchestration remain in the facade for the first move;
- the runtime contract for `SemanticScholarAdapter` remains unchanged;
- `fetch_adapter_mixin.py` was reduced from `316` to `229` LOC.

Next closeout step:

- add a small ratchet so
  [`fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py)
  stays a bounded facade and does not absorb search/page flow again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/semanticscholar`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the ChEMBL
   fetch-paging split;
2. `fetch_adapter_mixin.py` is reduced to one bounded Semantic Scholar family
   split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one Semantic Scholar search-flow
   split rather than a broader provider rewrite.
