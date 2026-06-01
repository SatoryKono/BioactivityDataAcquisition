---
id: fix-forbidden-port-import-facade
title: Fix forbidden port import facade violation
task_id: fix-forbidden-port-import-facade
created_at: '2026-06-01T15:27:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Changed derived target data-source delegation helper to import HealthCheckResult
  from the sanctioned bioetl.domain.ports facade; refreshed module coverage inventory
  and verified forbidden import facade, ruff, related provider/private-import tests,
  and source-tree hash guard.
---

# Episodic summary

## Task

- Title: Fix forbidden port import facade violation

## Outcome

- Changed derived target data-source delegation helper to import HealthCheckResult from the sanctioned bioetl.domain.ports facade; refreshed module coverage inventory and verified forbidden import facade, ruff, related provider/private-import tests, and source-tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
