# Wave 3 PubMed Filter Fetch Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3H-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`,
`health_check_mixin.py`, `chembl/fetch_resilience_mixin.py`,
`openalex/filter_fetch_adapter_mixin.py`, `error_handling.py`, and
`http/health_monitor.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py`](../../src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py).

This selection is evidence-backed from two directions:

- the local hotspot snapshot kept `pubmed/adapter_filter_fetch_mixin.py` in the
  strongest remaining provider-bounded adapter group at `340` LOC;
- unlike the recently completed shared-helper clusters, this file stays inside
  one provider family with a narrow runtime caller surface.

## Why This Cluster Next

`pubmed/adapter_filter_fetch_mixin.py` is a strong next bounded cluster
because:

1. it is provider-bounded through [`pubmed_client.py`](../../src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py);
2. its public surface is small and stable: the mixin remains the only external
   collaborator symbol;
3. the file already exposes visible internal seams: filter dispatch, fallback
   execution, resume-offset handling, and PMID resolution;
4. it has a focused provider test net that already anchors fetch and fallback
   behavior.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py`](../../src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py`](../../src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py)
- other new internal PubMed modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py`](../../tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py`](../../tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_fallback.py`](../../tests/unit/infrastructure/adapters/pubmed/test_fallback.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded PubMed family shape before code
movement:

- direct `src/` caller:
  [`pubmed_client.py`](../../src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py)
  imports `PubMedAdapterFilterFetchMixin`
- the mixin already sits beside decomposed provider helpers:
  [`_fetch.py`](../../src/bioetl/infrastructure/adapters/pubmed/_fetch.py),
  [`_search.py`](../../src/bioetl/infrastructure/adapters/pubmed/_search.py),
  and [`_health.py`](../../src/bioetl/infrastructure/adapters/pubmed/_health.py)
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py`](../../tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py)
  - [`tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py`](../../tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py)
  - [`tests/unit/infrastructure/adapters/pubmed/test_fallback.py`](../../tests/unit/infrastructure/adapters/pubmed/test_fallback.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `PubMedAdapterFilterFetchMixin`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the PubMed filter/fetch orchestration flow.

Preferred split direction:

- keep `adapter_filter_fetch_mixin.py` as the import-stable facade used by
  `PubMedAdapter`;
- separate filter dispatch, fallback, and resume-offset helpers from the mixin
  shell;
- preserve `PubMedAdapter` inheritance and fallback-decorator wiring unchanged
  during the first move.

Reasonable internal target for the first slice:

- `_filter_fetch_support.py`

## Immediate Slice

Slice `3H-1`: cluster ledger and PubMed filter/fetch preflight.

Status: `completed`

Deliverables:

- confirm current direct caller of `PubMedAdapterFilterFetchMixin`
- confirm that `pubmed_client.py` is the live runtime contract
- freeze first write scope around `adapter_filter_fetch_mixin.py` plus one new
  internal module only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the PubMed adapter family
- the file already has clear seams for filter dispatch, fallback, and resume
  logic
- the first refactor can stay inside
  `src/bioetl/infrastructure/adapters/pubmed` without reopening shared helper
  topology

Next code slice:

Slice `3H-2`: filter/fallback/resume split with compatibility facade.

Status: `completed`

Implemented write scope for `3H-2`:

- keep
  [`adapter_filter_fetch_mixin.py`](../../src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py)
  as the import-stable facade
- move filter/fallback/resume helper logic into
  [`_filter_fetch_support.py`](../../src/bioetl/infrastructure/adapters/pubmed/_filter_fetch_support.py)
- preserve the public symbol `PubMedAdapterFilterFetchMixin`
- keep `pubmed_client.py` and fallback decorator wiring unchanged

Implementation result:

- `adapter_filter_fetch_mixin.py` now acts as a thinner provider-bounded
  facade;
- filter dispatch, fallback execution, PMID resolution, and resume-offset
  helpers now live in `_filter_fetch_support.py`;
- `adapter_filter_fetch_mixin.py` dropped from `340` to `225` LOC while
  preserving the same public surface and caller contracts.

Next closeout step:

- add a small ratchet so
  [`adapter_filter_fetch_mixin.py`](../../src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py)
  stays a bounded facade and does not absorb filter/fallback/resume helpers
  again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py tests/unit/infrastructure/adapters/pubmed/test_fallback.py tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py src/bioetl/infrastructure/adapters/pubmed/_filter_fetch_support.py src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`

## Definition Of Done For Current Slice

This cluster transition is complete when:

1. `pubmed/adapter_filter_fetch_mixin.py` is explicitly selected as the next
   provider-bounded hotspot after the shared HTTP helpers;
2. `adapter_filter_fetch_mixin.py` is narrowed without changing the public
   mixin surface;
3. the verify set is explicit and green for the current split;
4. the next implementation step is reduced to a possible ratchet or to the
   next bounded hotspot rather than a broader PubMed rewrite.
