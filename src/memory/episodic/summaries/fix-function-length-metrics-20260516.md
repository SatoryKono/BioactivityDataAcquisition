---
id: fix-function-length-metrics-20260516
title: Fix function length metric regressions
task_id: fix-function-length-metrics-20260516
created_at: '2026-05-16T10:31:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Reduced three function-length metric regressions below the 100-line cap by
  extracting replay-projection, effective-config-context, and control-plane anchor-value
  helpers without changing returned payload shapes.
---

# Episodic summary

## Task

- Title: Fix function length metric regressions

## Outcome

- Reduced three function-length metric regressions below the 100-line cap by extracting replay-projection, effective-config-context, and control-plane anchor-value helpers without changing returned payload shapes.

## Lessons learned

- Replace with durable follow-up if needed
