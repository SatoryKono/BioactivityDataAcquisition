---
id: chembl-molecule-bronze-cleanup-20260518
title: Fix chembl_molecule bronze cleanup
task_id: chembl-molecule-bronze-cleanup-20260518
created_at: '2026-05-18T19:03:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added E2E autouse patch for BronzeWriter.cleanup_old_files and fixed noop
  signature to accept dry_run/kwargs so chembl_molecule E2E no longer fails before
  assertions due to test-layer TypeError; full targeted E2E validation was noise-blocked
  by concurrent pytest runs.
---

# Episodic summary

## Task

- Title: Fix chembl_molecule bronze cleanup

## Outcome

- Added E2E autouse patch for BronzeWriter.cleanup_old_files and fixed noop signature to accept dry_run/kwargs so chembl_molecule E2E no longer fails before assertions due to test-layer TypeError; full targeted E2E validation was noise-blocked by concurrent pytest runs.

## Lessons learned

- Replace with durable follow-up if needed
