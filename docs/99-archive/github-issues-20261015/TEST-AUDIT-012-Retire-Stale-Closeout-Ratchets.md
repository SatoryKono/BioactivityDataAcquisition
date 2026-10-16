---
title: "[TEST-AUDIT-012] Triage and retire stale closeout ratchets without weakening architecture invariants"
github_issue: 5500
labels: technical-debt
assignees: []
---

## Context

The 2026-06-22 audit found a large architecture governance surface: hundreds of
architecture tests, including historical wave/issue closeout ratchets and
drift/inventory/scorecard checks.

## Problem

A targeted scan found:

- 14 `closeout` architecture test files.
- 157 test files whose paths include drift/inventory/scorecard/baseline/manifest/registry/backlog/ratchet terms.
- Historical rollup flaky candidates concentrated in generated-artifact and architecture-governance checks.

Representative closeout files:

- `tests/architecture/test_wave3_ownership_closeout.py`
- `tests/architecture/test_wave3_adapter_facade_closeout.py`
- `tests/architecture/test_wave4_complexity_closeout.py`
- `tests/architecture/test_tech_debt_issues_5387_5394_closeout.py`
- `tests/architecture/test_issue_5272_application_core_coverage_closeout.py`

## Acceptance Criteria

- [ ] Each closeout/ratchet architecture test has an explicit retention classification.
- [ ] Stale historical closeout tests are removed or converted into non-blocking evidence docs.
- [ ] Duplicate ratchets are consolidated into canonical architecture guards.
- [ ] Core invariants remain covered: Hexagonal layering, DDD aggregate invariants, Medallion contracts, Composite Pipeline Pattern, determinism/idempotency/replay, Composition Root, and RunManifest/RunLedger/checkpoints.
- [ ] No technical-debt budget is increased.

