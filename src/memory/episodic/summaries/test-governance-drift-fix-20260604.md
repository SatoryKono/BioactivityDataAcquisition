---
id: test-governance-drift-fix-20260604
title: Fix test governance artifact drift
task_id: test-governance-drift-fix-20260604
created_at: '2026-06-04T14:30:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/test-governance-current.json
summary: Refreshed the committed test governance artifact after live collector drift.
  The current snapshot had stale test-function totals and line anchors; rerunning
  report_test_governance_audit regenerated reports/quality/test-governance-current.json
  and restored the architecture drift guard.
---

# Episodic summary

## Task

- Title: Fix test governance artifact drift

## Outcome

- Refreshed the committed test governance artifact after live collector drift. The current snapshot had stale test-function totals and line anchors; rerunning report_test_governance_audit regenerated reports/quality/test-governance-current.json and restored the architecture drift guard.

## Lessons learned

- Replace with durable follow-up if needed
