---
title: "[TDX-AUDIT-018] Consolidate composition bootstrap runtime composite builder bundles"
labels: P1, technical-debt, composition, bootstrap, hotspot, refactor
assignees: []
---

## Context

Hotspot duplication for `composition/bootstrap/runtime` is zero, but the
`2026-07-03` audit still shows a large wiring surface: `48` modules under
`src/bioetl/composition/bootstrap/runtime/`, with `max_internal_fan_in=3/3`
and multiple `composite_*_bundle` / `composite_*_builder` modules. Related CLI
bootstrap code lives separately under `composition/bootstrap/cli/` (`12`
modules).

Wave 2 `#5864` reduced `composition_runtime_builders` hotspot pressure
(`files_ge_250_loc=0`, fan-in `5/5`), but bootstrap runtime assembly remains a
change-sensitive composition root.

## Evidence

- `reports/quality/hotspot-family-baseline.json`
- `src/bioetl/composition/bootstrap/runtime/composite_control_plane_builder.py`
- `src/bioetl/composition/bootstrap/runtime/composite_control_plane_bundle.py`
- `src/bioetl/composition/bootstrap/runtime/composite_execution_support_builder.py`
- `src/bioetl/composition/bootstrap/runtime/composite_execution_support_bundle.py`
- `src/bioetl/composition/bootstrap/runtime/composite_merge_service_builder.py`
- `src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py`
- `src/bioetl/composition/bootstrap/runtime/composite.py`
- `src/bioetl/composition/bootstrap/cli/__init__.py`

## Problem

This is architectural debt and hotspot debt.

Composite bootstrap wiring is split across many small bundle/builder modules with
near-budget fan-in. That increases DI review cost and makes runtime/bootstrap
changes harder to reason about, even without duplicate clusters.

## Required Outcome

- Consolidate composite bootstrap bundles along invariant boundaries (control
  plane, execution support, merge, observability) without moving DI out of the
  composition root.
- Reduce module count and/or internal fan-in while keeping duplication at zero.
- Refresh hotspot-family baseline and keep budgets flat or decreasing.

## File-level Implementation Plan

### Changes

- `src/bioetl/composition/bootstrap/runtime/composite_*_{bundle,builder}.py`:
  merge closely related bundles where they share lifecycle and dependency graph.
- `src/bioetl/composition/bootstrap/runtime/composite.py`: keep the public
  lazy facade; narrow exports after internal consolidation.
- `src/bioetl/composition/bootstrap/runtime/__init__.py`: align lazy exports
  with consolidated owners.
- `tests/unit/composition/bootstrap/runtime/`: extend behavioral tests for
  composite bootstrap assembly paths.
- `reports/quality/hotspot-family-baseline.json`: regenerate after each split
  or consolidation batch.

### Refactoring actions

Prefer explicit registry manifests over ad hoc builder proliferation. Do not push
wiring into domain or infrastructure layers.

## Constraints

- Composition root remains the only DI assembly point.
- Do not increase hotspot bounded-growth budgets.
- Preserve deterministic bootstrap ordering and idempotent runtime patch behavior
  per ADR-048.

## Acceptance Criteria

- [ ] `composition_bootstrap_runtime` hotspot metrics improve or hold without
      budget growth (files, fan-in, helper ratio).
- [ ] Composite bootstrap bundle/builder modules are fewer or have lower fan-in
      than the current baseline.
- [ ] Hotspot duplication for bootstrap/runtime remains `0`.
- [ ] Architecture and unit tests pass after baseline refresh.
