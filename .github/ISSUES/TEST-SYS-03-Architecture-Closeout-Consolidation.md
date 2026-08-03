---
title: "[P1][testing] TEST-SYS-03: Architecture closeout consolidation + nightly split"
labels: P1, testing, architecture-tests, ci, technical-debt, governance, cleanup
assignees: []
github_issue: 7025
---

## Context

~**16%** of architecture tests are closeout/tech-debt/issue freezes. They protect
budgets but inflate collection/runtime and dilute regression signal. Prior work:
TEST-AUDIT-012 (#5500), TEST-AUDIT-019 (#5931).

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §5 O1, P1-1  
**Epic:** TEST-SYS-00

## Problem

Per-issue closeout files remain executable forever after the issue is done.
Multiple S7 shards re-collect the same `tests/architecture` tree.

## Scope / modules

- `tests/architecture/test_*closeout*.py`
- `tests/architecture/test_tech_debt_issues_*`
- `configs/quality/closeout_ratchet_triage.yaml`
- `tests/architecture/test_closeout_ratchet_triage.py`
- CI workflows selecting architecture shards

## Acceptance Criteria

- [ ] Every closeout file has retention class in triage YAML (keep / nightly / retire / meta-gate)
- [ ] PR path runs **live** architecture invariants + snapshot meta-gate; bulky closeouts are nightly-only or merged into inventory-driven meta-suite
- [ ] Retire or archive files superseded by canonical guards without losing budget protection
- [ ] Architecture wall-clock / collect cost trends down or flat on PR
- [ ] No debt-budget growth; no deletion of purity/determinism/quarantine immutability gates

## Related

- TEST-AUDIT-019 #5931, TEST-AUDIT-012 #5500
- TEST-SYS-04 (shard collapse)
- ARCH-CR2-09 #7014 (test honesty)
