---
title: "[TDX-AUDIT-011] Explicitize composition runtime builder registration and ratchet DI fan-in"
labels: P1, technical-debt, architecture, composition, refactor, governance
assignees: []
---

## Context

The refreshed audit found `composition_runtime_builders` back at
`max_internal_fan_in=5/5`, with helper ratio and implicit provider registration
still creating evolution friction in the Composition Root.

## Evidence

- `reports/quality/total-tech-debt-audit-main-2026-07-01.md`
- `reports/quality/hotspot-duplication-baseline.json`
- `src/bioetl/composition/runtime_builders/**`
- `src/bioetl/composition/bootstrap/runtime/**`

## Problem

This is hotspot debt and architectural debt.

Runtime builder registration remains partly implicit, which makes DI ownership
harder to audit and keeps the composition family near its reviewed fan-in
ceiling.

## Required Outcome

- Make runtime builder registry/provider registration explicit.
- Reduce helper ratio and internal fan-in without moving DI outside the
  composition root.
- Keep provider-specific behavior local to its builder owners.

## File-level Implementation Plan

### Changes

- `src/bioetl/composition/runtime_builders/**`: make registration surfaces
  explicit and auditable.
- `src/bioetl/composition/bootstrap/runtime/**`: keep bootstrap-only activation
  boundaries intact.
- `reports/quality/hotspot-duplication-baseline.json`: regenerate after each
  consolidation batch.

### Refactoring actions

Do not create new cross-layer utility buckets. Prefer explicit registration over
hidden mixin wiring.

## Constraints

- Do not move domain or application I/O into composition helpers.
- Do not increase hotspot budgets or fan-in ceilings.
- Preserve deterministic bootstrap and replay semantics.

## Acceptance Criteria

- [ ] Runtime builder registration is explicit and documented by file.
- [ ] `composition_runtime_builders` fan-in decreases or stays within ceiling
      without budget growth.
- [ ] Helper ratio improves on regenerated hotspot evidence.
- [ ] Composition and architecture governance checks pass after refresh.
