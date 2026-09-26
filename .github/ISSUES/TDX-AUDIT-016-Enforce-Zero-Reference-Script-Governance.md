---
title: "[TDX-AUDIT-016] Enforce zero-reference supporting-script owner-or-removal governance in CI"
labels: P1, technical-debt, governance, scripts, hygiene, enforcement
assignees: []
---

## Context

The `2026-07-03` audit found `50` entries in
`configs/quality/scripts_inventory_manifest.json` with `reference_count: 0`.
Wave 1 `#5845` (`TDX-AUDIT-007`) inventoried supporting scripts, but zero-ref
scripts are not yet blocked by a dedicated fail-fast CI gate with explicit
owner-or-removal disposition.

## Evidence

- `configs/quality/scripts_inventory_manifest.json`
- `scripts/engineering/repo/README.md`
- `reports/quality/debt-governance-gates.json`
- `reports/quality/tech-debt-issues-5839-5845-closeout.json` (`#5845` evidence)
- `.github/workflows/quality-debt-weekly.yml`

## Problem

This is governance debt and dead-code risk.

Supporting scripts without tracked references can linger indefinitely, creating
orphan operational surfaces that are hard to discover during refactors or
security review.

## Required Outcome

- Every `reference_count: 0` script must have an explicit disposition:
  `retain_with_owner_rationale`, `retain_entrypoint`, or `remove`.
- Add a scorecard metric and architecture/QA gate that fails on new untriaged
  zero-reference scripts.
- Ratchet the zero-reference count flat or downward; do not allow silent growth.

## File-level Implementation Plan

### Changes

- `configs/quality/scripts_inventory_manifest.json`: triage all `50`
  zero-reference scripts with owner, rationale, and disposition metadata.
- `configs/quality/debt_scorecard.yaml`: add supporting-script zero-reference
  budget anchored to the triaged baseline.
- `tests/architecture/test_scripts_inventory_zero_reference_ratchet.py`: new
  fail-fast guard.
- `scripts/engineering/qa/report_debt_governance_gates.py`: emit gate for
  untriaged zero-reference scripts.
- Remove scripts only after importer/dynamic-invocation proof and manifest sync.

### Refactoring actions

Prefer removal for true orphans. Retain only scripts with documented owner,
review cadence, and invocation proof (CI, docs, or operator runbooks).

## Constraints

- Do not delete scripts referenced dynamically without proof-backed retention.
- Do not increase zero-reference budgets.
- Keep `scripts/engineering/repo/__main__.py` registry synchronized after
  removals.

## Acceptance Criteria

- [ ] Zero-reference script count is triaged to `0` untriaged entries.
- [ ] Scorecard and governance gates enforce flat-or-decreasing zero-reference
      residual.
- [ ] Removed scripts are absent from inventory and registry manifests.
- [ ] Retained zero-reference scripts have owner rationale in the manifest.
