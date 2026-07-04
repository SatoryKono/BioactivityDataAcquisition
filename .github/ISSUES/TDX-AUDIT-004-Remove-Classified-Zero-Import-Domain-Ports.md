---
title: "[TDX-AUDIT-004] Remove classified zero-import domain ports after importer proof"
labels: P1, technical-debt, dead-code, domain, ddd, cleanup
assignees: []
---

## Context

The dead-code inventory on current `main` reports `9` classified zero-import
candidates. Several of them are domain port modules that no longer show static
repo importers.

## Evidence

- `reports/quality/dead-code-inventory.md`
- `src/bioetl/domain/ports/data_normalization.py`
- `src/bioetl/domain/ports/data_source.py`
- `src/bioetl/domain/ports/delta_reader.py`
- `src/bioetl/domain/ports/filtering.py`
- `src/bioetl/domain/ports/idmapping.py`
- `src/bioetl/domain/ports/pii.py`
- `src/bioetl/domain/ports/protein_classification.py`
- `src/bioetl/domain/ports/resilience.py`
- `src/bioetl/__main__.py`

## Problem

This is dead-code debt.

Even when these modules are already classified, they still expand the conceptual
surface of the domain and leave stale extension points that no longer map to
live architecture.

## Required Outcome

- Remove zero-import modules that no longer have justified consumers.
- Where a module must remain, record a specific retention rationale and owner.
- Keep the dead-code inventory and importer evidence synchronized.

## File-level Implementation Plan

### Changes

- `reports/quality/dead-code-inventory.md`: regenerate after each removal or
  retention decision.
- `src/bioetl/domain/ports/*.py`: remove or explicitly retain with rationale.
- `src/bioetl/__main__.py`: re-evaluate whether it remains a supported entry
  surface.

### Refactoring actions

Do not replace removed modules with new alias modules. Migrate any discovered
callers to live canonical surfaces first.

## Constraints

- Do not remove a public surface without importer proof.
- Do not delete interfaces that still have external support commitments.
- Do not increase dead-code budgets or hide candidates from the report.

## Acceptance Criteria

- [ ] The zero-import candidate count decreases, or every retained candidate has
      explicit owner and rationale.
- [ ] No removed module has `src/` or test importers.
- [ ] Dead-code inventory and architecture guards pass after regeneration.

