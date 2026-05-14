---
id: issue-4036-http-package-root-export-removal
title: Issue 4036 HTTP package-root export removal
task_id: issue-4036-http-package-root-export-removal
created_at: '2026-05-13T17:55:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed HealthServer and HealthResponse convenience exports from bioetl.interfaces.http
  package root, added absence guard in tests/unit/interfaces/http/test_http_init.py,
  and validated the impacted HTTP package surface with py_compile plus targeted pytest
  slices.
---

# Episodic summary

## Task

- Title: Issue 4036 HTTP package-root export removal

## Outcome

- Removed HealthServer and HealthResponse convenience exports from bioetl.interfaces.http package root, added absence guard in tests/unit/interfaces/http/test_http_init.py, and validated the impacted HTTP package surface with py_compile plus targeted pytest slices.

## Lessons learned

- Replace with durable follow-up if needed
