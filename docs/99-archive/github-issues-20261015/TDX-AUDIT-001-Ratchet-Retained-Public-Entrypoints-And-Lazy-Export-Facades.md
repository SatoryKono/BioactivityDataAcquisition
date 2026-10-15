---
title: "[TDX-AUDIT-001] Ratchet retained public entrypoints and lazy export facades to canonical imports"
labels: P1, technical-debt, compatibility, architecture, composition, governance
assignees: []
---

## Context

The `2026-07-01` technical-debt audit on current `main` confirmed that the
blocking compatibility cleanup wave is closed, but residual sanctioned seams
remain live:

- `12` retained public entrypoints
- `4` retained public export facades
- multiple lazy-export package surfaces still acting as convenience seams

The earlier follow-up issue `#4864` is already closed, so the residual surface
needs a fresh owner.

## Evidence

- `reports/quality/compatibility-importer-census.md`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`
- `docs/02-architecture/07-compatibility-facade-inventory.md`
- `src/bioetl/composition/entrypoints.py`
- `src/bioetl/infrastructure/config/__init__.py`
- `src/bioetl/domain/composite/config.py`
- `src/bioetl/application/composite/merger.py`

## Problem

This is compatibility debt and governance debt.

The repo now tracks only sanctioned compatibility seams, but they are still
broad public import surfaces. That weakens Composition Root ownership, keeps
lazy exports alive longer than necessary, and leaves external-consumer risk
insufficiently explicit.

## Required Outcome

- Every retained seam has an explicit owner, consumer class, and sunset
  decision.
- First-party callers move to canonical internal modules wherever possible.
- No new lazy-export facade or sanctioned public seam is introduced.

## File-level Implementation Plan

### Changes

- `reports/quality/compatibility-importer-census.md`: regenerate after each
  caller migration.
- `docs/02-architecture/07-compatibility-facade-snapshot.md`: add explicit
  sunset metadata for each retained seam.
- `src/bioetl/composition/entrypoints.py`: narrow or remove retained wrappers
  after importer proof.
- `src/bioetl/infrastructure/config/__init__.py`: keep external compatibility
  only; ratchet first-party imports to zero growth.
- `src/bioetl/domain/composite/config.py` and
  `src/bioetl/application/composite/merger.py`: re-review public re-export
  necessity against current callers.

### Refactoring actions

Do not create replacement alias layers. Migrate first-party callers to the
canonical internal owners before shrinking public seams.

## Constraints

- Do not increase technical-debt budgets or compatibility caps.
- Do not break supported public imports without a deprecation window.
- Do not move I/O into domain or violate dependency direction.
- Preserve determinism, idempotency, and replay semantics.

## Acceptance Criteria

- [ ] Every retained public seam has owner, external-consumer class, and sunset
      status recorded in the canonical inventory.
- [ ] No new first-party imports of retained public facades appear in `src/`.
- [ ] At least one retained seam is removed, narrowed, or reclassified with
      evidence.
- [ ] Compatibility census and architecture governance tests stay green.

