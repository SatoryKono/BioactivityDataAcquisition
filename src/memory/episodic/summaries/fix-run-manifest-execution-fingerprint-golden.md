---
id: fix-run-manifest-execution-fingerprint-golden
title: Fix run manifest execution fingerprint golden mismatch
task_id: fix-run-manifest-execution-fingerprint-golden
created_at: '2026-06-17T14:21:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_run_manifest_service.py
- tests/unit/domain/normalization/test_fingerprints.py
- docs/filters/migration-plan.md
summary: Updated stale execution identity golden hashes for run-manifest and domain
  fingerprint tests to match the current canonical payload that includes silver_filter_compatibility_mode=structural_only_compat.
  Added an assertion tying the run-manifest golden to the identity payload mode. Validated
  targeted run-manifest, domain fingerprint, checkpoint metadata, checkpoint alignment
  tests and ruff. No src/bioetl changes; module coverage inventory refresh not required.
---

# Episodic summary

## Task

- Title: Fix run manifest execution fingerprint golden mismatch

## Outcome

- Updated stale execution identity golden hashes for run-manifest and domain fingerprint tests to match the current canonical payload that includes silver_filter_compatibility_mode=structural_only_compat. Added an assertion tying the run-manifest golden to the identity payload mode. Validated targeted run-manifest, domain fingerprint, checkpoint metadata, checkpoint alignment tests and ruff. No src/bioetl changes; module coverage inventory refresh not required.

## Lessons learned

- Replace with durable follow-up if needed
