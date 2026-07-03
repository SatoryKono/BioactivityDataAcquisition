---
title: "[TDX-AUDIT-010] Ratchet control-plane hotspot LOC and fan-in ceilings"
labels: P1, technical-debt, architecture, control-plane, refactor, governance
assignees: []
---

## Context

The refreshed audit found control-plane hotspot pressure still near reviewed
ceilings: `files_ge_250_loc=15/16` and `max_internal_fan_in=3/4` in the
application control-plane family.

## Evidence

- `reports/quality/total-tech-debt-audit-main-2026-07-01.md`
- `reports/quality/hotspot-duplication-baseline.json`
- `reports/quality/architecture-quality-scorecard.json`
- `src/bioetl/application/services/control_plane/**`

## Problem

This is hotspot debt.

The control-plane runtime surface remains large and change-sensitive. Without a
fresh ratchet owner, hotspot families can grow back toward reviewed budget
ceilings.

## Required Outcome

- Ratchet `files_ge_250_loc` from `15` downward in the control-plane family.
- Split diagnostics/persistence support by invariant boundary.
- Keep `max_internal_fan_in` at or below the reviewed ceiling.

## File-level Implementation Plan

### Changes

- `src/bioetl/application/services/control_plane/**`: split oversized modules by
  invariant boundary rather than mechanical file slicing.
- `reports/quality/hotspot-duplication-baseline.json`: regenerate after each
  ratchet batch.
- `reports/quality/architecture-quality-scorecard.json`: refresh if scorecard
  inputs change.

### Refactoring actions

Prefer explicit ownership boundaries over new cross-cutting helper buckets.

## Constraints

- Do not increase hotspot budgets or fan-in ceilings.
- Do not weaken control-plane contracts, replay, or determinism semantics.
- Preserve dependency direction and Composition Root ownership.

## Acceptance Criteria

- [ ] Control-plane `files_ge_250_loc` decreases from the current baseline.
- [ ] `max_internal_fan_in` remains within the reviewed ceiling.
- [ ] Split modules have explicit invariant ownership.
- [ ] Hotspot and architecture governance checks pass after regeneration.
