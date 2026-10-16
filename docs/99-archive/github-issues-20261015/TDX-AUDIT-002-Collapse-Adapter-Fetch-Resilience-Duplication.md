---
title: "[TDX-AUDIT-002] Collapse adapter fetch and resilience duplication under canonical template owners"
labels: P0, technical-debt, duplication, adapters, infrastructure, refactor
assignees: []
---

## Context

The `2026-07-01` technical-debt audit found that the largest remaining
duplication surface is `src/bioetl/infrastructure/adapters` with `54` duplicate
clusters. Most of the actionable residue is concentrated in fetch/resilience
mixins and repeated contract/error template logic.

## Evidence

- `reports/quality/full-app-duplication-baseline.json`
- `src/bioetl/infrastructure/adapters/common/fetch_resilience_template.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`
- `src/bioetl/infrastructure/adapters/common/error_bundles.py`
- `src/bioetl/infrastructure/adapters/pubmed/_errors.py`

## Problem

This is duplication debt and architectural debt.

The current adapter family still repeats retry, fetch, and error-bundle logic
across provider packages. That increases maintenance cost and makes it easier
for provider behavior to drift in ways that are hard to review consistently.

## Required Outcome

- Duplicate adapter logic collapses into canonical template owners.
- Provider adapters keep provider-specific behavior only.
- Duplicate cluster count for this family is reduced without creating a new
  cross-layer utility bucket.

## File-level Implementation Plan

### Changes

- `src/bioetl/infrastructure/adapters/common/fetch_resilience_template.py`:
  keep or extract the canonical shared template.
- `src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py` and
  `fetch_resilience_mixin.py`: delegate to canonical shared logic.
- `src/bioetl/infrastructure/adapters/common/error_bundles.py` and
  provider-local `_errors.py` modules: reduce repeated structure to one owner
  pattern.
- `reports/quality/full-app-duplication-baseline.json`: regenerate after each
  consolidation batch.

### Refactoring actions

Prefer explicit composition and narrow templates over new mixin proliferation.
Keep provider-specific protocol differences local to their adapters.

## Constraints

- Do not change provider-visible behavior.
- Do not introduce infrastructure-to-application or infrastructure-to-domain
  reverse dependencies.
- Do not raise duplication budgets or exemption limits.
- Preserve deterministic fetch/retry semantics and error classification.

## Acceptance Criteria

- [ ] Duplicate clusters in `src/bioetl/infrastructure/adapters` decrease from
      the current baseline.
- [ ] Canonical shared adapter template owners are documented by file.
- [ ] Provider-specific adapters no longer duplicate fetch/resilience skeletons.
- [ ] Duplication governance checks pass on regenerated artifacts.

