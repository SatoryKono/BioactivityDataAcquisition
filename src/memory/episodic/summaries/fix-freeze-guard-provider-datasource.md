---
id: fix-freeze-guard-provider-datasource
title: Fix compatibility freeze guard test failure
task_id: fix-freeze-guard-provider-datasource
created_at: '2026-06-16T08:08:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/test_coverage_boost_facades.py
summary: Replaced the remaining string-based monkeypatch target for bioetl.composition._services
  with an object-based patch so the compatibility freeze guard no longer detects a
  forbidden internal module string in unit tests.
---

# Episodic summary

## Task

- Title: Fix compatibility freeze guard test failure

## Outcome

- Replaced the remaining string-based monkeypatch target for bioetl.composition._services with an object-based patch so the compatibility freeze guard no longer detects a forbidden internal module string in unit tests.

## Lessons learned

- Replace with durable follow-up if needed
