---
id: fix-semanticscholar-e2e-timeout
title: Fix Semantic Scholar E2E timeout on 429
task_id: fix-semanticscholar-e2e-timeout
created_at: '2026-06-03T14:38:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/datasource/http_client.py
summary: Clamped provider HTTP retry waits in test_mode, routed Semantic Scholar E2E
  tests through transient-skip helper, and refreshed module-coverage inventory hash
  after src changes.
---

# Episodic summary

## Task

- Title: Fix Semantic Scholar E2E timeout on 429

## Outcome

- Clamped provider HTTP retry waits in test_mode, routed Semantic Scholar E2E tests through transient-skip helper, and refreshed module-coverage inventory hash after src changes.

## Lessons learned

- Replace with durable follow-up if needed
