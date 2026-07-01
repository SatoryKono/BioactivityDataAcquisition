---
title: "[TDX-AUDIT-003] Consolidate pipeline transformer contract duplication across provider families"
labels: P1, technical-debt, duplication, pipeline, application, refactor
assignees: []
---

## Context

The `2026-07-01` audit found `11` remaining duplication clusters in
`src/bioetl/application/pipelines`, mainly repeated transformer contract
patterns across provider families.

## Evidence

- `reports/quality/full-app-duplication-baseline.json`
- `src/bioetl/application/pipelines/crossref/transformer.py`
- `src/bioetl/application/pipelines/openalex/transformer.py`
- `src/bioetl/application/pipelines/pubchem/transformer.py`
- `src/bioetl/application/pipelines/pubmed/transformer.py`
- `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py`

## Problem

This is duplication debt.

Transformer modules keep re-implementing similar contract skeletons, which
spreads normalization policy and makes provider-specific divergence harder to
audit.

## Required Outcome

- Shared transformer contract structure moves to canonical base owners.
- Provider pipelines keep only provider-specific mapping logic.
- The duplication baseline reflects a measurable reduction for pipeline
  transformer families.

## File-level Implementation Plan

### Changes

- `src/bioetl/application/pipelines/**/transformer.py`: rework repeated
  skeletons into canonical base abstractions.
- `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py`:
  re-evaluate as a canonical owner candidate or reduce to provider-specific
  deltas.
- `reports/quality/full-app-duplication-baseline.json`: regenerate after the
  consolidation wave.

### Refactoring actions

Preserve domain and application boundaries. Do not hide provider differences
behind over-generalized abstractions.

## Constraints

- Do not weaken DQ, contract, or normalization behavior.
- Do not move runtime I/O concerns into application transformers.
- Do not increase duplication budgets.
- Preserve deterministic transformation and replay outputs.

## Acceptance Criteria

- [ ] Pipeline transformer duplicate clusters decrease from the current
      baseline.
- [ ] Shared transformer base responsibilities are explicit and localized.
- [ ] Provider-specific behavior remains covered by existing golden/contract
      tests.
- [ ] Regenerated duplication and pipeline-governance artifacts stay green.

