---
title: "[TDX-AUDIT-013] Burn down infrastructure adapter duplication clusters from the 48-cluster baseline"
labels: P0, technical-debt, duplication, adapters, infrastructure, refactor
assignees: []
---

## Context

Wave 1 `#5840` (`TDX-AUDIT-002`) introduced canonical adapter template owners,
but the refreshed `2026-07-03` full-app duplication baseline still reports
`48` duplicate clusters under `src/bioetl/infrastructure/adapters`. The
dominant actionability category remains
`export_facade_or_package_barrel`, with additional fetch/resilience template
residue.

## Evidence

- `reports/quality/full-app-duplication-baseline.json`
- `src/bioetl/infrastructure/adapters/common/fetch_resilience_template.py`
- `src/bioetl/infrastructure/adapters/common/error_bundles.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`
- `src/bioetl/infrastructure/adapters/pubmed/_errors.py`
- `reports/quality/tech-debt-issues-5839-5845-closeout.json` (`#5840` evidence)

## Problem

This is duplication debt and architectural debt.

Provider adapters still repeat barrel exports, fetch/resilience skeletons, and
error-bundle structure. That increases review cost and allows provider behavior
to drift outside canonical template owners.

## Required Outcome

- Reduce duplicate cluster count for `src/bioetl/infrastructure/adapters` from
  `48` downward without raising budgets.
- Keep provider-specific protocol differences local to provider packages.
- Regenerate duplication baselines after each consolidation batch.

## File-level Implementation Plan

### Changes

- `src/bioetl/infrastructure/adapters/common/fetch_resilience_template.py`:
  remain the canonical fetch/resilience owner; extend only where needed.
- Provider `fetch_*_mixin.py` and `_errors.py` modules: delegate repeated
  structure to common owners.
- Package `__init__.py` barrel clusters: narrow lazy/public exports to tested
  canonical surfaces.
- `reports/quality/full-app-duplication-baseline.json`: regenerate and ratchet
  downward through `TDX-AUDIT-012` enforcement.

### Refactoring actions

Prefer explicit composition over new mixin layers. Collapse low-risk barrel
clusters first (`low_risk_cluster_share` is `0.875` in the baseline ranking).

## Constraints

- Do not change provider-visible HTTP/retry/error behavior.
- Do not introduce reverse dependencies into domain or application layers.
- Do not raise duplication budgets.

## Acceptance Criteria

- [ ] Adapter duplicate cluster count decreases from the `48` baseline.
- [ ] Canonical template owners are documented by file in closeout evidence.
- [ ] Provider adapters no longer duplicate fetch/resilience skeletons.
- [ ] Full-app duplication ratchet passes on regenerated artifacts.
