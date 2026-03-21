# Wave 3 CrossRef Models Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3P-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`,
`chembl/fetch_paging_mixin.py`, `semanticscholar/fetch_adapter_mixin.py`,
`crossref/client.py`, `chembl/entity_mapper.py`, `pubchem/client.py`, and
`pubmed/models.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/crossref/models.py`](../../src/bioetl/infrastructure/adapters/crossref/models.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter/model
  files in the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `crossref/models.py` as the last
  remaining provider-bounded hotspot at `301` LOC under the active `~300+ LOC`
  operational cutoff.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `crossref/models.py` — `301` LOC

`crossref/models.py` was the right next bounded cluster because:

1. it stays inside one provider family rather than a shared seam;
2. package-root DTO exports are already narrow and stable;
3. the file had a visible internal seam between the main publication-record DTO
   and the response-wrapper models;
4. compatibility could be frozen with a tiny direct re-export test.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/crossref/models.py`](../../src/bioetl/infrastructure/adapters/crossref/models.py)

Immediate adjacent files allowed only if needed by the split:

- new internal CrossRef modules created strictly for the split
- [`src/bioetl/infrastructure/adapters/crossref/__init__.py`](../../src/bioetl/infrastructure/adapters/crossref/__init__.py) only as export-surface context

Target test net:

- [`tests/unit/infrastructure/adapters/crossref/test_compatibility.py`](../../tests/unit/infrastructure/adapters/crossref/test_compatibility.py)
- [`tests/unit/infrastructure/adapters/crossref/test_crossref_client.py`](../../tests/unit/infrastructure/adapters/crossref/test_crossref_client.py)
- [`tests/unit/infrastructure/adapters/crossref/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/crossref/test_request_metadata.py)
- [`tests/unit/infrastructure/adapters/crossref/test_batch.py`](../../tests/unit/infrastructure/adapters/crossref/test_batch.py)
- [`tests/unit/infrastructure/adapters/crossref/test_fallback.py`](../../tests/unit/infrastructure/adapters/crossref/test_fallback.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded CrossRef models shape before code
movement:

- shared payload fragment models were already extracted in `models_shared.py`;
- direct runtime callers depended on the public facade exports, not on internal
  class ordering;
- the file still mixed the main `CrossRefPublicationRecord` DTO with response
  wrapper models for list and single-item endpoints.

Public collaborator symbols that had to remain stable through the first split:

- `CrossRefPublicationRecord`
- `CrossRefMessage`
- `CrossRefPublicationsResponse`
- `CrossRefPublicationResponse`
- `CROSSREF_RECORD_MODELS`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the CrossRef models facade.

Preferred split direction:

- keep `models.py` as the public import-stable facade;
- keep `CrossRefPublicationRecord` in `models.py` as the canonical record DTO;
- move the response-wrapper DTOs into a private internal helper module;
- preserve package-root re-exports and `CROSSREF_RECORD_MODELS`.

Reasonable internal target for the first slice:

- `_response_models.py`

## Immediate Slice

Slice `3P-1`: cluster ledger and CrossRef models preflight.

Status: `completed`

Deliverables:

- confirm package-root export surface for CrossRef models
- confirm the visible seam between the record DTO and response-wrapper DTOs
- freeze first write scope around `models.py` plus one internal helper only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live blast radius is bounded to the CrossRef adapter family;
- the file had a clear split point between `CrossRefPublicationRecord` and the
  response-wrapper models;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/crossref` without reopening client or
  package-topology changes.

Next code slice:

Slice `3P-2`: response-wrapper split with compatibility facade.

Status: `completed`

Implemented write scope for `3P-2`:

- keep
  [`models.py`](../../src/bioetl/infrastructure/adapters/crossref/models.py)
  as the public import-stable facade
- move response-wrapper DTOs into
  [`_response_models.py`](../../src/bioetl/infrastructure/adapters/crossref/_response_models.py)
- preserve the public collaborator symbols exported by `models.py`
- add a direct compatibility test for facade-to-helper re-exports

Implementation result:

- `models.py` now acts as a thinner public facade;
- response-wrapper DTOs now live in `_response_models.py`;
- `CrossRefPublicationRecord` remains the canonical record DTO owner in
  `models.py`;
- package-root re-exports remain unchanged;
- `models.py` was reduced from `301` to `247` LOC.

Next closeout step:

- add a small ratchet so
  [`models.py`](../../src/bioetl/infrastructure/adapters/crossref/models.py)
  stays a bounded facade and does not absorb response-wrapper DTOs again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/crossref/test_compatibility.py tests/unit/infrastructure/adapters/crossref/test_crossref_client.py tests/unit/infrastructure/adapters/crossref/test_request_metadata.py tests/unit/infrastructure/adapters/crossref/test_batch.py tests/unit/infrastructure/adapters/crossref/test_fallback.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/crossref`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the last provider-bounded `~300+ LOC` hotspot is explicitly selected and
   reduced;
2. `models.py` is reduced to one bounded CrossRef family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to closeout/ratchet work or to a
   broader shared-seam decision, not to another provider-bounded `~300+ LOC`
   adapter file.
