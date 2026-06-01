---
id: workflow-quarantine-orphans-1
title: Move reconcile_foreign_keys orphans to quarantine
task_id: workflow-quarantine-orphans-1
created_at: '2026-06-01T18:18:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added workflow FK reconciliation quarantine output path; orphans are now
  written to QuarantinePort before deletion, tagged by workflow_name if available.
---

# Episodic summary

## Task

- Title: Move reconcile_foreign_keys orphans to quarantine

## Outcome

- Added workflow FK reconciliation quarantine output path; orphans are now written to QuarantinePort before deletion, tagged by workflow_name if available.

## Lessons learned

- Replace with durable follow-up if needed
