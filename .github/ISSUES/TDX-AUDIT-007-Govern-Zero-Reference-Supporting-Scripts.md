---
title: "[TDX-AUDIT-007] Turn zero-reference supporting scripts into explicit owner-or-removal governance"
labels: P2, technical-debt, governance, cleanup, developer-experience
assignees: []
---

## Context

The script inventory no longer reports orphan or unknown scripts, but the
`2026-07-01` audit found `81` `supporting` scripts still retained in backlog,
many with `reference_count = 0`.

## Evidence

- `reports/quality/scripts_deprecation_backlog.md`
- `configs/quality/scripts_inventory_manifest.json`
- `scripts/docs/_compat_shim.py`
- `scripts/engineering/qa/create_github_issues.py`
- `scripts/ops/maintenance/github/update_github_issue.sh`
- `scripts/ai/mcp/*.ps1`

## Problem

This is governance debt and cleanup debt.

The current script inventory distinguishes `supporting` from `orphan`, but it
does not force zero-reference helpers to converge toward a canonical owner or a
removal decision.

## Required Outcome

- Zero-reference supporting scripts become an explicit governance queue.
- Every retained zero-reference helper has an owner and replacement strategy.
- Scripts without justification are removed instead of staying indefinitely in a
  supporting bucket.

## File-level Implementation Plan

### Changes

- `reports/quality/scripts_deprecation_backlog.md`: regenerate after owner or
  removal decisions.
- `configs/quality/scripts_inventory_manifest.json`: add any needed governance
  metadata surfaces without widening retention scope.
- `scripts/docs/_compat_shim.py` and other zero-reference helpers: re-review for
  removal or canonical replacement.

### Refactoring actions

Keep script governance deterministic and machine-auditable. Do not hide backlog
entries by reclassifying them without an owner decision.

## Constraints

- Do not add new supporting-script debt without owner metadata.
- Do not increase script governance budgets.
- Do not convert runtime behavior into undocumented shell-only flows.

## Acceptance Criteria

- [ ] Zero-reference supporting scripts have explicit owner or removal
      disposition.
- [ ] Supporting backlog count decreases, or every retained zero-reference entry
      has justification.
- [ ] Script inventory and backlog reports stay synchronized after regeneration.

