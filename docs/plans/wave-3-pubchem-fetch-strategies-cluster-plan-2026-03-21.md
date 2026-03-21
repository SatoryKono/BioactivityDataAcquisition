# Wave 3 PubChem Fetch Strategies Cluster Plan

Date: 2026-03-21  
Status: active bounded-cluster plan, `3I-2` implemented  
Parent program: [consolidated-master-refactor-plan-2026-03-20.md](./consolidated-master-refactor-plan-2026-03-20.md)

## Purpose

This plan opens the next bounded adapter hotspot after the completed
`crossref/batch.py`, `http/client_retry_mixin.py`, `health_check_mixin.py`,
`chembl/fetch_resilience_mixin.py`, `openalex/filter_fetch_adapter_mixin.py`,
`error_handling.py`, `http/health_monitor.py`, and
`pubmed/adapter_filter_fetch_mixin.py` splits inside
`Wave 3: Adapter and infrastructure hotspot reduction`.

The next cluster is centered on
[`src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py).

This selection is evidence-backed from two directions:

- the dependency-hotspot backlog still keeps provider-bounded adapter helpers in
  the first infrastructure-adapter concentration wave;
- the current local size snapshot kept `pubchem/fetch_strategies.py` in the top
  remaining provider-bounded hotspot group at `345` LOC, while larger shared
  seams such as `common/base_title_fallback.py` and
  `cached_bronze_data_source.py` have broader blast radius.

## Why This Cluster Next

Current remaining hotspot comparison inside
`src/bioetl/infrastructure/adapters` showed:

- `pubchem/fetch_strategies.py` — `345` LOC
- `chembl/fetch_paging_mixin.py` — `343`
- `semanticscholar/fetch_adapter_mixin.py` — `317`
- `pubchem/client.py` — `306`

`pubchem/fetch_strategies.py` was the safest next bounded cluster because:

1. it stays inside one provider family rather than a shared utility seam;
2. the live `src` caller contract is narrow and explicit through
   [`client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py);
3. the file already had a visible internal seam between query/search flow and
   identifier-based fetch loops;
4. its behavior is already anchored by dedicated PubChem fetch-strategy tests.

## Cluster Scope

Primary target:

- [`src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py)

Immediate adjacent files allowed only if needed by the split:

- [`src/bioetl/infrastructure/adapters/pubchem/client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py)
- [`src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py)
- [`src/bioetl/infrastructure/adapters/pubchem/policy_helper.py`](../../src/bioetl/infrastructure/adapters/pubchem/policy_helper.py)
- [`src/bioetl/infrastructure/adapters/pubchem/query_builder.py`](../../src/bioetl/infrastructure/adapters/pubchem/query_builder.py)
- [`src/bioetl/infrastructure/adapters/pubchem/response_mapper.py`](../../src/bioetl/infrastructure/adapters/pubchem/response_mapper.py)
- new internal PubChem modules created strictly for the split

Target test net:

- [`tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py`](../../tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py)
- [`tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies_compat.py`](../../tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies_compat.py)
- [`tests/unit/infrastructure/adapters/pubchem/test_adapter.py`](../../tests/unit/infrastructure/adapters/pubchem/test_adapter.py)
- [`tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py`](../../tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py)

Supporting guards:

- [`tests/architecture/test_code_metrics.py`](../../tests/architecture/test_code_metrics.py)
- [`tests/architecture/test_max_loc_per_file.py`](../../tests/architecture/test_max_loc_per_file.py)
- [`tests/architecture/test_architecture_dependency_docs_drift.py`](../../tests/architecture/test_architecture_dependency_docs_drift.py)

## Current Preflight Snapshot

Cluster-start inventory confirmed a bounded PubChem family shape before code
movement:

- direct `src/` importer:
  [`client.py`](../../src/bioetl/infrastructure/adapters/pubchem/client.py)
  consumes `PubChemFetchStrategies` through injected composition wiring;
- the current facade already collaborates with extracted helpers via:
  - [`fetch_flow.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py)
  - [`policy_helper.py`](../../src/bioetl/infrastructure/adapters/pubchem/policy_helper.py)
  - [`query_builder.py`](../../src/bioetl/infrastructure/adapters/pubchem/query_builder.py)
  - [`response_mapper.py`](../../src/bioetl/infrastructure/adapters/pubchem/response_mapper.py)
- direct behavior anchors:
  - [`tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py`](../../tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py)
  - [`tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies_compat.py`](../../tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies_compat.py)
  - [`tests/unit/infrastructure/adapters/pubchem/test_adapter.py`](../../tests/unit/infrastructure/adapters/pubchem/test_adapter.py)

Public collaborator symbols that must remain stable through the first internal
split:

- `PubChemFetchStrategies`

## Target Shape

The intended first slice is not a behavior rewrite. It should only narrow the
internal topology of PubChem fetch-strategy flow.

Preferred split direction:

- keep `fetch_strategies.py` as the temporary import-stable facade;
- move query/search, substance, and assay fetch flow into a private internal
  helper module;
- leave CID, SMILES, and InChIKey loops in the facade for the first move;
- keep the injected `PubChemFetchStrategies` contract unchanged for
  `PubChemAdapter`.

Reasonable internal target for the first slice:

- `_fetch_strategy_search.py`

## Immediate Slice

Slice `3I-1`: cluster ledger and PubChem fetch-strategy preflight.

Status: `completed`

Deliverables:

- confirm current direct importers of `PubChemFetchStrategies`
- confirm that `client.py` is the live `src/` caller contract
- freeze first write scope around `fetch_strategies.py` plus new internal
  modules only
- keep docs/evidence language aligned with a temporary compatibility seam

Preflight result:

- the live `src` blast radius is bounded to the PubChem adapter family;
- the file already had a visible seam between search flow and identifier-based
  loop helpers;
- the first refactor could stay inside
  `src/bioetl/infrastructure/adapters/pubchem` without reopening shared
  adapter-base or interface topology.

Next code slice:

Slice `3I-2`: search-flow split with compatibility facade.

Status: `completed`

Implemented write scope for `3I-2`:

- keep
  [`fetch_strategies.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py)
  as the temporary import-stable facade
- move query-based search, substance, and assay flow into
  [`_fetch_strategy_search.py`](../../src/bioetl/infrastructure/adapters/pubchem/_fetch_strategy_search.py)
- preserve the public collaborator symbol `PubChemFetchStrategies`
- keep changes inside the bounded PubChem adapter family without reopening
  `PubChemAdapter` runtime wiring

Implementation result:

- `fetch_strategies.py` now acts as a thinner import-stable facade;
- query/search flow now lives in `_fetch_strategy_search.py`;
- identifier-based CID, SMILES, and InChIKey flow remains in the facade for the
  first move;
- the runtime contract for `PubChemAdapter` remains unchanged;
- `fetch_strategies.py` was reduced from `345` to `280` LOC.

Next closeout step:

- add a small ratchet so
  [`fetch_strategies.py`](../../src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py)
  stays a bounded facade and does not absorb query/search flow again.

## Verification

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies.py tests/unit/infrastructure/adapters/pubchem/test_fetch_strategies_compat.py tests/unit/infrastructure/adapters/pubchem/test_adapter.py tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines tests/architecture/test_code_metrics.py::TestGodObjectDetection::test_large_classes_have_delegation tests/architecture/test_max_loc_per_file.py tests/architecture/test_architecture_dependency_docs_drift.py::test_dependency_map_drift_check_passes_current_repo`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/infrastructure/adapters/pubchem`

## Definition Of Done For Cluster Start

This cluster-start transition is complete when:

1. the next bounded adapter hotspot is explicitly chosen after the PubMed split;
2. `fetch_strategies.py` is reduced to one bounded PubChem family split target;
3. the verify set is explicit before code movement starts;
4. the next implementation step is reduced to one PubChem search-flow split
   rather than a broader PubChem adapter rewrite.
