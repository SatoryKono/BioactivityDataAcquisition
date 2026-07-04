---
title: "[TDX-AUDIT-014] Burn down application pipeline transformer duplication from the 9-cluster baseline"
labels: P1, technical-debt, duplication, pipelines, application, refactor
assignees: []
---

## Context

Wave 1 `#5841` (`TDX-AUDIT-003`) established shared publication transformer
owners, but the refreshed `2026-07-03` full-app duplication baseline still
reports `9` duplicate clusters under `src/bioetl/application/pipelines`. The
dominant actionability category is
`pipeline_transformer_contract_pattern`.

## Evidence

- `reports/quality/full-app-duplication-baseline.json`
- `src/bioetl/application/pipelines/common/base_publication_transformer.py`
- `src/bioetl/application/pipelines/common/publication_transformer_context.py`
- `src/bioetl/application/pipelines/crossref/transformer.py`
- `src/bioetl/application/pipelines/openalex/transformer.py`
- `src/bioetl/application/pipelines/semanticscholar/transformer.py`
- `reports/quality/tech-debt-issues-5839-5845-closeout.json` (`#5841` evidence)

## Problem

This is duplication debt.

Provider pipeline transformers still repeat contract-shell logic that should live
in shared owners. That makes cross-provider parity changes expensive and raises
determinism risk when only some transformers pick up fixes.

## Required Outcome

- Reduce duplicate cluster count for `src/bioetl/application/pipelines` from `9`
  downward.
- Keep provider-specific normalization and field mapping local.
- Preserve deterministic transformer outputs and ordering semantics.

## File-level Implementation Plan

### Changes

- `src/bioetl/application/pipelines/common/base_publication_transformer.py`
  and `publication_transformer_context.py`: extend canonical shared contract.
- Provider `transformer.py` modules: delegate repeated shell logic to common
  owners.
- Add or extend provider parity tests where consolidation touches behavior.
- `reports/quality/full-app-duplication-baseline.json`: regenerate after each
  batch.

### Refactoring actions

Consolidate contract-pattern clusters before touching provider-specific mapping
logic. Avoid creating a cross-layer utility outside application pipelines.

## Constraints

- Do not change published pipeline output schemas without contract migration.
- Do not raise duplication budgets.
- Keep domain free of I/O; transformers stay in application layer.

## Acceptance Criteria

- [ ] Pipeline duplicate cluster count decreases from the `9` baseline.
- [ ] Shared transformer contract owners are explicit and tested.
- [ ] Provider transformers delegate repeated shell logic to common owners.
- [ ] Full-app duplication ratchet passes on regenerated artifacts.
