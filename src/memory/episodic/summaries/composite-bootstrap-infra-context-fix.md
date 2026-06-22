---
id: composite-bootstrap-infra-context-fix
title: Fix composite bootstrap plan infra context contract
task_id: composite-bootstrap-infra-context-fix
created_at: '2026-06-22T17:27:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/bootstrap/runtime/test_composite_runner_bootstrap.py
summary: Updated the composite runner bootstrap unit test to assert the canonical
  CompositeInfrastructureContext normalization performed before support-service assembly,
  instead of expecting the legacy raw SimpleNamespace bundle.
---

# Episodic summary

## Task

- Title: Fix composite bootstrap plan infra context contract

## Outcome

- Updated the composite runner bootstrap unit test to assert the canonical CompositeInfrastructureContext normalization performed before support-service assembly, instead of expecting the legacy raw SimpleNamespace bundle.

## Lessons learned

- Replace with durable follow-up if needed
