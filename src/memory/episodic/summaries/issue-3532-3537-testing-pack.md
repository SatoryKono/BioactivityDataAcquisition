---
id: issue-3532-3537-testing-pack
title: Implement testing issue pack 3532 3533 3535 3536 3537
task_id: issue-3532-3537-testing-pack
created_at: '2026-05-14T07:19:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/conftest.py
summary: Added deterministic E2E test context helpers and guards for replay/control-plane
  assertions; switched full-cycle PubChem and ChEMBL assay E2E tests to stable contexts;
  added architecture guardrails for pytest bootstrap import-path mutation and hotspot
  budget registry bijection; strengthened pytest single-source policy against legacy
  setup.cfg/tox.ini sections. Verified modified files with py_compile and direct Python
  assertions for deterministic context, replay parentage, pytest config single source,
  bootstrap path policy, and hotspot registry parity. Full pytest subsets remained
  expensive to initialize, so broad pytest reruns were not carried to completion in
  this pass.
---

# Episodic summary

## Task

- Title: Implement testing issue pack 3532 3533 3535 3536 3537

## Outcome

- Added deterministic E2E test context helpers and guards for replay/control-plane assertions; switched full-cycle PubChem and ChEMBL assay E2E tests to stable contexts; added architecture guardrails for pytest bootstrap import-path mutation and hotspot budget registry bijection; strengthened pytest single-source policy against legacy setup.cfg/tox.ini sections. Verified modified files with py_compile and direct Python assertions for deterministic context, replay parentage, pytest config single source, bootstrap path policy, and hotspot registry parity. Full pytest subsets remained expensive to initialize, so broad pytest reruns were not carried to completion in this pass.

## Lessons learned

- Replace with durable follow-up if needed
