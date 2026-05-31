---
id: fix-test-governance-audit-drift
title: Fix test governance audit baseline drift
task_id: fix-test-governance-audit-drift
created_at: '2026-05-31T15:59:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_test_governance_audit.py
summary: Investigated reported test_governance_audit failures. Current checkout already
  has compatibility ratchet target/budget at 53 and assertless triage weak_no_value
  at 424; WSL and Windows scanner outputs match config, and the targeted governance
  tests pass on both runtimes. No source/config patch required.
---

# Episodic summary

## Task

- Title: Fix test governance audit baseline drift

## Outcome

- Investigated reported test_governance_audit failures. Current checkout already has compatibility ratchet target/budget at 53 and assertless triage weak_no_value at 424; WSL and Windows scanner outputs match config, and the targeted governance tests pass on both runtimes. No source/config patch required.

## Lessons learned

- Replace with durable follow-up if needed
