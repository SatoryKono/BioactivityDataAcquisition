---
id: issue-4036-composition-services-package-root-removal
title: Issue 4036 composition.services package-root removal
task_id: issue-4036-composition-services-package-root-removal
created_at: '2026-05-13T17:58:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed direct versioning helper re-exports from bioetl.composition.services
  package root, kept only the versioning namespace, added a package-root absence guard,
  and validated with py_compile plus targeted versioning pytest coverage.
---

# Episodic summary

## Task

- Title: Issue 4036 composition.services package-root removal

## Outcome

- Removed direct versioning helper re-exports from bioetl.composition.services package root, kept only the versioning namespace, added a package-root absence guard, and validated with py_compile plus targeted versioning pytest coverage.

## Lessons learned

- Replace with durable follow-up if needed
