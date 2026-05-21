---
id: fix-contract-failures-20260521
title: Fix contract test failures
task_id: fix-contract-failures-20260521
created_at: '2026-05-21T08:04:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_normalization_cross_layer_contracts.py
summary: Updated the chembl_publication Gold schema snapshot registry to match the
  active contract surface and rewrote the runtime-anchor contract test to validate
  the lenient runtime-anchor seam instead of equating it with the canonical checkpoint
  execution-identity fingerprint.
---

# Episodic summary

## Task

- Title: Fix contract test failures

## Outcome

- Updated the chembl_publication Gold schema snapshot registry to match the active contract surface and rewrote the runtime-anchor contract test to validate the lenient runtime-anchor seam instead of equating it with the canonical checkpoint execution-identity fingerprint.

## Lessons learned

- Replace with durable follow-up if needed
