---
title: "[TDX-AUDIT-005] Extract shared composite config policy blocks into a canonical authority surface"
labels: P1, technical-debt, config, composite, governance, determinism
assignees: []
---

## Context

The `2026-07-01` audit confirmed that config drift is blocked, but sanctioned
duplication remains in the five composite configs. Shared policy blocks such as
field priorities, normalized anchor policy, provider lookup fields, and field
mappings are still repeated in each composite config.

The earlier non-composite config backlog issue `#5568` is closed and does not
cover this remaining composite-policy residue.

## Evidence

- `reports/quality/config-surface-backlog.json`
- `configs/composites/activity.yaml`
- `configs/composites/assay.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/publication.yaml`
- `configs/composites/target.yaml`

## Problem

This is config debt and determinism-governance debt.

The current duplication is intentionally sanctioned, but it still leaves a
manual multi-file authority surface for deterministic composite policy.

## Required Outcome

- Shared composite policy moves to one canonical authority mechanism.
- Entity-specific composite config files keep only entity-specific deltas.
- Sanctioned duplication is reduced rather than merely documented.

## File-level Implementation Plan

### Changes

- `reports/quality/config-surface-backlog.json`: regenerate after policy
  extraction.
- `configs/composites/*.yaml`: replace repeated shared policy blocks with the
  canonical authority surface or generated include path.
- Related config-governance tooling: add fail-fast drift detection for the new
  shared authority mechanism.

### Refactoring actions

Keep config behavior machine-auditable. Do not introduce runtime-only hidden
inheritance or manual copy steps.

## Constraints

- Do not weaken deterministic composite merge or lineage behavior.
- Do not increase config discrepancy or duplication budgets.
- Do not solve this by suppressing backlog clusters.

## Acceptance Criteria

- [ ] Shared composite policy duplication decreases from the current baseline.
- [ ] One canonical authority surface is documented for shared composite policy.
- [ ] Composite config behavior remains deterministic and regression-tested.
- [ ] Config backlog and governance checks pass after regeneration.

