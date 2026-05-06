---
id: reduce-cc-replay-policy
title: Reduce CC in replay policy helpers
task_id: reduce-cc-replay-policy
created_at: '2026-05-06T13:29:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/reproducibility_policy.py
summary: Reduced cyclomatic complexity in replay readiness, checkpoint taxonomy, and
  exact replay blocker helpers without changing replay diagnostics behavior.
---

# Episodic summary

## Task

- Title: Reduce CC in replay policy helpers

## Outcome

- Reduced cyclomatic complexity in replay readiness, checkpoint taxonomy, and exact replay blocker helpers without changing replay diagnostics behavior.

## Lessons learned

- Replace with durable follow-up if needed
