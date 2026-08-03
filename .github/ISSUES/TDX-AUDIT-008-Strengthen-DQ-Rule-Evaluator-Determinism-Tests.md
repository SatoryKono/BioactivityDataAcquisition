---
title: "[TDX-AUDIT-008] Strengthen DQ rule evaluator determinism with golden and property tests"
labels: P0, technical-debt, coverage, domain, determinism, governance
assignees: []
---

## Context

The refreshed `2026-07-01` technical-debt audit on current `main` confirmed that
domain coverage governance is green on uncovered modules, but `159` domain modules
remain only partially covered. The highest determinism risk sits in DQ rule
evaluation, coercion, vocab/cross-rule behavior, and failure payload ordering.

## Evidence

- `reports/quality/total-tech-debt-audit-main-2026-07-01.md`
- `reports/quality/module-coverage-inventory.json`
- `src/bioetl/domain/behavior/_dq_rule_evaluators.py`
- `src/bioetl/domain/behavior/_dq_rule_evaluators_vocab.py`
- `src/bioetl/domain/behavior/dq_rule_evaluator.py`
- `src/bioetl/domain/behavior/value_validator.py`

## Problem

This is test debt and determinism-risk debt.

DQ invariants can still regress without golden/property coverage for rule
evaluation ordering, coercion boundaries, vocab/cross-rule interactions, and
deterministic failure payloads.

## Required Outcome

- Add golden and/or property tests for DQ rule evaluation paths.
- Cover coercion, vocab/cross-rule behavior, and deterministic failure payload
  ordering.
- Raise focused coverage on the highest-risk evaluator modules without lowering
  existing governance gates.

## File-level Implementation Plan

### Changes

- `src/bioetl/domain/behavior/_dq_rule_evaluators*.py`: add focused behavioral
  tests for branch-heavy evaluator paths.
- `src/bioetl/domain/behavior/dq_rule_evaluator.py`: cover orchestration and
  failure ordering semantics.
- `src/bioetl/domain/behavior/value_validator.py`: cover coercion and rejection
  boundaries.
- `reports/quality/module-coverage-inventory.json`: refresh after targeted test
  batches.

### Refactoring actions

Prefer deterministic golden/property tests over import-only or assertless smoke
coverage.

## Constraints

- Do not weaken DQ semantics or hide failures behind broader exception handling.
- Do not increase debt budgets or relax coverage governance.
- Preserve deterministic outputs, UTC timestamps, and canonical serialization.

## Acceptance Criteria

- [ ] DQ rule evaluation has golden/property coverage for coercion and
      vocab/cross-rule behavior.
- [ ] Failure payload ordering is covered by deterministic regression tests.
- [ ] At least one targeted evaluator module measurably improves on the canonical
      coverage inventory.
- [ ] Architecture and coverage governance checks pass after refresh.
