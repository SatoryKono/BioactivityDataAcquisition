# Wave 3 ChEMBL Entity Mapper Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3M-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`,
`pubmed/adapter_filter_fetch_mixin.py`, `pubchem/fetch_strategies.py`,
`chembl/fetch_paging_mixin.py`, `semanticscholar/fetch_adapter_mixin.py`, and
`crossref/client.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/chembl/entity_mapper.py`](../../src/bioetl/infrastructure/adapters/chembl/entity_mapper.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter helpers in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `chembl/entity_mapper.py` in the top
  remaining provider-bounded hotspot group at `322` LOC, while larger shared
  seams such as `common/base_title_fallback.py` and
  `cached_bronze_data_source.py` have broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `chembl/entity_mapper.py` — `322` LOC
- `pubchem/client.py` — `305`
- `pubmed/models.py` — `301`
- `crossref/models.py` — `301`

`chembl/entity_mapper.py` was a good next bounded cluster because:

1. it stays inside one provider family rather than a shared utility seam;
2. its live `src` callers are concentrated in the ChEMBL adapter family;
3. the file already had a visible seam between public mapper methods and bulky
   static lookup/data logic;
4. behavior is already anchored by unit and integration tests that exercise the
   public `ChemblEntityMapper` contract.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/chembl/entity_mapper.py`](../../src/bioetl/infrastructure/adapters/chembl/entity_mapper.py)

Immediate adjacent files allowed only if needed by the split:

- new internal ChEMBL modules created strictly for the split
- [`src/bioetl/domain/registry/publication.py`](../../src/bioetl/domain/registry/publication.py) only as read-only context

Target test net:

- [`tests/unit/infrastructure/test_adapters.py`](../../tests/unit/infrastructure/test_adapters.py)
- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client.py)
- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py)
- [`tests/integration/adapters/test_chembl.py`](../../tests/integration/adapters/test_chembl.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded ChEMBL family shape before code
movement:

- direct `src` callers are concentrated in ChEMBL adapter modules using the
  public `ChemblEntityMapper` API;
- test coverage is mostly indirect but stable, through adapter and integration
  suites that exercise URL/resource resolution and invalid-entity behavior;
- the file already had a natural split line between public static methods and
  bulky non-publication lookup dictionaries.

Public collaborator symbols that must remain stable through the first internal
split:

- `ChemblEntityMapper`
- `CHEMBL_API_BASE`
- `ENTITY_MAPPING`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the ChEMBL entity mapper.

Preferred split direction:

- keep `entity_mapper.py` as the public import-stable facade;
- move bulky static lookup/data logic into a private internal helper module;
- leave public `ChemblEntityMapper` methods and backward-compatible
  `ENTITY_MAPPING` export in the facade;
- keep the adapter family contract unchanged.

Reasonable internal target for the first slice:

- `_entity_mapping_lookup.py`

## Immediate Slice

Slice `3M-1`: cluster ledger and ChEMBL entity-mapper preflight.

Status: `completed`

Deliverables:

- confirm current test anchors for `ChemblEntityMapper`
- confirm that the public facade contract is the primary compatibility surface
- freeze first write scope around `entity_mapper.py` plus one internal helper
  only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live blast radius is bounded to the ChEMBL adapter family;
- the file had a visible seam between public methods and lookup/data logic;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/chembl` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3M-2`: lookup-data split with compatibility facade.

Status: `completed`

Implemented write scope for `3M-2`:

- keep
  [`entity_mapper.py`](../../src/bioetl/infrastructure/adapters/chembl/entity_mapper.py)
  as the public import-stable facade
- move non-publication lookup/data logic and resolution helpers into
  [`_entity_mapping_lookup.py`](../../src/bioetl/infrastructure/adapters/chembl/_entity_mapping_lookup.py)
- preserve the public collaborator symbols `ChemblEntityMapper`,
  `CHEMBL_API_BASE`, and `ENTITY_MAPPING`
- keep changes inside the bounded ChEMBL adapter family without reopening
  mapper call sites

Implementation result:

- `entity_mapper.py` now acts as a thinner public facade;
- lookup/data logic now lives in `_entity_mapping_lookup.py`;
- `ChemblEntityMapper` remains the public owner of the adapter-facing contract;
- `ENTITY_MAPPING` remains available as a backward-compatible export;
- `entity_mapper.py` was reduced from `322` to `225` LOC.

Next closeout step:

- add a small ratchet so
  [`entity_mapper.py`](../../src/bioetl/infrastructure/adapters/chembl/entity_mapper.py)
  stays a bounded facade and does not absorb bulky lookup/data logic again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/test_adapters.py tests/unit/infrastructure/adapters/chembl/test_chembl_client.py tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py tests/integration/adapters/test_chembl.py -k "entity_mapping or invalid_entity_type or chembl_client or get_entity_count or deduplicates or extraction_params"`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/chembl`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the CrossRef
   client split;
2. `entity_mapper.py` is reduced to one bounded ChEMBL family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one ChEMBL entity-mapper lookup
   split rather than a broader provider rewrite.
