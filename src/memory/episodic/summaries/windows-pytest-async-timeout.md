---
id: windows-pytest-async-timeout
title: Debug Windows pytest async fixture timeout
task_id: windows-pytest-async-timeout
created_at: '2026-06-01T18:09:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/health_server.py
summary: Bounded HealthServer writer/server wait_closed shutdown paths to prevent
  Windows/PyCharm pytest-asyncio fixture teardowns from hanging; added timeout regression
  tests and refreshed module coverage inventory source_tree_sha256 after src edits.
---

# Episodic summary

## Task

- Title: Debug Windows pytest async fixture timeout

## Outcome

- Bounded HealthServer writer/server wait_closed shutdown paths to prevent Windows/PyCharm pytest-asyncio fixture teardowns from hanging; added timeout regression tests and refreshed module coverage inventory source_tree_sha256 after src edits.

## Lessons learned

- Replace with durable follow-up if needed
