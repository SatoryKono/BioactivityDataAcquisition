---
title: "[TDX-AUDIT-017] Migrate first-party lazy-export consumers to canonical import owners"
labels: P1, technical-debt, compatibility, composition, refactor, imports
assignees: []
---

## Context

The compatibility census reports `12` retained public entrypoints and `4` public
export facades with `transition_debt: []`, but the repo still maintains
`43` module-level lazy `__getattr__` surfaces classified in
`tests/architecture/test_lazy_export_public_api_inventory.py`.

Wave 1 `#5839` froze retained surfaces; Wave 2 `#5864` explicitized runtime
builder registration. The remaining work is to reduce first-party `src/` and
`tests/` imports that still route through lazy facades where canonical owners
exist.

## Evidence

- `tests/architecture/test_lazy_export_public_api_inventory.py`
- `configs/quality/compatibility_facade_inventory.yaml`
- `reports/quality/compatibility-importer-census.json`
- `src/bioetl/composition/lazy_exports.py`
- `src/bioetl/composition/runtime_builders/__init__.py`
- `src/bioetl/composition/bootstrap/runtime/__init__.py`
- `src/bioetl/infrastructure/config/__init__.py`
- `docs/02-architecture/07-compatibility-facade-inventory.md`

## Problem

This is compatibility debt.

Lazy exports are sanctioned for external stability, but internal first-party
code should prefer canonical module paths. Uncontrolled internal use increases
indirection, slows static analysis, and makes facade removal harder later.

## Required Outcome

- Produce an importer map for top lazy-export surfaces with first-party
  `src/` and `tests/` consumers.
- Migrate internal importers to canonical owners without breaking public API.
- Keep `EXPECTED_LAZY_EXPORT_FACADES` inventory stable or shrinking; block new
  unclassified surfaces.

## File-level Implementation Plan

### Changes

- `reports/quality/compatibility-importer-census.json`: refresh after migration
  batches (regenerate via QA tooling).
- Priority surfaces:
  - `src/bioetl/composition/bootstrap/runtime/__init__.py`
  - `src/bioetl/composition/runtime_builders/__init__.py`
  - `src/bioetl/infrastructure/config/__init__.py`
  - CLI domain lazy packages under `src/bioetl/interfaces/cli/commands/domains/*/`
- Replace first-party imports only; retain external entrypoints per inventory.
- Add architecture test guard prohibiting new internal imports of deprecated
  facade paths where canonical replacements exist.

### Refactoring actions

Migrate in small batches per owner package. Do not remove public facades in
this issue; only shrink internal dependency on them.

## Constraints

- Do not break external public import paths without a versioned migration note.
- Do not add new lazy-export surfaces without classifying them in the inventory
  test.
- Do not increase compatibility debt budgets.

## Acceptance Criteria

- [ ] Importer map exists for the priority lazy-export surfaces.
- [ ] First-party `src/` importers to those surfaces decrease from baseline.
- [ ] `test_lazy_export_public_api_inventory` passes with no unclassified drift.
- [ ] Public entrypoint count remains `12` or lower; facades remain `4` or lower.
