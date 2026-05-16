---
id: fix-bootstrap-entrypoints-manifest-drift-20260516
title: Fix bootstrap entrypoint manifest mock drift
task_id: fix-bootstrap-entrypoints-manifest-drift-20260516
created_at: '2026-05-16T09:05:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Patched bootstrap entrypoint tests to mock create_run_manifest_with_effective_config
  so they stay focused on bootstrap behavior, and corrected invalid SHA-256 placeholders
  in the chembl_activity manifest mock. Verified the two affected tests pass.
---

# Episodic summary

## Task

- Title: Fix bootstrap entrypoint manifest mock drift

## Outcome

- Patched bootstrap entrypoint tests to mock create_run_manifest_with_effective_config so they stay focused on bootstrap behavior, and corrected invalid SHA-256 placeholders in the chembl_activity manifest mock. Verified the two affected tests pass.

## Lessons learned

- Replace with durable follow-up if needed
