---
id: fix-health-cli-server-tests
title: Fix health CLI server unit test failures
task_id: fix-health-cli-server-tests
created_at: '2026-05-31T16:58:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/commands/test_health.py
summary: Updated health CLI unit tests to patch get_health_server_quarantine_service,
  the actual read-only health server quarantine bootstrap seam used by _run_health_server.
  This prevents tests from constructing a real QuarantineService and restores expected
  HealthServer kwargs plus shutdown output. Verified targeted failures, full test_health.py,
  ruff, and diff whitespace.
---

# Episodic summary

## Task

- Title: Fix health CLI server unit test failures

## Outcome

- Updated health CLI unit tests to patch get_health_server_quarantine_service, the actual read-only health server quarantine bootstrap seam used by _run_health_server. This prevents tests from constructing a real QuarantineService and restores expected HealthServer kwargs plus shutdown output. Verified targeted failures, full test_health.py, ruff, and diff whitespace.

## Lessons learned

- Replace with durable follow-up if needed
