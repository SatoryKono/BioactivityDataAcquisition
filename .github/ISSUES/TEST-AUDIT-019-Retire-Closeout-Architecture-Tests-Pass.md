---
title: "[TEST-AUDIT-019] Retire or archive stale closeout architecture tests (51-file pass)"
labels: technical-debt, ci, P1
assignees: []
---

## Context

The `2026-07-03` test-system audit measured **410** architecture test files,
including **51 closeout** and **11 ratchet** files. Closeout triage policy exists
via `closeout_ratchet_triage.yaml`, but the live surface still imposes CI time and
author cognitive load.

This issue continues `TEST-AUDIT-012` with refreshed evidence from the July audit.

## Problem

Historical wave/issue closeout tests overlap with canonical architecture guards
and generator-backed drift checks. Representative files:

- `tests/architecture/test_wave3_ownership_closeout.py`
- `tests/architecture/test_wave3_adapter_facade_closeout.py`
- `tests/architecture/test_wave4_complexity_closeout.py`
- `tests/architecture/test_tech_debt_issues_5387_5394_closeout.py`
- `tests/architecture/test_tech_debt_issues_5866_5872_closeout.py`
- `tests/architecture/test_issue_5272_application_core_coverage_closeout.py`

Each file without a live guard should be retired, converted to non-blocking
evidence, or merged into a canonical ratchet — not left as redundant merge-blocking tests.

## Evidence

- `tests/architecture/test_closeout_ratchet_triage.py`
- `configs/quality/closeout_ratchet_triage.yaml`
- `reports/quality/test-governance-current.json`
- Architecture file counts from `2026-07-03` audit (51 closeout / 410 total)
- `.github/ISSUES/TEST-AUDIT-012-Retire-Stale-Closeout-Ratchets.md` ([#5500](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5500))

## Acceptance Criteria

- [ ] Every closeout architecture test file has an explicit retention classification in `closeout_ratchet_triage.yaml`.
- [ ] Stale closeout tests are removed or downgraded without losing live invariants.
- [ ] Duplicate ratchets are consolidated into canonical architecture guards.
- [ ] Core invariants remain covered: Hexagonal layering, DDD aggregates, Medallion contracts, determinism/replay, Composition Root, RunManifest/RunLedger/checkpoints.
- [ ] Architecture test file count and CI duration trend downward or flat after the pass.
- [ ] No technical-debt budget is increased.

## Related

- Extends `TEST-AUDIT-012` ([#5500](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5500)) with the post-audit 51-file inventory.
