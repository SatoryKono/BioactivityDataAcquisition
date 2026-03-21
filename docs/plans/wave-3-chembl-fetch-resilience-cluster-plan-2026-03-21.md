# Wave 3 ChEMBL Fetch Resilience Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, preflight completed  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, and
`health_check_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog keeps `chembl/fetch_resilience_mixin.py` in the
  first infrastructure-adapter concentration wave
- the current live size snapshot still places it in the top remaining adapter
  hotspot group at `367` LOC

## Why This Cluster Next

Three files are currently tied at `367` LOC:

- `http/health_monitor.py`
- `error_handling.py`
- `chembl/fetch_resilience_mixin.py`

`chembl/fetch_resilience_mixin.py` is the safest next bounded cluster because:

1. its caller surface is narrower than the other two candidates;
2. it is effectively confined to the ChEMBL fetch family rather than shared
   across multiple provider or interface layers;
3. the visible responsibility seams are already present in code:
   retry-exhausted recovery, direct-record fallback, dedup-aware batch
   reduction, and split-batch policy logging;
4. its behavior net is already anchored by focused ChEMBL adapter tests.

`health_monitor.py` and `error_handling.py` remain important backlog items, but
their current blast radius is broader and less suitable for the next small
bounded slice.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py)
- [`src/bioetl/infrastructure/adapters/chembl/client.py`](../../src/bioetl/infrastructure/adapters/chembl/client.py)
- other new internal ChEMBL modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client.py)
- [`tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirms a bounded ChEMBL family shape before code
movement:

- direct `src/` importer:
  [`fetch_adapter_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py)
  imports `ChemblFetchResilienceMixin`
- outer runtime family anchor:
  [`client.py`](../../src/bioetl/infrastructure/adapters/chembl/client.py)
  composes `ChemblFetchAdapterMixin` into `ChemblAdapter`
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/chembl/test_chembl_client.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client.py)
  - [`tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`](../../tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `ChemblFetchResilienceMixin`
- `CHEMBL_ADAPTER_ERRORS`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of the ChEMBL fetch resilience flow.

Preferred split direction:

- keep `fetch_resilience_mixin.py` as the temporary import-stable facade
- separate direct-record fallback and retry-exhausted recovery helpers from the
  public mixin shell
- keep `ChemblFetchAdapterMixin` and `ChemblAdapter` inheritance shape unchanged
  during the first move

Reasonable internal targets for the first slice:

- `_fetch_resilience_recovery.py`
- `_fetch_resilience_fallback.py`

The exact file map may differ, but the first slice must stay inside the bounded
ChEMBL fetch family and preserve current imports from
`bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin`.

## Immediate Slice

Slice `3D-1`: cluster ledger and resilience-flow split preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `ChemblFetchResilienceMixin`
- confirm that `fetch_adapter_mixin.py` is the live `src/` caller contract
- freeze first write scope around `fetch_resilience_mixin.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the ChEMBL fetch family
- tests already anchor the runtime behavior at adapter level
- the first refactor can stay inside `src/bioetl/infrastructure/adapters/chembl`
  without reopening broader adapter or interface topology

Next code slice:

Slice `3D-2`: resilience-flow split with compatibility facade.

Planned write scope for `3D-2`:

- keep
  [`fetch_resilience_mixin.py`](../../src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py)
  as the temporary import-stable facade
- add one or more small internal ChEMBL modules for retry-recovery or fallback
  logic
- avoid changes to `fetch_adapter_mixin.py` or `client.py` unless typing or
  import wiring requires a minimal adjustment
- avoid touching unrelated ChEMBL helpers in the same slice

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/chembl/test_chembl_client.py tests/unit/infrastructure/adapters/chembl/test_chembl_client_coverage.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/chembl`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the health split;
2. `fetch_resilience_mixin.py` is narrowed to one bounded family and split
   shape;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one ChEMBL resilience-flow split
   rather than a broader utility-layer rewrite.
