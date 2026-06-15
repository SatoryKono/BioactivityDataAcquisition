---
id: fix-versioning-dirty-state
title: Fix versioning dirty-state provenance
task_id: fix-versioning-dirty-state
created_at: '2026-06-15T11:10:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/services/test_versioning.py
summary: Stabilized versioning provenance unit tests against live repo lockfile state
  by isolating runtime cwd and mocking repo lockfile fallback, so dirty/clean provenance
  expectations no longer depend on the checkout's real uv.lock presence.
---

# Episodic summary

## Task

- Title: Fix versioning dirty-state provenance

## Outcome

- Stabilized versioning provenance unit tests against live repo lockfile state by isolating runtime cwd and mocking repo lockfile fallback, so dirty/clean provenance expectations no longer depend on the checkout's real uv.lock presence.

## Lessons learned

- Replace with durable follow-up if needed
