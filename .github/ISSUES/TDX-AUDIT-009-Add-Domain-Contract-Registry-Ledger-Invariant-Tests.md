---
title: "[TDX-AUDIT-009] Add domain contract registry and ledger invariant tests"
labels: P0, technical-debt, coverage, domain, control-plane, determinism
assignees: []
---

## Context

The refreshed `2026-07-01` audit identified contract/invariant debt in domain
control-plane surfaces: registry loading semantics, gold contract identity,
ledger event immutability, and replay-safe serialization remain only partially
covered.

## Evidence

- `reports/quality/total-tech-debt-audit-main-2026-07-01.md`
- `reports/quality/contract-registry-diagnostics.json`
- `src/bioetl/domain/control_plane/contract_registry.py`
- `src/bioetl/domain/control_plane/contract_registry_loader.py`
- `src/bioetl/domain/control_plane/gold_contract.py`
- `src/bioetl/domain/ledger/core_events.py`

## Problem

This is contract/invariant debt.

Contract registry and ledger invariants are governance-critical, but current
coverage is still tail-heavy rather than backed by focused domain-only
behavioral tests.

## Required Outcome

- Add domain-only invariant tests for registry loading semantics.
- Cover gold contract identity and ledger event immutability.
- Verify replay-safe serialization for ledger/control-plane events.

## File-level Implementation Plan

### Changes

- `src/bioetl/domain/control_plane/contract_registry*.py`: add invariant tests
  for loading, identity, and failure semantics.
- `src/bioetl/domain/control_plane/gold_contract.py`: add identity and contract
  boundary tests.
- `src/bioetl/domain/ledger/core_events.py`: add immutability and replay-safe
  serialization tests.
- `reports/quality/module-coverage-inventory.json`: refresh after test batches.

### Refactoring actions

Keep tests domain-only. Do not pull infrastructure I/O into domain test paths.

## Constraints

- Do not weaken contract registry or ledger invariants.
- Do not increase debt budgets.
- Preserve replay semantics and deterministic serialization.

## Acceptance Criteria

- [ ] Registry loading semantics have focused domain-only tests.
- [ ] Gold contract identity and ledger event immutability are regression-tested.
- [ ] Replay-safe serialization paths are covered without infrastructure imports.
- [ ] Contract and coverage governance artifacts stay green after refresh.
