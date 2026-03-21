# Wave 3 PubMed Models Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3O-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`,
`chembl/fetch_paging_mixin.py`, `semanticscholar/fetch_adapter_mixin.py`,
`crossref/client.py`, `chembl/entity_mapper.py`, and `pubchem/client.py`
splits inside `Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/pubmed/models.py`](../../src/bioetl/infrastructure/adapters/pubmed/models.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter/model
  files in the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `pubmed/models.py` in the remaining
  provider-bounded hotspot group at `301` LOC.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `pubmed/models.py` — `301` LOC
- `crossref/models.py` — `301`

`pubmed/models.py` was a good next bounded cluster because:

1. it stays inside one provider family rather than a shared seam;
2. the file already had a visible internal seam between article/extended record
   models and ESearch response DTOs;
3. package-root exports and DTO imports are narrow enough to preserve with thin
   re-exports;
4. compatibility can be locked with a tiny direct test.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/pubmed/models.py`](../../src/bioetl/infrastructure/adapters/pubmed/models.py)

Immediate adjacent files allowed only if needed by the split:

- new internal PubMed modules created strictly for the split
- [`src/bioetl/infrastructure/adapters/pubmed/__init__.py`](../../src/bioetl/infrastructure/adapters/pubmed/__init__.py) only as export-surface context

Target test net:

- [`tests/unit/infrastructure/adapters/pubmed/test_models_compat.py`](../../tests/unit/infrastructure/adapters/pubmed/test_models_compat.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py`](../../tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py)
- [`tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py`](../../tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded PubMed family shape before code
movement:

- package root re-exported only the major DTOs from `models.py`;
- there were no broad call-site dependencies on internal class ordering;
- the file had a natural split between article/extended metadata models and
  ESearch response models.

Public collaborator symbols that must remain stable through the first internal
split:

- `PubMedArticleRecord`
- `PubMedExtendedRecord`
- `PubMedSearchResponse`
- `PubMedSearchResult`
- `PUBMED_RECORD_MODELS`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the PubMed models module.

Preferred split direction:

- keep `models.py` as the public import-stable facade;
- move ESearch response DTOs into a private internal helper module;
- leave article and extended record models in `models.py`;
- preserve package-root re-exports and DTO compatibility.

Reasonable internal target for the first slice:

- `_search_models.py`

## Immediate Slice

Slice `3O-1`: cluster ledger and PubMed models preflight.

Status: `completed`

Deliverables:

- confirm package-root export surface for PubMed models
- confirm the visible seam between record models and search-response DTOs
- freeze first write scope around `models.py` plus one internal helper only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live blast radius is bounded to the PubMed adapter family;
- the file had a clear split point between article models and search DTOs;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/pubmed` without reopening client/fallback
  topology.

Next code slice:

Slice `3O-2`: search-model split with compatibility facade.

Status: `completed`

Implemented write scope for `3O-2`:

- keep
  [`models.py`](../../src/bioetl/infrastructure/adapters/pubmed/models.py)
  as the public import-stable facade
- move ESearch response DTOs into
  [`_search_models.py`](../../src/bioetl/infrastructure/adapters/pubmed/_search_models.py)
- preserve the public collaborator symbols exported by `models.py`
- add a direct compatibility test for module and package-root re-exports

Implementation result:

- `models.py` now acts as a thinner public facade;
- ESearch response DTOs now live in `_search_models.py`;
- article and extended record models remain in `models.py`;
- package-root re-exports remain unchanged;
- `models.py` was reduced from `301` to `266` LOC.

Next closeout step:

- add a small ratchet so
  [`models.py`](../../src/bioetl/infrastructure/adapters/pubmed/models.py)
  stays a bounded facade and does not absorb search-response DTOs again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/pubmed/test_models_compat.py tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/pubmed`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the PubChem
   client split;
2. `models.py` is reduced to one bounded PubMed family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one PubMed search-model split
   rather than a broader provider rewrite.
