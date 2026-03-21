# Wave 3 PubChem Client Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3N-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`,
`chembl/fetch_paging_mixin.py`, `semanticscholar/fetch_adapter_mixin.py`,
`crossref/client.py`, and `chembl/entity_mapper.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/pubchem/client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter facades in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `pubchem/client.py` in the top remaining
  provider-bounded hotspot group at `305` LOC, while larger shared seams such
  as `common/base_title_fallback.py` and `cached_bronze_data_source.py` have
  broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `pubchem/client.py` — `305` LOC
- `pubmed/models.py` — `301`
- `crossref/models.py` — `301`

`pubchem/client.py` was a good next bounded cluster because:

1. it stays inside one provider family rather than a shared utility seam;
2. the live `src` caller contract is concentrated around `PubChemAdapter`;
3. the file already had a visible seam between fetch-routing surface and
   runtime/health responsibilities;
4. its behavior is already anchored by direct PubChem adapter and request-metadata tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/pubchem/client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py)

Immediate adjacent files allowed only if needed by the split:

- new internal PubChem modules created strictly for the split
- [`src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py) only as read-only collaborator context

Target test net:

- [`tests/unit/infrastructure/adapters/pubchem/test_adapter.py`](../../tests/unit/infrastructure/adapters/pubchem/test_adapter.py)
- [`tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py)
- [`tests/unit/infrastructure/test_adapters.py`](../../tests/unit/infrastructure/test_adapters.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded PubChem family shape before code
movement:

- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/pubchem/test_adapter.py`](../../tests/unit/infrastructure/adapters/pubchem/test_adapter.py)
  - [`tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py)
  - [`tests/unit/infrastructure/test_adapters.py`](../../tests/unit/infrastructure/test_adapters.py)
- the current client already delegated query/filter execution to
  `fetch_strategies`, so the remaining mixed concern in `client.py` was the
  fetch-routing surface itself alongside health/runtime concerns.

Public collaborator symbols that must remain stable through the first internal
split:

- `PUBCHEM_HEALTH_ERRORS`
- `PubChemAdapter`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the PubChem client facade.

Preferred split direction:

- keep `client.py` as the public import-stable facade;
- move fetch-routing surface into a private internal mixin;
- leave runtime wiring and health/probe behavior in the facade for the first
  move;
- keep the injected `PubChemAdapter` contract unchanged.

Reasonable internal target for the first slice:

- `_client_fetch_surface.py`

## Immediate Slice

Slice `3N-1`: cluster ledger and PubChem client preflight.

Status: `completed`

Deliverables:

- confirm direct test anchors for `PubChemAdapter`
- confirm that `fetch_strategies` already owns detailed provider fetch logic
- freeze first write scope around `client.py` plus one internal helper only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live blast radius is bounded to the PubChem adapter family;
- the file had a visible seam between fetch-routing and health/runtime logic;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/pubchem` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3N-2`: fetch-surface split with compatibility facade.

Status: `completed`

Implemented write scope for `3N-2`:

- keep
  [`client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py)
  as the public import-stable facade
- move fetch-routing surface into
  [`_client_fetch_surface.py`](../../src/bioetl/infrastructure/adapters/pubchem/_client_fetch_surface.py)
- preserve the public collaborator symbols `PUBCHEM_HEALTH_ERRORS` and
  `PubChemAdapter`
- keep changes inside the bounded PubChem adapter family without reopening
  runtime wiring or strategy ownership

Implementation result:

- `client.py` now acts as a thinner public facade;
- fetch-routing surface now lives in `_client_fetch_surface.py`;
- runtime and health/probe behavior remain in `client.py`;
- the runtime contract for `PubChemAdapter` remains unchanged;
- `client.py` was reduced from `305` to `210` LOC.

Next closeout step:

- add a small ratchet so
  [`client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py)
  stays a bounded facade and does not absorb fetch-routing logic again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/pubchem/test_adapter.py tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py tests/unit/infrastructure/test_adapters.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/pubchem`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the ChEMBL
   entity-mapper split;
2. `client.py` is reduced to one bounded PubChem family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one PubChem client fetch-surface
   split rather than a broader provider rewrite.
