---
id: fix-function-length-metrics-20260516
title: Fix function length metric regressions
task_id: fix-function-length-metrics-20260516
created_at: '2026-05-16T10:41:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Followed up the long-function refactor by splitting operator replay projection
  into a dedicated helper module, shrinking replay diagnostics below the application
  file-size cap, and refreshing the existing control-plane extractor file-size exemption
  to 483 LOC while preserving current behavior.
---

# Episodic summary

## Task

- Title: Fix function length metric regressions

## Outcome

- Followed up the long-function refactor by splitting operator replay projection into a dedicated helper module, shrinking replay diagnostics below the application file-size cap, and refreshing the existing control-plane extractor file-size exemption to 483 LOC while preserving current behavior.

## Lessons learned

- Replace with durable follow-up if needed
