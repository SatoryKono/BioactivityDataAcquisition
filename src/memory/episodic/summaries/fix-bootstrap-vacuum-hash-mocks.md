---
id: fix-bootstrap-vacuum-hash-mocks
title: Fix bootstrap vacuum test doubles for strict hash normalization
task_id: fix-bootstrap-vacuum-hash-mocks
created_at: '2026-05-15T17:08:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/bootstrap/test_bootstrap_entrypoints.py
summary: Updated bootstrap vacuum tests so mocked control-plane refs use canonical
  64-char lowercase hex hashes for strict normalization.
---

# Episodic summary

## Task

- Title: Fix bootstrap vacuum test doubles for strict hash normalization

## Outcome

- Updated bootstrap vacuum tests so mocked control-plane refs use canonical 64-char lowercase hex hashes for strict normalization.

## Lessons learned

- Replace with durable follow-up if needed
