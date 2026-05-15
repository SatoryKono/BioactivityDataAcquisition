---
id: fix-relative-as-uri-20260515
title: Fix relative Path.as_uri failure in run_manifest test support
task_id: fix-relative-as-uri-20260515
created_at: '2026-05-15T11:51:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Made synthetic test roots absolute so import-time Path.as_uri() calls used
  by run-manifest-related tests are valid on Windows and Linux.
---

# Episodic summary

## Task

- Title: Fix relative Path.as_uri failure in run_manifest test support

## Outcome

- Made synthetic test roots absolute so import-time Path.as_uri() calls used by run-manifest-related tests are valid on Windows and Linux.

## Lessons learned

- Replace with durable follow-up if needed
