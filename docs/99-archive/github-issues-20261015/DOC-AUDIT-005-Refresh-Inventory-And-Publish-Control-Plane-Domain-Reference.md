---
title: "docs(reference): refresh current-state inventory and publish a dedicated domain control-plane reference page"
labels: documentation, architecture, enhancement
assignees: []
---

## Context

The 2026-06-19 documentation audit found two closely related reference-surface
gaps:

1. `current-state-inventory.md` is stale on some generated/current values.
2. `docs/04-reference/domain/` has no dedicated control-plane page even though
   `src/bioetl/domain/control_plane/` is now a first-class domain surface.

## Problem

### Inventory drift

`docs/02-architecture/current-state-inventory.md` still reports:

- datasource provisioning as `grafana/provisioning/datasources/*.yml`;
- `source modules: 2168`.

But the audited current state is:

- split provisioning under `datasources-core/` and `datasources-tracing/`;
- committed `HEAD` Python module count under `src/bioetl`: `2170`.

### Domain reference coverage gap

`docs/04-reference/domain/` currently covers aggregates, events, invariants,
ports, value objects, and workflow state machine, but not the domain
control-plane family itself:

- `run_manifest.py`
- `run_ledger.py`
- `workflow_manifest.py`
- `workflow_ledger.py`
- `workflow_execution_state.py`
- `contract_registry.py`
- `gold_contract.py`
- `reproducibility_policy.py`

Today that knowledge is spread between architecture docs and contract docs,
which weakens the domain reference map.

## Evidence

- `docs/02-architecture/current-state-inventory.md:214`
- `docs/02-architecture/current-state-inventory.md` (source module count section)
- `grafana/provisioning/**`
- committed `HEAD` module count under `src/bioetl` = `2170`
- `docs/04-reference/domain/README.md`
- `src/bioetl/domain/control_plane/**`
- `docs/04-reference/contracts/run-manifest-ledger.md`
- `docs/02-architecture/domain-control-plane.md`

## Proposed Solution

1. Refresh `current-state-inventory.md` from the live repo state.
2. Add a dedicated domain reference page for control-plane artifacts under
   `docs/04-reference/domain/`.
3. Link the new page from `docs/04-reference/domain/README.md`.
4. Keep contract-level details in `run-manifest-ledger.md`, but give the domain
   catalog a direct entry for control-plane concepts and ownership seams.

## Acceptance Criteria

- [ ] `current-state-inventory.md` matches the current provisioning layout and repo counts.
- [ ] `docs/04-reference/domain/` includes a dedicated control-plane page.
- [ ] The new page links clearly to `run-manifest-ledger.md`, ADR-044, ADR-046, and ADR-047.
- [ ] The domain reference map no longer requires readers to infer control-plane coverage from architecture docs alone.

## Validation

```bash
find grafana/provisioning -maxdepth 3 -type f | sort
git ls-tree -r --name-only HEAD src/bioetl | rg '\\.py$' | wc -l
find docs/04-reference/domain -maxdepth 1 -type f | sort
```

## Non-Goals

- changing control-plane runtime behavior
- redesigning the current-state inventory format
- duplicating every contract detail into the new domain reference page

