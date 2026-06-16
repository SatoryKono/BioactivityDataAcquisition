---
id: app-services-lazy-facade-freeze-drift
title: Fix application services lazy facade freeze drift
task_id: app-services-lazy-facade-freeze-drift
created_at: '2026-06-16T08:11:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Removed the last test import through bioetl.application.services package
  root and updated the frozen test import inventory to the new zero-caller state.
---

# Episodic summary

## Task

- Title: Fix application services lazy facade freeze drift

## Outcome

- Removed the last test import through bioetl.application.services package root and updated the frozen test import inventory to the new zero-caller state.

## Lessons learned

- Replace with durable follow-up if needed
