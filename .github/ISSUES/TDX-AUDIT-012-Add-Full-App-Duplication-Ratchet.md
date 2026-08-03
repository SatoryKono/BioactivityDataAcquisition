---
title: "[TDX-AUDIT-012] Add full-app duplication ratchet to scorecard and architecture CI"
labels: P0, technical-debt, duplication, governance, architecture-tests, enforcement
assignees: []
---

## Context

The `2026-07-03` technical-debt audit found that hotspot-family duplication is
fully ratcheted to zero across five governed targets, but the broader full-app
duplication scan still reports `57` duplicate clusters. The largest residual is
`src/bioetl/infrastructure/adapters` with `48` clusters, followed by
`src/bioetl/application/pipelines` with `9`.

This surface is currently visible in `full-app-duplication-baseline.json` but
not enforced by a dedicated fail-fast architecture ratchet or scorecard budget.

## Evidence

- `reports/quality/full-app-duplication-baseline.json`
- `reports/quality/hotspot-duplication-baseline.json`
- `configs/quality/debt_scorecard.yaml`
- `tests/architecture/test_hotspot_duplication_family_ratchets.py`
- `tests/architecture/test_duplication_report_governance.py`
- `scripts/engineering/qa/report_duplication_baseline.py`

## Problem

This is governance debt and duplication debt.

Hotspot zero-budget families can stay green while full-app duplication grows or
stalls without blocking CI. The repo therefore lacks a deterministic enforcement
loop for the largest remaining duplication families outside the hotspot scope.

## Required Outcome

- Add scorecard metrics and architecture-test enforcement for full-app
  duplication families with flat-or-decreasing budgets.
- Commit regenerated `full-app-duplication-baseline.json` as the reviewed
  baseline for ratchet comparisons.
- Ensure `hotspot-duplication-baseline.json` and history artifacts remain
  tracked and aligned with scorecard `latest_reviewed_snapshot`.

## File-level Implementation Plan

### Changes

- `configs/quality/debt_scorecard.yaml`: add `full_app_duplication_ratchets`
  (or equivalent) with per-target budgets anchored to the current baseline:
  adapters `48`, pipelines `9`, bootstrap `0`, interfaces/cli `0`, total `57`.
- `tests/architecture/test_full_app_duplication_ratchet.py`: new fail-fast guard
  comparing live baseline JSON to scorecard budgets.
- `reports/quality/full-app-duplication-baseline.json`: regenerate via
  `python -m scripts.engineering.qa report-duplication-baseline` after each
  reduction batch.
- `.gitignore`: keep `hotspot-duplication-baseline.{json,md}` and
  `hotspot-duplication-history.jsonl` whitelisted for committed governance.
- `.github/workflows/duplication-complexity.yml`: ensure artifacts required by
  the new ratchet are produced in CI.

### Refactoring actions

Reuse the existing duplication report schema and actionability categories from
`report_duplication_baseline.py`; do not invent a parallel scanner.

## Constraints

- Do not increase duplication budgets or exemption limits.
- Do not weaken hotspot-family zero budgets to make full-app metrics pass.
- Preserve deterministic scan inputs and committed baseline ordering.

## Acceptance Criteria

- [ ] Scorecard defines flat-or-decreasing full-app duplication budgets for
      adapters, pipelines, and total cluster count.
- [ ] Architecture CI fails when live baseline exceeds reviewed budgets.
- [ ] `debt-governance-gates.json` includes the new ratchet with `pass` status.
- [ ] Hotspot and full-app duplication artifacts remain coherent after refresh.
