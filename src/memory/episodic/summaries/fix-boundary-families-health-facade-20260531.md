---
id: fix-boundary-families-health-facade-20260531
title: Fix boundary family health facade delegation tests
task_id: fix-boundary-families-health-facade-20260531
created_at: '2026-05-31T18:00:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/health.py
summary: Updated CLI health wrapper delegation so the failing health-service and health-server-deps
  boundary-family cases patch the public bioetl.composition.health_api facade seams.
  Verified both failing pytest parameters, ruff, module coverage inventory check,
  and architecture source-tree hash guard.
---

# Episodic summary

## Task

- Title: Fix boundary family health facade delegation tests

## Outcome

- Updated CLI health wrapper delegation so the failing health-service and health-server-deps boundary-family cases patch the public bioetl.composition.health_api facade seams. Verified both failing pytest parameters, ruff, module coverage inventory check, and architecture source-tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
