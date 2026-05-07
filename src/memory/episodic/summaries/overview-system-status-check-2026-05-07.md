---
id: overview-system-status-check-2026-05-07
title: Check Overview System Status panel correctness
task_id: overview-system-status-check-2026-05-07
created_at: '2026-05-07T18:30:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated bioetl_l0_status precedence to CRIT > WARN > UNKNOWN > OK so selected-scope
  UNKNOWN no longer masks real CRIT. Verified promtool check passes and live Prometheus
  now reports test_pipe=2 while scopes with only workflow/control-plane gaps remain
  3 as intended.
---

# Episodic summary

## Task

- Title: Check Overview System Status panel correctness

## Outcome

- Updated bioetl_l0_status precedence to CRIT > WARN > UNKNOWN > OK so selected-scope UNKNOWN no longer masks real CRIT. Verified promtool check passes and live Prometheus now reports test_pipe=2 while scopes with only workflow/control-plane gaps remain 3 as intended.

## Lessons learned

- Replace with durable follow-up if needed
