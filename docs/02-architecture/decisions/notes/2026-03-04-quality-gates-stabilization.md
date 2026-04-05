______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: '@bioetl-architecture'
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Decision Note: P0-1 Architecture Quality-Gate Stabilization

Date: 2026-03-04
Owner: @bioetl-architecture

## Scope

- Stabilize `tests/architecture` on the working branch.
- Keep global quality budgets unchanged.

## Actions

1. Refined adapter contract classification to validate concrete adapter entrypoints and exclude `*_mixin.py` / helper modules.
1. Structurally decomposed ChEMBL fetch path:
   - `fetch_paging_mixin.py`
   - `fetch_resilience_mixin.py`
   - slimmed `fetch_mixin.py` orchestration layer.
1. Synced class-level exemption values to current decomposed code shape (no layer-wide limit increase).

## Guardrails

- No global threshold increase.
- Exemption sync must accompany real code decomposition/refactor.
