---
id: fix-debt-governance-remote-main-failure-2026-06-22
title: Fix debt governance gate unit test remote-main dependency
task_id: fix-debt-governance-remote-main-failure-2026-06-22
created_at: '2026-06-22T08:22:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_debt_governance_gates.py
summary: Confirmed the debt-governance gate builder now treats remote-main baseline
  builder failures as stale artifacts instead of crashing, and revalidated the targeted
  unit tests.
---

# Episodic summary

## Task

- Title: Fix debt governance gate unit test remote-main dependency

## Outcome

- Confirmed the debt-governance gate builder now treats remote-main baseline builder failures as stale artifacts instead of crashing, and revalidated the targeted unit tests.

## Lessons learned

- Replace with durable follow-up if needed
