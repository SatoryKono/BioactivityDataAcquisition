# Wave 3 ChEMBL Fetch Paging Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3J-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, and
`pubchem/fetch_strategies.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded ChEMBL adapter
  helpers in the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `chembl/fetch_paging_mixin.py` in the
  top remaining provider-bounded hotspot group at `342` LOC, while larger
  shared seams such as `common/base_title_fallback.py` and
  `cached_bronze_data_source.py` have materially broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `chembl/fetch_paging_mixin.py` — `342` LOC
- `semanticscholar/fetch_adapter_mixin.py` — `317`
- `crossref/client.py` — `317`
- `pubchem/client.py` — `306`

`chembl/fetch_paging_mixin.py` was the safest next bounded cluster because:

1. it stays inside one provider family rather than a shared utility seam;
2. the live `src` caller contract is narrow and explicit through
   [`fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py);
3. the file already had a visible internal seam between page-fetch orchestration
   and filtered-pagination plus dedup helpers;
4. its behavior is already anchored by dedicated ChEMBL adapter tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py)
- [`src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py)
- [`src/bioetl/infrastructure/adapters/chembl/deduplication.py`](../../src/bioetl/infrastructure/adapters/chembl/deduplication.py)
- new internal ChEMBL modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client.py)
- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded ChEMBL family shape before code
movement:

- direct `src/` importer:
  [`fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py)
  mixes `ChemblFetchPagingMixin` into `ChemblFetchAdapterMixin`;
- the current paging mixin collaborates only with already local ChEMBL helpers
  and adapter host methods;
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/chembl/test_chembl_client.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client.py)
  - [`tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `CHEMBL_ADAPTER_ERRORS`
- `ChemblFetchPagingMixin`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of ChEMBL paging flow.

Preferred split direction:

- keep `fetch_paging_mixin.py` as the temporary import-stable facade;
- move filtered-pagination and dedup helpers into a private internal helper
  module;
- leave generic `_fetch_page()` and `_page_iterator()` flow in the facade for
  the first move;
- keep the injected `ChemblFetchPagingMixin` contract unchanged for
  `ChemblFetchAdapterMixin`.

Reasonable internal target for the first slice:

- `_fetch_paging_filtered.py`

## Immediate Slice

Slice `3J-1`: cluster ledger and ChEMBL fetch-paging preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `ChemblFetchPagingMixin`
- confirm that `fetch_adapter_mixin.py` is the live `src` caller contract
- freeze first write scope around `fetch_paging_mixin.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the ChEMBL adapter family;
- the file already had a visible seam between page-fetch flow and
  filtered-pagination/dedup helpers;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/chembl` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3J-2`: filtered-pagination split with compatibility facade.

Status: `completed`

Implemented write scope for `3J-2`:

- keep
  [`fetch_paging_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py)
  as the temporary import-stable facade
- move filtered-pagination and dedup helpers into
  [`_fetch_paging_filtered.py`](../../src/bioetl/infrastructure/adapters/chembl/_fetch_paging_filtered.py)
- preserve the public collaborator symbols `CHEMBL_ADAPTER_ERRORS` and
  `ChemblFetchPagingMixin`
- keep changes inside the bounded ChEMBL adapter family without reopening
  `ChemblFetchAdapterMixin` runtime wiring

Implementation result:

- `fetch_paging_mixin.py` now acts as a thinner import-stable facade;
- filtered-pagination and dedup flow now lives in `_fetch_paging_filtered.py`;
- generic page-fetch and page-iterator flow remains in the facade for the first
  move;
- the runtime contract for `ChemblFetchAdapterMixin` remains unchanged;
- `fetch_paging_mixin.py` was reduced from `342` to `133` LOC.

Next closeout step:

- add a small ratchet so
  [`fetch_paging_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py)
  stays a bounded facade and does not absorb filtered-pagination helpers again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/chembl/test_chembl_client.py tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/chembl`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the PubChem
   split;
2. `fetch_paging_mixin.py` is reduced to one bounded ChEMBL family split
   target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one ChEMBL filtered-pagination
   split rather than a broader ChEMBL adapter rewrite.
